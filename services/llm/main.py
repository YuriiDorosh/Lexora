"""LLM Enrichment Service (FastAPI).

Consumes ``enrichment.requested`` from RabbitMQ, generates structured
enrichment data, and publishes ``enrichment.completed`` or
``enrichment.failed``.

Real implementation uses a local CPU-only LLM via ``llama-cpp-python``
against a quantized GGUF model (ADR-027).  Default model is Qwen2.5-
1.5B-Instruct Q4_K_M, sized for an 8 GiB target server.  Operators with
more RAM can opt into 3B (or any other GGUF) via the LLM_MODEL_REPO /
LLM_MODEL_FILENAME environment variables.

If the model file is missing and ``LLM_AUTO_DOWNLOAD=1`` (default), it is
pulled from Hugging Face on first start via ``huggingface_hub``.  If the
download or load fails for any reason, the service keeps running in stub
mode so the RabbitMQ consumer never dies; /health honestly reports
``llm_ready=false`` in that case.
"""

from __future__ import annotations

import contextlib
from contextlib import asynccontextmanager
import json
import logging
import os
import re
import threading
import time

from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("llm-service")

# ---------------------------------------------------------------------------
# RabbitMQ configuration (from environment / docker-compose)
# ---------------------------------------------------------------------------

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

QUEUE_IN = "enrichment.requested"
QUEUE_COMPLETED = "enrichment.completed"
QUEUE_FAILED = "enrichment.failed"

# ---------------------------------------------------------------------------
# LLM configuration (from environment / docker-compose)
# ---------------------------------------------------------------------------

LLM_MODEL_REPO = os.getenv("LLM_MODEL_REPO", "Qwen/Qwen2.5-1.5B-Instruct-GGUF")
LLM_MODEL_FILENAME = os.getenv("LLM_MODEL_FILENAME", "qwen2.5-1.5b-instruct-q4_k_m.gguf")
LLM_MODEL_DIR = os.getenv("LLM_MODEL_DIR", "/models")
LLM_N_CTX = int(os.getenv("LLM_N_CTX", "2048"))
LLM_N_THREADS = int(os.getenv("LLM_N_THREADS", "0"))  # 0 = auto
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))
LLM_AUTO_DOWNLOAD = os.getenv("LLM_AUTO_DOWNLOAD", "1") == "1"

LANG_NAMES = {"en": "English", "uk": "Ukrainian", "el": "Greek", "pl": "Polish"}

# ---------------------------------------------------------------------------
# Model loading (CPU-only, ADR-027)
# ---------------------------------------------------------------------------

_llm = None  # llama_cpp.Llama instance once loaded
_llm_ready = False


def _resolve_model_path() -> str:
    """Return absolute path to the GGUF file, downloading if needed.

    Looks up ``<LLM_MODEL_DIR>/<LLM_MODEL_FILENAME>`` first.  If absent and
    auto-download is enabled, pulls the file from the Hugging Face repo via
    ``huggingface_hub.hf_hub_download`` into ``LLM_MODEL_DIR``.
    Raises if the file cannot be obtained.
    """
    os.makedirs(LLM_MODEL_DIR, exist_ok=True)
    target = os.path.join(LLM_MODEL_DIR, LLM_MODEL_FILENAME)
    if os.path.isfile(target):
        return target

    if not LLM_AUTO_DOWNLOAD:
        raise FileNotFoundError(
            f"Model file {target} missing and LLM_AUTO_DOWNLOAD=0 — "
            "pre-seed the llm_models volume or set LLM_AUTO_DOWNLOAD=1."
        )

    from huggingface_hub import hf_hub_download

    _logger.info(
        "Downloading model %s/%s → %s (this can take a while on first boot)",
        LLM_MODEL_REPO,
        LLM_MODEL_FILENAME,
        LLM_MODEL_DIR,
    )
    downloaded = hf_hub_download(
        repo_id=LLM_MODEL_REPO,
        filename=LLM_MODEL_FILENAME,
        local_dir=LLM_MODEL_DIR,
    )
    _logger.info("Model download complete: %s", downloaded)
    return downloaded


