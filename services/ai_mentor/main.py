# ---------------------------------------------------------------------------
# M26 — Lexora AI Mentor (Helpdesk RAG Service)
#
# CPU-only FastAPI service providing two capabilities:
#   1. POST /ingest  — embed documents and store in pgvector
#   2. POST /answer  — RAG pipeline: embed query → pgvector ANN → LLM synthesis
#
# Architecture:
#   - Embeddings: fastembed + BAAI/bge-small-en-v1.5 (33 MB ONNX, 384-dim)
#   - Vector store: pgvector table in the shared Postgres container
#   - LLM generation: llama-cpp-python + Qwen2.5-1.5B-Instruct Q4_K_M (default)
#   - Odoo calls POST /answer on every new helpdesk ticket creation
#   - Response injected into ticket chatter as OdooBot message by Odoo
# ---------------------------------------------------------------------------

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
import requests as _requests
from fastapi import FastAPI, HTTPException
from fastembed import TextEmbedding
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from pgvector.psycopg2 import register_vector
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ai_mentor] %(levelname)s %(message)s")
_logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────

_PGVECTOR_HOST = os.getenv("PGVECTOR_HOST", "postgres")
_PGVECTOR_PORT = int(os.getenv("PGVECTOR_PORT", "5432"))
_PGVECTOR_DB   = os.getenv("PGVECTOR_DB", "lexora")
_PGVECTOR_USER = os.getenv("PGVECTOR_USER", "odoo")
_PGVECTOR_PASS = os.getenv("PGVECTOR_PASS", "odoo")

_LLM_MODEL_REPO     = os.getenv("LLM_MODEL_REPO", "Qwen/Qwen2.5-1.5B-Instruct-GGUF")
_LLM_MODEL_FILENAME = os.getenv("LLM_MODEL_FILENAME", "qwen2.5-1.5b-instruct-q4_k_m.gguf")
_LLM_MODEL_DIR      = os.getenv("LLM_MODEL_DIR", "/models/llm")
_LLM_N_CTX          = int(os.getenv("LLM_N_CTX", "2048"))
_LLM_N_THREADS      = int(os.getenv("LLM_N_THREADS", "0"))  # 0 = auto
_LLM_MAX_TOKENS     = int(os.getenv("LLM_MAX_TOKENS", "400"))
_LLM_AUTO_DOWNLOAD  = os.getenv("LLM_AUTO_DOWNLOAD", "1") == "1"

_EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
_EMBED_DIM   = int(os.getenv("EMBED_DIM", "384"))

_RAG_TOP_K     = int(os.getenv("RAG_TOP_K", "5"))
_RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.30"))

# ── Global state ───────────────────────────────────────────────────────────

_llm: Llama | None = None
_embedder: TextEmbedding | None = None
_llm_ready = False
_embeddings_ready = False
_pgvector_ok = False

# ── pgvector helpers ───────────────────────────────────────────────────────

def _get_db_conn():
    conn = psycopg2.connect(
        host=_PGVECTOR_HOST, port=_PGVECTOR_PORT, dbname=_PGVECTOR_DB,
        user=_PGVECTOR_USER, password=_PGVECTOR_PASS,
    )
    register_vector(conn)
    return conn


def _init_pgvector():
    global _pgvector_ok
    for attempt in range(10):
        try:
            conn = _get_db_conn()
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ai_mentor_docs (
                        id       SERIAL PRIMARY KEY,
                        content  TEXT NOT NULL,
                        metadata JSONB DEFAULT '{}',
                        embedding vector(%s)
                    );
                """, (_EMBED_DIM,))
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS ai_mentor_docs_emb_idx
                        ON ai_mentor_docs
                        USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 50);
                """)
            conn.commit()
            conn.close()
            _pgvector_ok = True
            _logger.info("pgvector ready — ai_mentor_docs table initialised")
            return
        except Exception as exc:
            _logger.warning("pgvector init attempt %d/10 failed: %s", attempt + 1, exc)
            time.sleep(5)
    _logger.error("pgvector init failed after 10 attempts — vector search will not work")