def _init_llm():
    """Load the GGUF model via llama-cpp-python.

    Returns True on success.  On any exception (missing file, bad format,
    OOM, etc.) logs the cause and returns False so the service keeps
    running in stub mode.  /health reports the actual state.
    """
    global _llm
    try:
        model_path = _resolve_model_path()
        from llama_cpp import Llama

        kwargs = {
            "model_path": model_path,
            "n_ctx": LLM_N_CTX,
            "verbose": False,
        }
        if LLM_N_THREADS > 0:
            kwargs["n_threads"] = LLM_N_THREADS

        _logger.info(
            "Loading LLM model=%s n_ctx=%d n_threads=%s",
            os.path.basename(model_path),
            LLM_N_CTX,
            LLM_N_THREADS or "auto",
        )
        _llm = Llama(**kwargs)
        _logger.info("LLM model loaded successfully.")
        return True
    except Exception as exc:
        _logger.warning(
            "LLM initialisation failed (%s) — staying in stub mode.",
            exc,
        )
        return False


# ---------------------------------------------------------------------------
# Prompt + JSON extraction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a concise vocabulary-enrichment assistant. "
    "You respond with a SINGLE JSON object and nothing else. "
    "The JSON object must have exactly these keys: "
    '"synonyms" (array of 3-6 short strings), '
    '"antonyms" (array of 2-4 short strings, can be empty if none exist), '
    '"example_sentences" (array of 3-5 short sentences using the term in context), '
    '"explanation" (a one-paragraph string, 1-3 sentences). '
    "CRITICAL: Output ONLY in the SAME language as the input term. "
    "Do NOT translate. Do NOT switch to another language. "
    "Keep every string short. Do not add commentary, markdown, or code fences."
)


def _build_user_prompt(source_text: str, source_language: str, language: str) -> str:
    lang_name = LANG_NAMES.get(language, language)
    return (
        f"Term ({lang_name}): {source_text!r}\n"
        f"Enrich this term. All output values must be in {lang_name} only.\n\n"
        "Return the JSON object now."
    )


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_enrichment_json(raw: str) -> dict:
    """Parse the model's JSON reply.  Raises ValueError on unusable output.

    Handles small-model quirks: stray prose around the JSON, single-quoted
    keys, trailing commas.  If strict ``json.loads`` succeeds we prefer it;
    otherwise we fall back to a best-effort extraction of the outermost
    ``{...}`` block.
    """
    text = (raw or "").strip()
    try:
        parsed = json.loads(text)
    except Exception:
        match = _JSON_OBJECT_RE.search(text)
        if not match:
            raise ValueError(f"no JSON object in model output: {text[:200]!r}") from None
        candidate = match.group(0)
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)  # trailing commas
        parsed = json.loads(candidate)

    if not isinstance(parsed, dict):
        raise ValueError(f"model output was not a JSON object: {type(parsed).__name__}")
    return parsed


def _coerce_result(parsed: dict, source_text: str) -> dict:
    """Normalise model output into the shape language.enrichment expects."""

    def _as_str_list(v):
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return []

    def _as_str(v):
        if isinstance(v, str):
            return v.strip()
        if v is None:
            return ""
        return str(v).strip()

    return {
        "synonyms": _as_str_list(parsed.get("synonyms")),
        "antonyms": _as_str_list(parsed.get("antonyms")),
        "example_sentences": _as_str_list(parsed.get("example_sentences")),
        "explanation": _as_str(parsed.get("explanation"))
        or f"Enrichment for {source_text!r} (no explanation generated).",
    }


# ---------------------------------------------------------------------------
# Enrichment logic
# ---------------------------------------------------------------------------


def _enrich(source_text: str, source_language: str, language: str) -> dict:
    """Generate enrichment data.  Falls back to stub on any failure."""
    if not _llm_ready or _llm is None:
        return _stub_enrich(source_text, source_language, language)

    user_prompt = _build_user_prompt(source_text, source_language, language)

    last_exc = None
    for attempt in range(2):
        try:
            completion = _llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=LLM_MAX_TOKENS,
                temperature=0.3,
            )
            raw = completion["choices"][0]["message"]["content"]
            parsed = _parse_enrichment_json(raw)
            return _coerce_result(parsed, source_text)
        except ValueError as exc:
            # JSON parse failure — do NOT retry, a second run probably also
            # produces garbage.  Log and stub out.
            _logger.warning(
                "LLM JSON parse failed (attempt %d): %s — falling back to stub.",
                attempt + 1,
                exc,
            )
            return _stub_enrich(source_text, source_language, language)
        except Exception as exc:
            last_exc = exc
            _logger.warning(
                "LLM generation error (attempt %d): %s",
                attempt + 1,
                exc,
            )
            time.sleep(1)

    _logger.error("LLM generation failed after retries: %s — falling back to stub.", last_exc)
    return _stub_enrich(source_text, source_language, language)


def _stub_enrich(source_text: str, source_language: str, language: str) -> dict:
    """Return clearly-marked stub enrichment so the event flow is testable."""
    prefix = f"[stub:{source_language}→{language}]"
    return {
        "synonyms": [f"{prefix} synonym1", f"{prefix} synonym2"],
        "antonyms": [f"{prefix} antonym1", f"{prefix} antonym2"],
        "example_sentences": [
            f"{prefix} Example sentence using '{source_text}'.",
            f"{prefix} Another example with '{source_text}'.",
            f"{prefix} A third example for '{source_text}'.",
        ],
        "explanation": (
            f"{prefix} No real explanation available — LLM not loaded. " f"Text: '{source_text}'"
        ),
    }


# ---------------------------------------------------------------------------
# RabbitMQ consumer thread
# ---------------------------------------------------------------------------

_consumer_alive = False


def _publish(channel, queue_name: str, payload: dict):
    """Declare queue (idempotent) and publish a JSON message."""
    import pika

    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )


def _process_message(channel, method, properties, body):
    """Handle one enrichment.requested message."""
    message = {}
    try:
        message = json.loads(body)
        job_id = message.get("job_id", "")
        payload = message.get("payload", {})

        source_text = payload.get("source_text", "")
        source_language = payload.get("source_language", "en")
        language = payload.get("language", source_language)

        _logger.info(
            "Processing job_id=%s %s→%s text='%s'",
            job_id,
            source_language,
            language,
            source_text,
        )

        result = _enrich(source_text, source_language, language)

        _publish(
            channel,
            QUEUE_COMPLETED,
            {
                "job_id": job_id,
                "payload": result,
            },
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
        _logger.info("Completed job_id=%s", job_id)

    except Exception as exc:
        job_id = message.get("job_id", "?") if message else "?"
        _logger.error("Failed job_id=%s: %s", job_id, exc)
        try:
            _publish(
                channel,
                QUEUE_FAILED,
                {
                    "job_id": message.get("job_id", "") if message else "",
                    "payload": {"error": str(exc)},
                },
            )
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def _consumer_thread():
    """Background thread: connect to RabbitMQ and consume enrichment.requested."""
    global _consumer_alive
    import pika

    while True:
        try:
            credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
            params = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=credentials,
                heartbeat=30,
                blocked_connection_timeout=10,
            )
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_IN, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_IN, on_message_callback=_process_message)
            _consumer_alive = True
            _logger.info(
                "LLM enrichment consumer started. llm_ready=%s. Waiting for messages…",
                _llm_ready,
            )
            channel.start_consuming()
        except Exception as exc:
            _consumer_alive = False
            _logger.warning("RabbitMQ connection lost: %s — reconnecting in 5s", exc)
            time.sleep(5)


# ---------------------------------------------------------------------------
# Model loader thread — keeps FastAPI responsive while the model loads
# ---------------------------------------------------------------------------