# ── Embeddings ─────────────────────────────────────────────────────────────

def _init_embeddings():
    global _embedder, _embeddings_ready
    try:
        _logger.info("Loading fastembed model: %s", _EMBED_MODEL)
        _embedder = TextEmbedding(model_name=_EMBED_MODEL)
        # Warm up
        list(_embedder.embed(["warmup"]))
        _embeddings_ready = True
        _logger.info("fastembed ready — model %s loaded", _EMBED_MODEL)
    except Exception as exc:
        _logger.error("fastembed init failed: %s", exc)


def _embed(texts: list[str]) -> list[list[float]]:
    if not _embedder:
        raise RuntimeError("Embeddings not ready")
    return [list(v) for v in _embedder.embed(texts)]


# ── LLM ───────────────────────────────────────────────────────────────────

def _resolve_model_path() -> str:
    model_dir = Path(_LLM_MODEL_DIR)
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / _LLM_MODEL_FILENAME
    if model_path.exists():
        return str(model_path)
    if not _LLM_AUTO_DOWNLOAD:
        raise FileNotFoundError(
            f"Model file {model_path} not found and LLM_AUTO_DOWNLOAD=0"
        )
    _logger.info("Downloading %s from %s …", _LLM_MODEL_FILENAME, _LLM_MODEL_REPO)
    downloaded = hf_hub_download(
        repo_id=_LLM_MODEL_REPO,
        filename=_LLM_MODEL_FILENAME,
        local_dir=str(model_dir),
    )
    _logger.info("Model downloaded to %s", downloaded)
    return downloaded


def _init_llm():
    global _llm, _llm_ready
    try:
        path = _resolve_model_path()
        _logger.info("Loading LLM from %s (n_ctx=%d) …", path, _LLM_N_CTX)
        kwargs: dict[str, Any] = dict(
            model_path=path,
            n_ctx=_LLM_N_CTX,
            verbose=False,
        )
        if _LLM_N_THREADS > 0:
            kwargs["n_threads"] = _LLM_N_THREADS
        _llm = Llama(**kwargs)
        _llm_ready = True
        _logger.info("LLM ready — %s", _LLM_MODEL_FILENAME)
    except Exception as exc:
        _logger.error("LLM init failed: %s", exc)


# ── RAG helpers ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You are Lexora Support, a helpful assistant for the Lexora language-learning platform. "
    "Answer the user's support question based on the provided knowledge context. "
    "Be concise (2-4 sentences), friendly, and actionable. "
    "If the context does not contain enough information, say so honestly and suggest the user contact the team directly."
)