def _loader_thread():
    """Run _init_llm() off the request path so /health is immediately usable."""
    global _llm_ready
    _llm_ready = _init_llm()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    loader = threading.Thread(target=_loader_thread, daemon=True, name="llm-loader")
    loader.start()
    consumer = threading.Thread(target=_consumer_thread, daemon=True, name="enrichment-consumer")
    consumer.start()
    yield


app = FastAPI(
    title="Lexora LLM Enrichment Service",
    description=(
        "Local CPU-only LLM enrichment service (llama-cpp-python + Qwen2.5 GGUF). "
        "Falls back to stub when the model cannot be loaded."
    ),
    version="1.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "llm",
        "llm_ready": _llm_ready,
        "consumer_alive": _consumer_alive,
        "model_repo": LLM_MODEL_REPO,
        "model_filename": LLM_MODEL_FILENAME,
    }


# ---------------------------------------------------------------------------
# Sync roleplay endpoint (no RabbitMQ — direct HTTP call from Odoo controller)
# ---------------------------------------------------------------------------


class RoleplayMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class RoleplayRequest(BaseModel):
    system_prompt: str
    history: list[RoleplayMessage] = []
    user_message: str
    target_language: str = "en"


_ROLEPLAY_WRAPPER = (
    "STRICT OUTPUT RULES — obey these before anything else:\n"
    "1. Maximum 2-3 sentences per reply. Stop after 3 sentences.\n"
    "2. NEVER repeat a sentence or phrase you already wrote in this conversation.\n"
    "3. Only correct SIGNIFICANT mistakes (wrong tense, wrong word). "
    "Ignore minor errors like missing articles.\n"
    "4. When you correct, add ONE note at the very end only: [Correction: X → Y]\n"
    "5. Never list multiple corrections. Never correct the same thing twice.\n"
    "6. Stay in character. Respond naturally as your character would.\n\n"
)


def _roleplay(req: RoleplayRequest) -> str:
    lang_name = LANG_NAMES.get(req.target_language, req.target_language)
    wrapper = _ROLEPLAY_WRAPPER
    system_content = wrapper + "\n\n" + req.system_prompt

    messages = [{"role": "system", "content": system_content}]
    for msg in req.history[-10:]:  # keep last 10 messages to stay within context
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.user_message})

    if not _llm_ready or _llm is None:
        return (
            f"[stub: LLM not loaded] I understand you said: '{req.user_message}'. "
            f"Let's continue our conversation in {lang_name}!"
        )

    try:
        completion = _llm.create_chat_completion(
            messages=messages,
            max_tokens=200,
            temperature=0.7,
            repeat_penalty=1.15,
        )
        return completion["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        _logger.warning("Roleplay generation error: %s", exc)
        return "I'm sorry, I couldn't respond right now. Please try again!"


@app.post("/roleplay")
def roleplay_endpoint(req: RoleplayRequest):
    reply = _roleplay(req)
    return {"status": "ok", "reply": reply}


# ---------------------------------------------------------------------------
# Sync grammar explainer endpoint (M28 — no RabbitMQ, direct HTTP from Odoo)
# ---------------------------------------------------------------------------

_GRAMMAR_SYSTEM_PROMPT = (
    "You are a linguistics expert. Explain the grammar of the given phrase in exactly "
    "2 sentences. State what grammatical rule applies and why the phrase is structured "
    "this way. Be concise. Reply in the same language as the phrase."
)


class GrammarExplainRequest(BaseModel):
    phrase: str
    language: str = "en"


def _explain_grammar(phrase: str, language: str) -> str:
    """Return a 2-sentence grammar explanation.  Falls back to a stub when not loaded."""
    if not _llm_ready or _llm is None:
        return "LLM not ready — try again in 30 s."

    messages = [
        {"role": "system", "content": _GRAMMAR_SYSTEM_PROMPT},
        {"role": "user",   "content": f'Explain the grammar of: "{phrase}"'},
    ]
    try:
        result = _llm.create_chat_completion(
            messages=messages,
            max_tokens=150,
            temperature=0.3,
            repeat_penalty=1.1,
        )
        explanation = result["choices"][0]["message"]["content"].strip()
        return explanation or "Could not generate an explanation."
    except Exception as exc:
        _logger.error("explain-grammar failed: %s", exc)
        return ""


@app.post("/explain-grammar")
def explain_grammar_endpoint(req: GrammarExplainRequest):
    if not req.phrase or not req.phrase.strip():
        return {"status": "error", "explanation": ""}
    explanation = _explain_grammar(req.phrase.strip(), req.language)
    status = "ok" if explanation and not explanation.startswith("LLM not ready") else "unavailable"
    return {"status": status, "explanation": explanation}


# =============================================================================
# M30 — AI Speaking Coach: topic generation + speech analysis
# =============================================================================
#
# Two sync endpoints used by /my/speaking:
#   POST /generate-topic   → one B1 conversation starter in the requested language
#   POST /analyze-speech   → grammar corrections + synonym suggestions + improved
#                            version of a transcribed speech sample (JSON-only)
#
# Both endpoints share the language-agnostic pattern from /roleplay and
# /explain-grammar: LANG_NAMES.get(req.language, req.language) puts the human
# language name in the prompt; the model replies in that language.
# Stub fallback when _llm_ready=False so the portal never wedges.
# =============================================================================


class GenerateTopicRequest(BaseModel):
    language: str = "en"


_TOPIC_SYSTEM_PROMPT = (
    "You generate ONE short open-ended speaking-practice topic per request. "
    "Output exactly one sentence (8-15 words). No preamble, no list, no quotes."
)

# Few-shot anchor per language. The 1.5B model needs this to reliably reply
# in the right script — naming the language alone is not enough.
_TOPIC_EXAMPLES = {
    "en": "Example: What is the best advice you have ever received?",
    "uk": "Приклад: Яка найкорисніша порада, яку ви отримали в житті?",
    "el": "Παράδειγμα: Ποιά είναι η πιο πολύτιμη συμβουλή που έχεις πάρει;",
    "pl": "Przykład: Jaka jest najlepsza rada, jaką kiedykolwiek otrzymałeś?",
}


def _generate_topic(language: str) -> str:
    lang_name = LANG_NAMES.get(language, language or "English")

    if not _llm_ready or _llm is None:
        # Stub: language-appropriate placeholder so the UI flows cleanly
        # while the model is still loading.
        stubs = {
            "en": "Describe your favourite season and why you enjoy it.",
            "uk": "Розкажіть про вашу улюблену пору року та чому вона вам подобається.",
            "el": "Περιγράψτε την αγαπημένη σας εποχή και γιατί σας αρέσει.",
            "pl": "Opowiedz o swojej ulubionej porze roku i dlaczego ją lubisz.",
        }
        return stubs.get(language, stubs["en"])

    example = _TOPIC_EXAMPLES.get(language, _TOPIC_EXAMPLES["en"])
    user_content = (
        f"Write a new B1-level speaking topic in {lang_name}. Use the same "
        f"language and script as the example below, but pick a DIFFERENT subject. "
        f"Output ONLY the new topic — no example, no translation.\n\n"
        f"{example}\n\n"
        f"New topic in {lang_name}:"
    )

    messages = [
        {"role": "system", "content": _TOPIC_SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]
    try:
        result = _llm.create_chat_completion(
            messages=messages,
            max_tokens=80,
            temperature=0.8,
            repeat_penalty=1.1,
        )
        topic = result["choices"][0]["message"]["content"].strip()
        # Strip surrounding quotes the model sometimes adds.
        if topic.startswith(('"', "“", "«")) and topic.endswith(('"', "”", "»")):
            topic = topic[1:-1].strip()
        return topic or "Tell me about your favourite memory."
    except Exception as exc:
        _logger.error("generate-topic failed: %s", exc)
        return "Tell me about your favourite memory."


@app.post("/generate-topic")
def generate_topic_endpoint(req: GenerateTopicRequest):
    topic = _generate_topic(req.language)
    return {"status": "ok", "topic": topic, "language": req.language}


# -----------------------------------------------------------------------------


class AnalyzeSpeechRequest(BaseModel):
    transcript: str
    language: str = "en"
    topic: str | None = None


_ANALYZE_SYSTEM_PROMPT = (
    "You are a language-learning coach analysing a student's spoken response. "
    "Reply with a JSON object (and ONLY a JSON object — no preamble, no markdown) "
    "in this exact shape:\n"
    "{\n"
    '  "corrections": [{"wrong": "...", "correct": "...", "note": "..."}],\n'
    '  "synonyms":    [{"original": "...", "suggestion": "...", "reason": "..."}],\n'
    '  "improved":    "..."\n'
    "}\n"
    "Rules:\n"
    "1. corrections: at most 5 grammar / tense / agreement fixes. Skip minor "
    "things; focus on what a B1 learner most needs.\n"
    "2. synonyms: at most 5 better word choices. For each, include the original "
    "word, a stronger or more natural replacement, and a one-sentence reason.\n"
    "3. improved: a single rewritten version of the student's response that fixes "
    "all corrections and adopts the suggested synonyms. Keep the same meaning.\n"
    "4. ALL string values must be in the same language as the student's transcript.\n"
    "5. If the transcript has no errors, return empty arrays and copy the original "
    "into 'improved' unchanged."
)


def _analyze_speech(transcript: str, language: str, topic: str | None) -> dict:
    """Return {corrections, synonyms, improved}. Stub on _llm_ready=False."""
    if not _llm_ready or _llm is None:
        return {
            "corrections": [],
            "synonyms": [],
            "improved": transcript,
            "stub": True,
        }

    lang_name = LANG_NAMES.get(language, language or "English")
    user_lines = [f"Student transcript (in {lang_name}):", transcript.strip()]
    if topic:
        user_lines.insert(0, f"Topic: {topic.strip()}")
    user_content = "\n\n".join(user_lines)

    messages = [
        {"role": "system", "content": _ANALYZE_SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]

    try:
        result = _llm.create_chat_completion(
            messages=messages,
            max_tokens=512,
            temperature=0.4,
            repeat_penalty=1.1,
            response_format={"type": "json_object"},
        )
        raw = result["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        _logger.error("analyze-speech generation failed: %s", exc)
        return {"corrections": [], "synonyms": [], "improved": transcript, "error": str(exc)}

    try:
        parsed = _parse_enrichment_json(raw)  # tolerant JSON parser shared with /enrich
    except Exception as exc:
        _logger.error("analyze-speech JSON parse failed: %s — raw=%r", exc, raw[:200])
        return {"corrections": [], "synonyms": [], "improved": transcript, "parse_error": True}

    corrections = parsed.get("corrections") or []
    synonyms    = parsed.get("synonyms")    or []
    improved    = parsed.get("improved")    or transcript

    # Defensive normalisation — make sure each list entry is a dict with str values.
    def _coerce_list(items, keys):
        out = []
        if not isinstance(items, list):
            return out
        for it in items[:5]:
            if not isinstance(it, dict):
                continue
            row = {k: str(it.get(k, "") or "").strip() for k in keys}
            if any(row.values()):
                out.append(row)
        return out

    return {
        "corrections": _coerce_list(corrections, ("wrong", "correct", "note")),
        "synonyms":    _coerce_list(synonyms,    ("original", "suggestion", "reason")),
        "improved":    str(improved).strip() if improved else transcript,
    }


@app.post("/analyze-speech")
def analyze_speech_endpoint(req: AnalyzeSpeechRequest):
    transcript = (req.transcript or "").strip()
    if not transcript:
        return {"status": "error", "message": "Empty transcript",
                "corrections": [], "synonyms": [], "improved": ""}
    if len(transcript) > 4000:
        transcript = transcript[:4000]
    result = _analyze_speech(transcript, req.language, req.topic)
    result["status"] = "ok"
    return result