def _retrieve(query: str, top_k: int = _RAG_TOP_K) -> list[dict]:
    """Return top_k relevant document chunks from pgvector."""
    if not _pgvector_ok or not _embeddings_ready:
        return []
    try:
        vec = _embed([query])[0]
        conn = _get_db_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT content, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM   ai_mentor_docs
                ORDER  BY embedding <=> %s::vector
                LIMIT  %s;
            """, (vec, vec, top_k))
            rows = cur.fetchall()
        conn.close()
        return [
            {"content": r["content"], "metadata": r["metadata"], "score": float(r["score"])}
            for r in rows
            if float(r["score"]) >= _RAG_MIN_SCORE
        ]
    except Exception as exc:
        _logger.error("pgvector retrieval failed: %s", exc)
        return []


def _generate(subject: str, description: str, context_chunks: list[dict]) -> str:
    if not _llm_ready or not _llm:
        return _stub_reply(subject)

    context_text = "\n\n".join(
        f"[{i+1}] {c['content']}" for i, c in enumerate(context_chunks)
    ) if context_chunks else "No specific knowledge context available."

    user_msg = (
        f"Support ticket:\nSubject: {subject}\n\n{description}\n\n"
        f"---\nKnowledge context:\n{context_text}"
    )

    try:
        result = _llm.create_chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=_LLM_MAX_TOKENS,
            temperature=0.4,
            repeat_penalty=1.1,
        )
        reply = result["choices"][0]["message"]["content"].strip()
        return reply if reply else _stub_reply(subject)
    except Exception as exc:
        _logger.error("LLM generation failed: %s", exc)
        return _stub_reply(subject)


def _stub_reply(subject: str) -> str:
    return (
        f"Thank you for contacting Lexora Support regarding: \"{subject}\". "
        "Our team has received your ticket and will respond shortly. "
        "In the meantime, you can browse our Grammar Guide and Vocabulary sections for self-service help."
    )


# ── Seed initial knowledge ─────────────────────────────────────────────────

_SEED_DOCS = [
    {
        "content": (
            "Adding words to Lexora: Go to My Vocabulary, click '+ Add Word', "
            "enter the word or phrase, and select the source language. "
            "Translations to your learning languages are automatically requested. "
            "You can also add words via the browser extension by right-clicking selected text."
        ),
        "metadata": {"topic": "vocabulary", "action": "add_word"},
    },
    {
        "content": (
            "Practising vocabulary: Visit /my/practice for spaced repetition (SM-2 algorithm). "
            "Cards are shown based on your recall history. "
            "Grading yourself Hard, Good, or Easy adjusts the next review interval automatically."
        ),
        "metadata": {"topic": "practice", "action": "srs"},
    },
    {
        "content": (
            "PvP Arena word duels: Navigate to /my/arena and click 'New Challenge'. "
            "You need at least 10 vocabulary entries with completed translations to participate. "
            "You can challenge Lexora Bot if no human opponent is available within 60 seconds."
        ),
        "metadata": {"topic": "pvp", "action": "duel"},
    },
    {
        "content": (
            "Anki import: Go to /my/anki and upload an .apkg or .txt file. "
            "Select the source language and optionally a destination language. "
            "Duplicates are automatically detected and skipped. "
            "Imported audio from .apkg files is attached to the entries."
        ),
        "metadata": {"topic": "import", "action": "anki"},
    },
    {
        "content": (
            "AI Translator: The /translator page provides instant translations between "
            "English, Ukrainian, and Greek using Google Translate. "
            "Click 'Add to Vocabulary' on any translation result to save it to your list."
        ),
        "metadata": {"topic": "translator", "action": "translate"},
    },
    {
        "content": (
            "Browser extension: Install the Lexora Chrome extension and set the Lexora URL "
            "in extension Options. Right-click any selected text on a webpage and choose "
            "'Add to Lexora' to capture words with surrounding context. "
            "On YouTube, subtitle words become clickable for instant definitions."
        ),
        "metadata": {"topic": "extension", "action": "capture"},
    },
    {
        "content": (
            "XP and levels: You earn XP by completing practice reviews, winning duels, "
            "and completing grammar exercises. XP is spent in the XP Shop (/my/shop) "
            "on items like Streak Freeze, Profile Frames, and Double XP Booster."
        ),
        "metadata": {"topic": "gamification", "action": "xp"},
    },
    {
        "content": (
            "Roleplay scenarios: Visit /my/roleplay and choose a scenario (café, job interview, "
            "doctor, hotel, airport, market). The AI acts as a native speaker and provides "
            "grammar corrections inline. Sessions are saved so you can continue later."
        ),
        "metadata": {"topic": "roleplay", "action": "ai_conversation"},
    },
    {
        "content": (
            "Account and login: Lexora uses Odoo's authentication system. "
            "If you forget your password, use the 'Forgot password' link on the login page. "
            "Your language preferences (native language, learning languages) can be set at /my/profile."
        ),
        "metadata": {"topic": "account", "action": "login"},
    },
    {
        "content": (
            "Grammar Guide: Visit /grammar for the Grammar Encyclopedia covering "
            "all 12 English tenses, irregular verbs, articles, conditionals, modal verbs, "
            "and passive voice. Each section can be printed as a PDF cheat sheet."
        ),
        "metadata": {"topic": "grammar", "action": "encyclopedia"},
    },
]


def _seed_if_empty():
    """Insert initial knowledge docs if the table is empty."""
    if not _pgvector_ok or not _embeddings_ready:
        _logger.warning("Skipping seed — pgvector or embeddings not ready")
        return
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ai_mentor_docs;")
            count = cur.fetchone()[0]
        if count > 0:
            _logger.info("ai_mentor_docs already has %d documents — skipping seed", count)
            conn.close()
            return

        _logger.info("Seeding %d initial knowledge documents …", len(_SEED_DOCS))
        texts = [d["content"] for d in _SEED_DOCS]
        vectors = _embed(texts)
        with conn.cursor() as cur:
            for doc, vec in zip(_SEED_DOCS, vectors):
                cur.execute(
                    "INSERT INTO ai_mentor_docs (content, metadata, embedding) VALUES (%s, %s, %s);",
                    (doc["content"], json.dumps(doc["metadata"]), vec),
                )
        conn.commit()
        conn.close()
        _logger.info("Seeded %d documents into pgvector", len(_SEED_DOCS))
    except Exception as exc:
        _logger.error("Seed failed: %s", exc)


# ── FastAPI app ────────────────────────────────────────────────────────────

app = FastAPI(title="Lexora AI Mentor", version="1.0.0")


@app.on_event("startup")
def startup():
    threading.Thread(target=_init_pgvector, daemon=True, name="pgvector-init").start()
    threading.Thread(target=_init_embeddings, daemon=True, name="embed-loader").start()
    threading.Thread(target=_init_llm, daemon=True, name="llm-loader").start()
    # Seed after both pgvector and embeddings are ready
    threading.Thread(target=_wait_and_seed, daemon=True, name="seeder").start()


def _wait_and_seed():
    for _ in range(120):
        if _pgvector_ok and _embeddings_ready:
            _seed_if_empty()
            return
        time.sleep(5)
    _logger.warning("Seed timed out waiting for pgvector + embeddings")


# ── Request/response models ────────────────────────────────────────────────

class AnswerRequest(BaseModel):
    ticket_id: int
    subject: str
    description: str
    language: str = "en"


class AnswerResponse(BaseModel):
    reply: str
    sources: list[dict] = []
    rag_used: bool = False


class IngestDocument(BaseModel):
    content: str
    metadata: dict = {}


class IngestRequest(BaseModel):
    documents: list[IngestDocument]


class IngestResponse(BaseModel):
    indexed: int


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ai_mentor",
        "llm_ready": _llm_ready,
        "embeddings_ready": _embeddings_ready,
        "pgvector_ok": _pgvector_ok,
        "llm_model": _LLM_MODEL_FILENAME,
        "embed_model": _EMBED_MODEL,
    }


@app.post("/answer", response_model=AnswerResponse)
def answer(req: AnswerRequest):
    _logger.info(
        "answer — ticket_id=%d subject=%r lang=%s",
        req.ticket_id, req.subject[:60], req.language,
    )
    query = f"{req.subject} {req.description}"
    chunks = _retrieve(query)
    _logger.info("retrieved %d chunks (top_k=%d)", len(chunks), _RAG_TOP_K)

    reply = _generate(req.subject, req.description, chunks)
    return AnswerResponse(
        reply=reply,
        sources=[{"content": c["content"][:120], "score": c["score"]} for c in chunks],
        rag_used=bool(chunks),
    )


@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    if not _pgvector_ok:
        raise HTTPException(status_code=503, detail="pgvector not ready")
    if not _embeddings_ready:
        raise HTTPException(status_code=503, detail="embeddings not ready")

    texts = [d.content for d in req.documents]
    vectors = _embed(texts)
    conn = _get_db_conn()
    with conn.cursor() as cur:
        for doc, vec in zip(req.documents, vectors):
            cur.execute(
                "INSERT INTO ai_mentor_docs (content, metadata, embedding) VALUES (%s, %s, %s);",
                (doc.content, json.dumps(doc.metadata), vec),
            )
    conn.commit()
    conn.close()
    _logger.info("Ingested %d documents", len(req.documents))
    return IngestResponse(indexed=len(req.documents))
