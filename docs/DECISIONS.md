# Lexora — Architecture Decision Records (MVP)

> Version: 0.1 (post-discovery)
> Last updated: 2026-04-13

---

## ADR-001: Single learning entry model with type field

**Status:** Accepted

**Context:** Learning entries can be words, phrases, collocations, or sentences. Two design paths: single model with `type` field vs. separate models with a shared base mixin.

**Decision:** Use a single `language.entry` model with a `type` field (`word`, `phrase`, `sentence`, `collocation`). Type-specific behavior (validation, display) is handled by field-level rules, not separate models.

**Reasoning:** Simpler data model, simpler imports, simpler dedup, simpler translation/enrichment/PvP flows. All types share the same relations to translations, enrichments, audio, and media. The type distinction is primarily UX labeling with minor validation differences.

**Consequences:** Type-specific branching must be kept lean. If a future type requires truly different fields or relations, extraction into subtypes is possible without breaking the MVP schema.

---

## ADR-002: Per-user deduplication, not global canonical entries

**Status:** Accepted

**Context:** Should learning entries be per-user (Alice and Bob each own their own "apple") or global (one canonical "apple" entry shared via a join table)?

**Decision:** Deduplication is per-user. Each user owns their own entry records. Global canonical entries are not implemented in MVP.

**Reasoning:** Per-user ownership is simpler, clearer for privacy, and fits the product model (personal learning history, personal audio, personal PvP usage). Global entries would complicate ownership, privacy, and deletion.

**Consequences:** Some data duplication across users (same word stored N times). Analytics must aggregate across all users' entries. Future global content reuse (e.g., shared audio for common words) would require adding a global reference model later.

---

## ADR-003: Dedup key = normalize(source_text) + source_language + owner_id

**Status:** Accepted

**Context:** What constitutes a duplicate entry?

**Decision:**
- Dedup key: `normalize(source_text) + source_language + owner_id`
- `type` is NOT part of the key
- Normalization: Unicode NFC, lowercase, trim whitespace, collapse internal spaces, normalize smart punctuation, strip trailing sentence-ending punctuation for dedup comparison
- On collision: skip + report count; do not overwrite existing data
- Import skipped items are logged persistently and reviewable

**Reasoning:** Excluding `type` prevents the same word being duplicated under different type labels. Moderate normalization prevents noisy duplicates without over-collapsing distinct expressions.

---

## ADR-004: Learning entries are private by default with opt-in sharing

**Status:** Accepted

**Context:** Should user vocabulary lists be public, private, or configurable?

**Decision:** Private by default. Users can opt in to share their whole list or individual entries. Shared entries are viewable and copyable by other Language Users. Copied entries gain new ownership.

**Reasoning:** Privacy is the safe default. Social sharing is a product feature, not the product's default posture. Provenance metadata is stored on copied entries.

---

## ADR-005: Source language auto-detected with user confirmation

**Status:** Accepted

**Context:** How is the source language of a manually entered word determined?

**Decision:** System auto-detects language from typed text; prefills the language dropdown. If confidence is low, falls back to the user's `default_source_language` preference. User must confirm or correct before saving. Submission is blocked if language is unset.

**Reasoning:** Silent auto-save is too risky (wrong language breaks translation direction, dedup, PvP). Fully manual is too friction-heavy for a learning app. Confirm-and-correct is the right balance.

**For Anki imports:** User confirms source language at import time; no per-card auto-detection in MVP.

---

## ADR-006: Anki formats — .apkg (required) and .txt (required); .csv and .colpkg deferred

**Status:** Accepted

**Context:** Which Anki export formats to support in MVP?

**Decision:** `.apkg` and `.txt` (tab-separated) are required for MVP. `.csv` and `.colpkg` are documented as future extensions.

**Field mapping:** Auto-detect Front/Back convention for `.apkg`; fall back to user-provided mapping UI if ambiguous.

**Media in .apkg:** Attempt to extract embedded audio and attach to entries. Images are ignored. Failed media extraction must not block text import.

---

## ADR-007: Four async worker services

**Status:** Accepted

**Context:** The product prompt left audio as a possible 4th service, conditional on discovery.

**Decision:** Four worker services, all async via RabbitMQ:
1. Translation (Argos Translate)
2. LLM Enrichment (Qwen3 8B)
3. Anki Import
4. Audio / TTS (piper / espeak-ng, offline-first)

**Reasoning:** TTS generation can be slow (especially on CPU). Synchronous generation would block the Odoo request cycle. Consistency with the translation/enrichment pattern simplifies the job status model. A 5th dedicated PvP service is deferred (PvP orchestration stays in Odoo + Redis).

---

## ADR-008: Audio — both recording and TTS; offline-first; Odoo filestore storage

**Status:** Accepted

**Context:** Which audio modes, storage model, and TTS approach?

**Decision:**
- Both user-recorded and auto-generated TTS in MVP
- TTS: local/offline-first (piper → espeak-ng → Coqui TTS). No cloud API calls required for MVP
- Storage: Odoo filestore (`ir.attachment`). No external object storage in MVP
- User recordings: stored permanently on upload
- Generated TTS: lazily generated once, stored permanently
- Max upload: ~10 MB (configurable system parameter)
- Known limitation: Greek TTS quality is weaker than English/Ukrainian

---

## ADR-009: PvP — Odoo bus + Redis for real-time; no dedicated PvP service in MVP

**Status:** Accepted

**Context:** PvP requires real-time per-round state and countdown synchronization.

**Decision:** Option B: Odoo bus/WebSocket for UI event delivery; Redis for ephemeral battle state (matchmaking queue, round state, countdown, reconnect grace). Odoo is the authoritative persistence layer. No 5th dedicated PvP service in MVP.

**Reasoning:** Odoo bus handles the UI notification layer. Redis handles the sub-second ephemeral state that Odoo's ORM is not designed for. This avoids introducing a 5th service while still giving PvP the real-time correctness it needs.

---

## ADR-010: PvP matchmaking by language pair only; 60s timeout; bot at medium difficulty

**Status:** Accepted

**Context:** Matchmaking criteria, timeout, and bot behavior.

**Decision:**
- Match by `(practice_language, native_language)` only. No skill brackets in MVP.
- Wait 60 seconds for a real opponent; then start a bot battle.
- Bot: configurable difficulty (easy/medium/hard); default medium (~60% correct).
- Bot battles count in player history and win rate.
- Minimum 10 entries in practice language (configurable system parameter) to enter any battle.

---

## ADR-011: PvP distractor selection — own dictionary first, then shared fallback pool

**Status:** Accepted

**Context:** Where do the 3 distractor translation options in each round come from?

**Decision:** Distractors come from the player's own dictionary first (translations of other entries in the same practice language). If insufficient, fill from a system-level shared fallback pool (a small curated table of common words per language). Opponent's dictionary is NOT used.

**Round display:** Show source entry text + 4 translation options (1 correct translation + 3 distractor translations).

---

## ADR-012: PvP disconnection — 15s reconnect grace, then forfeit

**Status:** Accepted

**Context:** What happens when a player's connection drops mid-battle?

**Decision:** A 15-second Redis TTL key serves as the reconnect grace period. If the player does not reconnect: forfeit, opponent awarded the win, result saved in history. Battle is not deleted.

---

## ADR-013: Posts require moderator approval before publishing

**Status:** Accepted

**Context:** Who can publish posts/articles?

**Decision:** Any Language User can create drafts and submit for review. Publishing requires moderator approval. Moderators and Admins can publish directly.

**Reasoning:** Fully open publishing risks early spam/noise. Draft-and-review balances user-generated content with content quality control. Trusted-user auto-publish is a future enhancement (OD-11).

---

## ADR-014: "Copy to my list" auto-triggers translation

**Status:** Accepted

**Context:** After copying text from a post/chat into the learning list, should translation be automatic?

**Decision:** Yes. Translation is enqueued automatically after a copy-to-list save (same as manual entry save). Enrichment remains a separate manual action.

---

## ADR-015: Chat — public channels and private DMs; inline save-to-list

**Status:** Accepted

**Context:** What chat modes are in scope?

**Decision:** Both public channels and private DMs. Start DM from user profile. "Save to my list" inline popup is available from chat message text. Moderators handle public channels; DMs are private unless a message is reported.

---

## ADR-016: No Elasticsearch in MVP stack

**Status:** Accepted

**Context:** The original README included Elasticsearch. The product prompt called it optional.

**Decision:** Remove Elasticsearch from the active MVP Docker Compose. Use PostgreSQL and Odoo ORM for all dashboard analytics and search. Add Elasticsearch later as a read-model layer if SQL performance becomes inadequate.

**Reasoning:** ES requires significant RAM (2+ GB just for the container), increases operational complexity, and is not needed for MVP query volumes. SQL + fuzzy search (pg_trgm via `base_search_fuzzy`) is sufficient for MVP.

---

## ADR-017: Data retention — delete private data, anonymize community contributions

**Status:** Accepted

**Context:** What happens to user data when an account is deleted?

**Decision:**
- Private learning entries: hard delete
- User-recorded audio tied to deleted entries: delete from filestore
- Chat messages (public): anonymize author to "Deleted User"; content retained
- Posts/articles: anonymize ownership; admin decides whether to keep published
- PvP battle history: anonymize player identity; match records retained for opponent history integrity
- Leaderboard: user removed from public visibility
- Import logs: deleted with the account

GDPR right-to-erasure is treated as a real product requirement. The MVP implementation is pragmatic, not a full legal compliance platform.

---

## ADR-018: UUID job_id on every async event for idempotency

**Status:** Accepted

**Context:** RabbitMQ can redeliver messages on failure. Workers must not create duplicate results.

**Decision:** Every event payload carries a `job_id` (UUID, generated by Odoo at publish time). Workers check for a completed job before processing. Completed job re-delivery → no-op with logging. Odoo-side status machine: `pending → processing → completed / failed`. Workers ack only after durable write.

---

## ADR-019: PvP leaderboard — win count ranked, per language pair views

**Status:** Accepted

**Context:** What ranking system for the leaderboard?

**Decision:** Win count is the primary ranking. Win rate is displayed alongside. Language-pair-specific leaderboard views. No ELO in MVP. Minimum battle count before appearing in certain ranking views is configurable. ELO is a future enhancement.

---

## ADR-020: `language.lang` lookup model for learning_languages

**Status:** Accepted (M2)

**Context:** `language.user.profile.learning_languages` needs to store a set of language codes.
Options: (A) JSON Char field, (B) three Boolean fields, (C) Many2many to a lookup model.

**Decision:** Option C — `language.lang` model with `code` + `name`, seeded with uk/en/el. Profile has `Many2many → language.lang`. Selection fields on `language.entry` (source_language etc.) remain as Odoo `Selection` fields since they are scalar values, not sets.

**Reasoning:** Consistent Odoo idiom, trivially extensible if more languages are added. Avoids mixed approach (Selection scalar vs. JSON for the same concept). M3 iterates `profile.learning_languages` to enqueue translation jobs.

---

## ADR-021: Portal vocabulary views in `language_words`, not `language_portal`

**Status:** Accepted (M2)

**Context:** PLAN §M2 explicitly lists "Portal views" as `language_words` work. ARCHITECTURE assigns portal views to `language_portal`.

**Decision:** Follow PLAN for M2 — portal controller and Qweb templates for vocabulary live in `language_words` (adding `portal` as a dependency). `language_portal` remains the home for posts/articles/copy-to-list UI (M7+).

**Reasoning:** The vocabulary portal is tightly coupled to the `language.entry` model. Co-locating controller + model in the same module reduces cross-module coupling for this slice. `language_portal` will house UI that spans multiple models (posts, chat, copy-to-list).

---

## ADR-022: `langdetect` for source language auto-detection; SPEC fallback applies

**Status:** Accepted (M2)

**Context:** SPEC §4.1 requires auto-detection of source language with fallback to `default_source_language` when confidence is low.

**Decision:** Use `langdetect==1.0.9` (added to `base-requirements.txt`). Detection threshold: 0.7 probability for one of the three supported codes (en/uk/el). Below threshold → return None → UI falls back to user's `default_source_language`.

**Known limitation:** Single-word detection is unreliable (e.g., "яблуко" may be classified as Russian due to Cyrillic character overlap). This is inherent to `langdetect` for short texts. The UI always allows manual correction. This is within the scope of SPEC §4.1 ("user reviews/corrects the language"). Documented as a known limitation.

---

## ADR-023: Odoo-side RabbitMQ consumer — cron-based basic_get draining

**Status:** Accepted (M3)

**Context:** Odoo needs to consume translation result events from RabbitMQ (`translation.completed`, `translation.failed`). Options: (A) persistent background thread, (B) cron-based polling with `basic_get`.

**Decision:** Option B — a scheduled cron action runs every minute, opens a `BlockingConnection`, drains up to 200 messages per queue using `basic_get` (polling), then closes the connection. Handler processes each message and acks after durable write.

**Reasoning:** Persistent threads in Odoo workers are complex to manage (worker restarts, multiple workers competing). Cron-based draining is idiomatic Odoo, predictable, and sufficient for MVP translation volumes (low throughput). `basic_get` is safe in a synchronous context, unlike `basic_consume` which requires an event loop.

**Consequences:** Up to ~60s latency between translation completion and Odoo DB update. Acceptable for MVP. If sub-second latency is needed in future, a dedicated consumer process should be added.

---

## ADR-024: Translation service fallback stub when Argos not installed

**Status:** Accepted (M3)

**Context:** Argos Translate requires downloading language packages at startup (~200 MB), which slows dev container start significantly.

**Decision:** Translation service attempts to install Argos packages on startup. If `argostranslate` is not importable (not in the container image) or package download fails, the service falls back to a stub that returns `[stub:src→tgt] <source_text>`. The health endpoint reports `argos_ready: false`.

**Reasoning:** Dev and CI can run the full stack without a multi-GB model download. Production containers rebuild with argostranslate installed. The stub makes the async event flow testable end-to-end without real translation.

**Consequences:** Stub translations are clearly marked and not production-quality. Anyone running the dev stack sees stub output until Argos packages are installed.

---

## ADR-025: LLM service stub fallback; portal enrichment via QWeb inheritance

**Status:** Accepted (M4)

**Context:** Same two questions as M3: (1) how to run the LLM service without loading a multi-GB model in dev, (2) where to put the portal enrichment UI.

**Decision:**
- LLM service starts a daemon consumer thread immediately; `_init_llm()` returns False in dev (no model loaded). `_enrich()` falls back to `_stub_enrich()` which returns clearly-marked `[stub:src→lang]` data. `/health` reports `llm_ready: false, consumer_alive: true`.
- Portal enrichment section is implemented as a QWeb template in `language_enrichment/views/portal_enrichment.xml` that inherits `language_words.portal_vocabulary_detail`. This keeps `language_enrichment` self-contained without modifying `language_words`.
- Enrichment is user-triggered only (not auto on entry create), unlike translation. The portal "Enrich with AI" button POSTs to `/my/vocabulary/<id>/enrich`, which calls `_enqueue_single(entry, entry.source_language)`.

**Reasoning:** Same reasoning as ADR-024 for the stub. QWeb inheritance is cleaner than modifying the parent template because enrichment is a separate feature layer; the parent module (`language_words`) shouldn't need to know about enrichment. Tests revealed that the test user must have `group_language_user` (not just `base.group_user`) to pass `check_access` on `language.entry` create — matching the M3 test pattern exactly.

---

## ADR-026: LLM inference is CPU-only; no GPU assumed for MVP

**Status:** Accepted (M4 — post-implementation correction)

**Context:** ARCHITECTURE.md originally said "A GPU or large RAM (≥16 GB) is recommended." The target server is CPU-only with no GPU.

**Decision:** The LLM enrichment service is designed for CPU-only operation. The recommended model for production use is **Qwen2.5 1.5B or 3B** (INT8 or FP32, ≤3 GB RAM), loadable via `transformers` with `torch` CPU backend, or equivalently via `llama-cpp-python` with a `.gguf` checkpoint. Qwen3 8B INT4 via `llama-cpp-python` is supported on machines with ≥16 GB RAM but is slower (~30–120s per request). Unquantized Qwen3 8B in FP16/FP32 on CPU is explicitly out of scope — memory and latency requirements are impractical.

**Consequences:** In stub mode (current dev default), enrichment results are fake but the full async event pipeline is exercised. To activate real inference: implement `_init_llm()` and `_enrich()` in `services/llm/main.py` and rebuild the image with the chosen model's pip dependencies. No Dockerfile or compose changes are needed beyond adding packages to a `requirements-full.txt`. ARCHITECTURE.md, SPEC.md, and `services/llm/main.py` have been updated to reflect CPU-first reality.

---

## ADR-027: Real CPU-only LLM runtime — llama-cpp-python + Qwen2.5-1.5B-Instruct GGUF (M4b)

**Status:** Accepted (M4b, revised 2026-04-18 for target server constraints)

**Context:** ADR-026 locked in "CPU-first, no GPU". M4b makes the enrichment service actually run a real model instead of returning stubbed data. The concrete runtime and model must be pinned so image builds are reproducible and future maintainers can reason about RAM, latency, and licence implications without re-deriving the decision.

**Target server profile:** Ubuntu 24.04 x86_64 KVM · Intel Xeon E5-2680 v2 (Ivy Bridge-EP, AVX but **no AVX2**) · 6 vCPUs @ 2.8 GHz · **8 GiB RAM total** · no GPU. Other services co-resident on the same host: Odoo (4 workers ~1.5–2 GiB), PostgreSQL (~0.5–1 GiB), RabbitMQ Erlang VM (~0.3 GiB), Redis, nginx, three other worker services. Realistic RAM budget for the LLM service: **~3–4 GiB with safety margin**.

**Decision:**
- Runtime: **`llama-cpp-python`** (installs the `llama.cpp` C++ engine via a Python wheel). Pinned in `services/llm/requirements.txt`.
- Default model: **`Qwen/Qwen2.5-1.5B-Instruct-GGUF`**, file `qwen2.5-1.5b-instruct-q4_k_m.gguf` (~0.95 GiB on disk, ~1.2 GiB resident during inference). Apache-2.0 licence.
- Model and filename are **env-configurable** (`LLM_MODEL_REPO`, `LLM_MODEL_FILENAME`). Operators with ≥16 GiB RAM can opt into Qwen2.5-3B-Instruct Q4_K_M (~2.5 GiB resident) without code changes.
- Delivery: model is **not baked into the image**. The container downloads it on first start via `huggingface_hub.hf_hub_download` into a Docker named volume `llm_models` mounted at `/models`. Subsequent restarts are fast.
- JSON shape is enforced at inference time with `response_format={"type":"json_object"}`; parse failures fall back to `_stub_enrich()` so the queue never wedges.
- `prefetch_count=1` (already set in M4) is preserved, so only one inference runs concurrently per worker — important on a 6-vCPU box where parallel inferences would thrash.

**Reasoning for revising default from 3B to 1.5B:**
- On the target server, 3B Q4_K_M at ~2.5 GiB resident would consume ~60 % of the LLM service's realistic RAM budget. Any memory spike from co-resident services pushes the host into swap, and on spinning/constrained KVM storage that cascades into stalls across Odoo.
- E5-2680 v2 is AVX-only (no AVX2). `llama.cpp` runs but loses ~30 % throughput vs AVX2 hosts. 3B latency under these conditions is ~30–90 s per enrichment — borderline unusable for an interactive button.
- 1.5B Q4_K_M at ~1.2 GiB resident leaves meaningful headroom and runs at ~10–30 s per enrichment on this CPU — slow but acceptable.
- 1.5B is noticeably weaker than 3B for antonyms and Greek. Accepted tradeoff: the enrichment output is clearly labelled AI-generated in the UI, and Greek weakness is already an open decision (OD-3) and documented SPEC limitation.

**Reasoning for llama-cpp-python over transformers:**
- **Smaller image than `transformers` + `torch` CPU.** `torch` CPU wheels are ~200 MB and pull in many transitive deps (fsspec, triton stubs, sympy, networkx). `llama-cpp-python` is a single C++ engine with a thin Python binding — the image delta is mostly `build-essential` + `cmake`, and only if no manylinux wheel is available for the pinned version.
- **Quantization is native.** `transformers` would require a separate quantization path (`bitsandbytes` or `optimum`) that does not play cleanly on CPU.
- **Grammar-constrained / JSON-mode sampling** is a first-class feature of `llama.cpp` and the primary safety net against small-model JSON hallucinations — the #1 production failure mode for this feature. `transformers` has no equivalent without extra libraries.

**Alternatives considered and rejected for M4b:**
- `transformers` + `torch` CPU with Qwen2.5-1.5B-Instruct — larger image, no native JSON grammar, and `torch` itself can briefly peak to 2 GiB on model load which is a worse fit for the 8 GiB host.
- `ctransformers` — less actively maintained; same GGUF backing anyway.
- Qwen2.5-3B Q4_K_M as default — too tight on 8 GiB.
- Qwen2.5-0.5B — small enough to fit easily but enrichment quality degrades to near-stub for Ukrainian/Greek antonym generation.
- Qwen3 8B INT4 — out of scope on an 8 GiB host.
- Cloud APIs (OpenAI / Anthropic) — explicitly out of scope per SPEC (offline-first) and user directive.

**Consequences:**
- Image build adds `build-essential`, `cmake`, `git` to the LLM service Dockerfile (~300 MB, pruned via apt cache cleanup). If `llama-cpp-python` at the pinned version publishes a manylinux x86_64 wheel for Python 3.11, pip prefers that and the build tools are only a safety net.
- First start downloads ~0.95 GiB from Hugging Face into the `llm_models` volume (much less than the 3B option). Documented in TASKS.md M4b plan and in `docker_compose/llm/docker-compose.yml` comments.
- `/health` now has a real `llm_ready:true` state once the model is loaded; in the download/load window it remains `false`.
- Greek enrichment quality remains a known limitation (SPEC §4.4, OD-3). M4b does not attempt to close that gap.
- Odoo-side contracts (event names, payload shape, `language.enrichment` state machine) are **unchanged**.
- Operators with headroom can switch to 3B by setting `LLM_MODEL_REPO=Qwen/Qwen2.5-3B-Instruct-GGUF` and `LLM_MODEL_FILENAME=qwen2.5-3b-instruct-q4_k_m.gguf` in their `.env`, then `make up-llm-no-cache`.

**Revisit triggers:**
- If 1.5B quality on the target server is too weak → try Q5_K_M of the same 1.5B (~0.3 GiB larger) before jumping to 3B.
- If first-boot download is too flaky → pre-seed the `llm_models` volume via an ops script (`huggingface-cli download …` on the host, then copy into the volume).
- If p95 latency exceeds ~40 s on the target host → consider increasing `n_threads`, reducing `n_ctx`, or disabling memory-mapped loading (`use_mmap=False` is heavier on RAM but skips page-in stalls).
- If Ivy Bridge AVX-only throughput turns out to be worse than projected → the model can be re-quantized to Q4_0 (~10 % faster than Q4_K_M on older CPUs, ~5 % lower quality).

**Local verification results (M4b-15 / M4b-16 / M4b-18, dev host — NOT the target server):**
- First-start cold download of `qwen2.5-1.5b-instruct-q4_k_m.gguf` from Hugging Face → ~90 s (~1.1 GiB payload). Load into `llama.cpp` completes shortly after; `/health` flips `llm_ready:false → true`.
- Warm restart (model already present in the `llm_models` volume): `llm_ready:true` in ~1 s.
- `apple` / `en`: ~14 s end-to-end round-trip through RabbitMQ, valid JSON, real synonyms / antonyms / 3 example sentences / 1 explanation paragraph. No `[stub:…]` prefix.
- `яблуко` / `uk`: ~6.6–7 s round-trip. JSON structure valid. Quality caveat: the 1.5B model repeated a placeholder example sentence ("Яблоко засушено") and rendered the explanation in Russian rather than Ukrainian — consistent with a small multilingual model and already documented in SPEC §4.4 and OD-3. Structure/pipeline is production-valid; quality is the 3B upgrade trigger.
- Expected server numbers (E5-2680 v2, AVX-only, 2.8 GHz, 6 vCPUs): p50 ≈ 15–40 s per enrichment; record the first real measurement once deployed.

---

## ADR-028: Translation pivot — free online API wrapper; LLM restricted to enrichment

**Status:** Accepted (M4c, 2026-04-18)

**Supersedes (in part):** ADR-024 (translation-service fallback stub while Argos was deferred) — Argos is now removed from the translation path entirely, not just deferred. ADR-023 (cron-based Odoo consumer) and ADR-018 (UUID idempotency) are unchanged.

**Context:** M4b deployed Qwen2.5-1.5B-Instruct Q4_K_M on the 8 GiB target server and confirmed two things:

1. The pipeline works end-to-end (source-language English enrichment is usable).
2. **Multilingual output is unusable for anything that has to be correct.** Real examples produced during server-side validation:

   | input | produced uk | produced el |
   |---|---|---|
   | vice versa | Віка універсальна | αντίστροφα |
   | prom | Пром | χορός |
   | arrogant | арган | αλαζόνας |
   | imminent | Іммінент | επικείμενη |
   | bedroll | Кошик | κλινοσκεπάσματα |
   | strut | труси | στρούτ |

   Greek is mostly acceptable. Ukrainian ranges from wrong ("арган") to actively misleading ("труси" = underwear). This is a data-level failure of the 1.5B model's Ukrainian capacity, not a prompt issue. Jumping to 3B or 8B to recover quality is impractical on an AVX-only 8 GiB host (ADR-027).

The other option — Argos Translate — carries its own well-known quality problems for Ukrainian/Greek, has no direct uk↔el model (two-hop routing, OD-2), and each language-pair package is ~150–200 MB on disk.

**Decision:**

1. **LLM Enrichment Service** is restricted to enrichment in the entry's **source language only**. It generates synonyms, antonyms, example sentences, and an explanation, all in the same language as the input. It is not responsible for translation. The service's JSON-output contract and event names are unchanged.
2. **Translation Service** switches from Argos Translate to a free online translation library. Default backend: **`deep_translator==1.11.4`** (MIT licence) with the `GoogleTranslator` provider. Fallback provider: `MyMemoryTranslator`, used automatically when Google returns a transient error or blocks the source IP.
3. Provider, per-request timeout, and fallback provider are configurable via env vars (`TRANSLATE_PROVIDER`, `TRANSLATE_TIMEOUT_SECONDS`, `TRANSLATE_FALLBACK_PROVIDER`) so switching to a paid backend (DeepL, Google Cloud, Azure Translator) in production is a one-line change.
4. The Translation Service remains a RabbitMQ worker. Event names (`translation.requested`, `translation.completed`, `translation.failed`), payload shape, and the `language.translation` state machine on the Odoo side are **unchanged**. Only `_translate()` and `services/translation/requirements.txt` change.

**Reasoning:**
- LLM-based translation at 1.5B has been empirically shown to be wrong in ways users cannot detect. Quality failures like "труси" for "strut" are not acceptable for a learning app where users trust the translation.
- Argos keeps the "offline" SPEC commitment but ships demonstrably weak Ukrainian/Greek output and heavy per-pair packages. The offline commitment was a means, not an end.
- Free community Google Translate wrappers (hit via `deep_translator`) produce production-grade translations for our three MVP languages, with sub-second latency, no API key, and no GPU. This is the highest-quality option available without introducing cost.
- `deep_translator` cleanly abstracts the provider behind a constructor arg. If Google starts blocking the server's IP, switching to MyMemory or DeepL is a one-line change — the consumer code is provider-agnostic.

**Trade-offs and risks (MUST surface in SPEC and in the portal "Known limitations" section):**
- **Internet dependency.** The Translation Service now requires outbound HTTPS to the configured provider. SPEC §4.3 must be amended — the "offline" commitment no longer holds for translation. Offline translation becomes a future enhancement, not a default.
- **ToS and rate limits.** `deep_translator`'s Google backend hits Google's public endpoint without an API key. Google has tolerated this pattern for years but does not formally permit it. The project's event-driven, one-entry-per-job pattern produces single-digit translations per second worst case, well within observed tolerance. If blocked, the MyMemory fallback kicks in automatically. For production, a paid API key is a trivial drop-in.
- **Privacy.** Entry text is sent to a third-party service. Acceptable for MVP (vocabulary is generally public content) but must be disclosed in SPEC §5. A privacy-sensitive deployment would swap the provider back to an offline engine.
- **Non-determinism.** Unlike Argos (deterministic), Google/MyMemory may return different text on different days. Translation records are created once per entry/target-language pair (existing UNIQUE constraint); re-runs only happen on explicit retry.

**Alternatives considered and rejected:**
- **`googletrans`** — historically unmaintained; breaks each time Google updates its endpoint. `deep_translator` is the community successor.
- **`translators` package** — supports more providers but has a quirkier API, less active changelog, and no clean constructor-level provider switch.
- **Keep Argos Translate.** Weak Ukrainian/Greek quality, no direct uk↔el pair, heavy image, offline commitment isn't worth the quality tax for MVP.
- **Translate via the LLM.** The trigger for this ADR.
- **Paid APIs as default (DeepL / Google Cloud / Azure).** Adds billing + config complexity for MVP. Supported as a future swap via `TRANSLATE_PROVIDER`.
- **Two-tier: LLM-first, free-API fallback.** Rejected — adds latency and complexity without improving quality.

**Consequences:**
- `services/translation/requirements.txt` pins `deep_translator==1.11.4`. No Argos packages anywhere.
- `docker_compose/translation/Dockerfile` stays on `python:3.11-slim` with no extra build tools (deep_translator is pure-Python + `requests`/`beautifulsoup4`, pip wheels only).
- `docker_compose/translation/docker-compose.yml` gains the `TRANSLATE_*` env vars with defaults.
- SPEC §4.3 rewritten to describe the online-API approach with the documented fallback chain.
- SPEC §4.4 clarified: enrichment is always in the entry's source language.
- OD-2 (Argos uk↔el quality) is resolved by **removal**, not improvement.
- Odoo-side contracts unchanged; no Odoo module updates required for the pivot.
- Existing 71 tests remain green (no schema or event change).

**Revisit triggers:**
- If Google starts rate-limiting or blocking: set `TRANSLATE_PROVIDER=mymemory` (already supported) and record the incident. If MyMemory also fails, acquire a paid Google Cloud / DeepL key and switch to the paid provider.
- If users report inaccurate translations: evaluate DeepL as a paid drop-in. Its quality for Slavic/Greek is generally better than free Google.
- If a privacy-sensitive or air-gapped deployment emerges: fork a separate offline translation service; the online path remains the default for the hosted product.
- If `deep_translator` itself goes unmaintained: `translators` is the second-choice library; the `_translate()` function is small enough to swap in a morning.

---

## ADR-029: Polish (`pl`) as a first-class language; canonical Selection import; auto-translate to all supported languages

**Status:** Accepted (M29, 2026-05-03)

**Context:** Lexora MVP shipped with three languages — English (`en`), Ukrainian (`uk`), Greek (`el`). M29 adds Polish (`pl` / 🇵🇱) as a fully-integrated fourth language across DB, controllers, FastAPI services, browser extension, and portal templates. Three sub-decisions were locked during implementation.

### Sub-decision 29a: Polish vendor identifiers

| Concern | Choice | Rationale |
|---|---|---|
| Flag emoji | 🇵🇱 (U+1F1F5 U+1F1F1) | Standard regional indicator pair |
| MyMemory locale | `pl-PL` | Required region-tag format (verified in `deep_translator` supported list) |
| Edge TTS voice | `pl-PL-ZofiaNeural` | Female neural, consistent with `uk-UA-PolinaNeural` / `el-GR-AthinaNeural` convention |
| espeak-ng fallback | `-v pl` | Standard ISO code, works out of the box |
| `langdetect` | Native `pl` support | No new dependency required |
| Extension diacritic regex | `/[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/` (BEFORE the `'en'` fallback) | Cyrillic→uk and Greek→el branches stay first (script-exclusive); Polish triggers only when no other Slavic/Greek script is present |

Google's `GoogleTranslator` (the default provider in `services/translation/main.py`) accepts the bare `pl` code — no provider-side change needed. The MyMemory locale only matters when the fallback path activates.

### Sub-decision 29b: Canonical `LANGUAGE_SELECTION` import (post-mortem, the bug that almost broke M29)

**The bug:** Three modules — `language_translation`, `language_enrichment`, `language_audio` — each defined their own local `LANGUAGE_SELECTION = [...]` literal at module level. Their Selection fields used `selection=LANGUAGE_SELECTION` (local reference, not import). When M29 Step 1 added `('pl', 'Polish')` to the canonical constant in `language_words.models.language_lang`, the three local copies stayed at three entries. The bug stayed dormant until the M29 backfill tried to create `language.translation` rows with `target_language='pl'` and Odoo's Selection validator rejected every one with `Wrong value for language.translation.target_language: 'pl'`.

**The fix:** All three local literals replaced with:

```python
from odoo.addons.language_words.models.language_lang import LANGUAGE_SELECTION
```

This makes `language_words.models.language_lang.LANGUAGE_SELECTION` the **single source of truth** for the four-language Selection across all five modules that consume it (`language_words`, `language_translation`, `language_enrichment`, `language_audio`, plus the inline `[(...)]` literals in `language_pvp.models.language_duel`, `language_portal.models.language_post`, `language_idiom`, `language_scenario`, `language_scenario_session`, `language_words.models.language_word_of_day`).

**Rule for future language additions:** any new `Selection` field that should track the supported-language set MUST `from odoo.addons.language_words.models.language_lang import LANGUAGE_SELECTION` — never copy the literal locally. The remaining inline `[(...), ...]` literals in PvP/portal/idiom/scenario/word-of-day models are tolerated but flagged in `docs/TASKS.md` for a future cleanup pass; they were updated by hand during M29 Step 1 and don't currently drift.

**Why it happened:** the duplicates predate M29 (translation/enrichment/audio were authored standalone in M3/M4/M6 before the canonical constant became the convention). Step 1 used a `grep '('en', 'uk', 'el')'` sweep that picked up _value_ tuples but not _named-constant references_. A future-proof grep would also search for `LANGUAGE_SELECTION = \[`.

### Sub-decision 29c: Auto-translate every new entry to all 4 supported languages (changed from `profile.learning_languages`)

**Before M29:** `language.entry.create()` enqueued translations only for the languages listed in the owner's `language.user.profile.learning_languages` (Many2many → `language.lang`). If a user hadn't ticked Polish on their profile, new entries never got Polish translations.

**After M29:** `_enqueue_translations()` in `language_translation.models.language_entry_translation` iterates over a module-level `_DEFAULT_TARGET_LANGUAGES = ('en', 'uk', 'el', 'pl')` constant minus the source language. The user's `profile.learning_languages` no longer gates the translation request — it can still gate which translations are *displayed* in the UI (out of scope for M29).

**Same change applied to `_live_translate()`** in `language_portal/controllers/portal_api.py` (the synchronous path used by the browser extension's Quick Look overlay): `[:2]` cap raised to `[:3]` and the `profile.learning_languages` lookup removed. Now the extension always shows all three non-source translations.

**Rationale:** Polish (and any future language) should be covered out of the box. The previous design coupled translation _coverage_ with user _preferences_ — adding a language meant 100% of existing users had to update their profile to actually see it. The new design separates the two concerns: data layer covers everything, presentation layer can filter later.

**Trade-off:** every entry creation now enqueues 3 translation jobs instead of N (where N = profile size, typically 1-2). RabbitMQ + Google Translate handle this comfortably (~1 s per call). Cost on the dev host is negligible; production should monitor Google API rate limits if entry creation volume spikes.

### Backfill discipline

The M29 backfill enqueued 1055 Polish translations for active non-Polish entries via the existing `_enqueue_single` (idempotent — re-runs are safe). All 1055 drained to `status='completed'` via the standard RabbitMQ → Translation Service → cron-drain pipeline (ADR-023). Sample results were correct: `book → książka`, `arrogant → arogancki`, `imminent → nadciągający`. No special migration tooling needed — the existing translation infrastructure handled the bulk task.

### Revisit triggers

- If a fifth language is added: extend `LANGUAGE_SELECTION` in `language_words.models.language_lang` and `_DEFAULT_TARGET_LANGUAGES` in `language_entry_translation`. Cleanup pass on the inline `[(...)]` literals in PvP/portal models is also overdue.
- If translation API rate-limits become a problem under high entry-creation volume: revert sub-decision 29c partially — keep `_DEFAULT_TARGET_LANGUAGES` for the data layer but throttle/queue the actual translation requests.
- If users want per-language opt-out: re-introduce `profile.learning_languages` as a *display* filter, not a translation filter.

---

## ADR-030: Synchronous record-transcribe-analyze pipeline for the AI Speaking Coach (M30)

**Status:** Accepted (M30, 2026-05-06)

**Context:** M30 introduces `/my/speaking`, a portal page where a user records oral practice in any of the four supported languages (en/uk/el/pl), receives a transcript from Faster-Whisper, and gets grammar/synonym/improved-version feedback from Qwen2.5-1.5B. The architectural question is the same one M17 (Roleplay) and M28 (Grammar Explainer) already faced: should this run through the existing RabbitMQ async machinery (translation, enrichment, audio jobs all use it), or as direct synchronous HTTP calls from the Odoo controller to the FastAPI services?

### Sub-decision 30a: Synchronous pipeline (no RabbitMQ)

**Decision:** All three stages run inline. The browser blocks on each step, the user sees a friendly progress message ("Transcribing…", "Analyzing…"), and total wall-clock from "Stop recording" to "feedback rendered" is on the order of 30 s.

```
Browser MediaRecorder → Stop
  → POST /my/speaking/transcribe (multipart, 120 s timeout)
       Odoo creates language.speaking.session row in status='transcribing'
       → POST audio_service /transcribe-sync (Faster-Whisper inline)
       ← {transcript, duration, language}
       Odoo persists transcript, flips status='analyzing'
  ← {session_id, transcript, duration, language}
  → POST /my/speaking/analyze (JSON-RPC, 90 s timeout)
       → POST llm_service /analyze-speech (Qwen2.5-1.5B chat completion)
       ← {corrections, synonyms, improved}
       Odoo persists feedback, flips status='completed'
  ← {corrections, synonyms, improved}
```

**Why sync, not async:**
1. **The conversation is one-shot.** A speaking session ends when the user clicks Stop. There is nothing else for the user to do during transcription or analysis — async makes the page poll for results that the user is staring at the whole time. The `/explain-grammar` endpoint chose sync for the same reason in M28; `/roleplay` chose sync for the same reason in M17.
2. **Latency is bounded.** Whisper `base` int8 transcribes 90 s of audio in ~10-20 s on the target host; Qwen2.5-1.5B at `temperature=0.4`, `max_tokens=512` returns analysis JSON in ~15-30 s. Both fit inside reasonable HTTP timeouts (120 s for transcription, 90 s for analysis). The async event-bus pattern would not get the result faster — it would just defer it through three extra hops (publish → consume → publish-back → consume-back) plus the RabbitMQ cron-drain latency from ADR-023.
3. **Failure recovery is simpler.** The session row is pre-created in `status='transcribing'` so a mid-flow failure leaves a visible row the user can see and retry. With async, a wedged consumer could leave the user staring at a spinner forever. The sync path lets the controller catch service-level errors (HTTP 413/415/503) and surface them directly with a meaningful message.
4. **No new infrastructure.** Both endpoints (`/transcribe-sync`, `/analyze-speech`, `/generate-topic`) are added to the existing audio_service and llm_service containers. No new container, no new RabbitMQ queue, no new cron. The audio service reuses the already-loaded `faster_whisper.WhisperModel`; the LLM service reuses the already-loaded `llama_cpp.Llama`.

**Trade-off — what we give up:**
- The browser holds an open HTTP connection for up to ~30 s during analysis. On a flaky mobile network this is more fragile than firing a job and polling. Acceptable for MVP — the page is desktop-first (mic recording UX) and an explicit error message on timeout is clearer than a silent failure.
- A long-running analysis can in theory wedge a single Odoo worker. With `workers=4` and `prefetch_count=1` on the LLM container, the practical concurrency ceiling is fine for the expected user count.

**Pattern reuse rule:** any future feature whose user can't proceed until the AI result is back **should be sync**. Translation, enrichment, audio-generation, and Anki-import all involve a user who can keep using the app while the job runs — those stay async via RabbitMQ.

### Sub-decision 30b: Three-key JSON contract for `/analyze-speech`

**Decision:** The LLM service's `/analyze-speech` endpoint returns:

```json
{
  "status": "ok",
  "corrections": [{"wrong": "...", "correct": "...", "note": "..."}],
  "synonyms":    [{"original": "...", "suggestion": "...", "reason": "..."}],
  "improved":    "..."
}
```

Three top-level keys, three independent panels in the UI. Empty arrays mean "nothing to fix" — the panel is hidden via `d-none` instead of showing "0 corrections" or `null`.

**Enforcement:** the LLM call uses `response_format={"type":"json_object"}`. The system prompt explicitly names the three keys, caps each list at 5 items, and demands ALL string values in the same language as the transcript (so a Polish speaker sees Polish corrections and reasons).

**Tolerance:** the same `_parse_enrichment_json` parser shared with `/enrich` is used. On parse failure (the 1.5B model occasionally emits Python-style single quotes inside JSON strings on Slavic input), the endpoint returns the original transcript as `improved` with empty arrays — UI never wedges. This is documented in TASKS.md M30-S2-04 and is the upgrade trigger to Qwen2.5-3B (ADR-027 revisit). The browser surfaces a `parse_error: true` flag so a future UI can show a "limited analysis" notice if needed.

**Defensive normalisation in the FastAPI handler:** `_coerce_list` accepts only the whitelisted keys per row, drops empty rows, and caps each list at 5 entries. This means a malformed-but-parseable LLM response can't crash the controller or inject unexpected fields into the database.

### Sub-decision 30c: Audio cap at 90 seconds, env-configurable

**Decision:** `AUDIO_SYNC_MAX_SECONDS=90` (soft cap, duration-based) and `AUDIO_SYNC_MAX_BYTES=15728640` (15 MB hard guard, byte-based) on `/transcribe-sync`. Both env-configurable in `docker_compose/audio/docker-compose.yml`.

**Why two caps:**
- The byte cap rejects pathological uploads before Whisper ever opens the file — cheap O(1) guard.
- The duration cap is enforced after Whisper's pre-pass (`info.duration`), so a low-bitrate 90 s clip is accepted while a high-bitrate 30 s clip that exceeds 15 MB is rejected upfront. Different attack surfaces.

The browser-side recorder has no hard JS-level cap — the UI just shows "⏱ Max recording time: 90 seconds — Whisper auto-stops past this limit" so users have a clear expectation, and the server-side rejection (HTTP 413 with a friendly detail message) is the authoritative limit. The duration is reported back to the browser so the UI can display "transcript ready (12.3 s, EN)".

### Sub-decision 30d: Few-shot anchor for `/generate-topic`

**Decision:** The topic-generation prompt uses a per-language few-shot example (`_TOPIC_EXAMPLES` dict in `services/llm/main.py`). Naming the language alone (e.g. "Generate one B1-level topic in Greek") was not enough for Qwen2.5-1.5B — initial smoke tests produced Greek and Ukrainian topics in English text. The few-shot anchor closes that gap by giving the model a concrete in-language example to mimic.

This is consistent with the M18-FIX-09 prompt-engineering rule: 1.5B models pattern-match on examples far more reliably than they follow descriptive instructions. Future language additions only need to add one entry to `_TOPIC_EXAMPLES`.

### Lessons that fed back into the codebase

- **Canonical Selection import (ADR-029) extended.** `language.speaking.session.target_language` imports `LANGUAGE_SELECTION` from `language_words.models.language_lang`, so adding a fifth language is still a one-line change in one file.
- **`post_update_hook` discipline.** During M30 we found that `language_portal._fix_library_menu_parents` had been silently crashing on `env['website.website']` (the model is `'website'` in this Odoo build). Other modules' child menus were broken on website 2 for who knows how long. Fixed defensively with a registry-membership check, and `post_update_hook` now also runs the menu re-parenter so future child menus auto-attach to per-website parents on `--update`. **Rule:** `post_update_hook` must run every idempotent fixer, not only the seeders.
- **QWeb interpolation gotcha.** `t-attf-class="badge #{ {dict}.get(...) }"` is invalid in Odoo 18 — the inner braces of a dict literal collide with the `#{...}` interpolation parser. Use `t-att-class="'badge ' + {dict}.get(...)"` (Python expression form) for any class derived from a status enum.
- **Flexbox sandwich pattern (M28-12c) reused.** The Speaking Coach page reuses M28's two-zone card layout where the analysis output is in a scroll-body region. No new layout work needed.

### Revisit triggers

- If users want a longer cap (e.g. 3-minute monologues), bump `AUDIO_SYNC_MAX_SECONDS` and consider switching the LLM analysis to async-with-polling — a 3-minute Whisper pass plus 3-minute Qwen analysis exceeds reasonable HTTP timeouts.
- If `parse_error: true` rates climb (telemetry suggestion: log the rate over time), the upgrade to Qwen2.5-3B Q4_K_M (already configured behind env vars `LLM_MODEL_REPO` / `LLM_MODEL_FILENAME`) is the recommended fix. Server RAM permitting.
- If we ship a mobile / network-flaky variant, switch to a polling pattern: the sync endpoints stay, but the browser fires-and-checks via a session-status route instead of holding an open connection.

---

## ADR-031: Browser Extension AI Surfaces — Lexora Writer (M31) and Slang/Idiom Explainer (M32)

**Status:** Accepted (M31+M32, 2026-05-09)

**Context:** Two browser-extension features that share an architectural shape but address different user moments.

- **M31 Lexora Writer** — proactive grammar/style assistant: floating "L" FAB on every focused `<textarea>` / `[contenteditable]`; one-click sends the field text through `/lexora_api/writer_check` → `/analyze-writing` and renders corrections + improved version in a Shadow-DOM popup with an "Apply to text" button.
- **M32 Slang & Idiom Explainer** — reactive "what does this mean" affordance: new "💡 Explain Slang/Idiom" button alongside the existing M28 "Explain Grammar" button in both Quick Look and YouTube subtitle overlays; sends the selected phrase through `/lexora_api/explain_slang` → `/explain-slang` and renders kind / figurative / literal / example / confidence in an amber-themed block.

Both reuse the existing service stack — no new container, no new RabbitMQ queue, no new Pydantic patterns. This ADR records the four locked sub-decisions that define how M31 and M32 behave.

### Sub-decision 31a: Synchronous proxy chain (ADR-030 reapplied)

**Decision:** Both flows are synchronous browser → Odoo proxy → LLM. Browser blocks on each step; the user sees a "Looking up…" / "Analysing…" pill and the result lands ~15-30 s later.

```
Browser content.js / overlay.js
  → background.js fetch
  → POST /lexora_api/writer_check or /lexora_api/explain_slang
      (Odoo proxy: type='http', auth='none' + _require_session(),
       60 s requests.post timeout)
  → POST llm_service /analyze-writing or /explain-slang
      (FastAPI sync, Qwen2.5-1.5B chat completion, ~15-30 s)
  ← JSON contract
  ← Renders inside the same overlay surface; no page navigation
```

**Why the same rule as M30:** the user is staring at the result. There's no point queuing through RabbitMQ when the blocking call is the only thing the user is waiting on. A polling pattern would add complexity for zero perceived-latency benefit.

**Pattern reuse audit (locked at ADR-031):**

| Endpoint | Status field | Stub fallback | Defensive coerce | Few-shot anchor |
|---|---|---|---|---|
| `/roleplay` (M17) | inline | yes | n/a (free text) | n/a |
| `/explain-grammar` (M28) | inline | yes | n/a | n/a |
| `/generate-topic` (M30) | wrapper | yes | n/a (free text) | yes (`_TOPIC_EXAMPLES`) |
| `/analyze-speech` (M30) | wrapper | yes | yes | n/a |
| `/analyze-writing` (M31) | wrapper | yes | yes | yes (`_WRITING_EXAMPLES`) |
| **`/explain-slang` (M32)** | wrapper | yes | enum-clamped | yes (`_SLANG_EXAMPLES`) |

Every new sync endpoint MUST: (a) inject `status: "ok"` server-side; (b) provide a stub fallback that returns the same JSON shape with sentinel content when `_llm_ready=False`; (c) defensively coerce arrays / enums; (d) add a per-`{output_language}` few-shot anchor when the contract demands a specific language.

### Sub-decision 31b: Apply-to-text — the React/Vue write-back pattern

**Problem:** M31 needs to write the LLM's `improved` text back into the user's textarea or contenteditable. On React-controlled inputs (Reddit, Gmail compose, X/Twitter, GitHub PR descriptions, Notion), assigning `input.value = improved` directly fires React's overridden setter, which silently reverts the change because React's internal state hasn't been updated.

**Fix — the canonical "native input setter" pattern:**

```js
function _applyWriterImproved(input, improved) {
  if (input.tagName === 'TEXTAREA') {
    // Walk past React's wrapped setter to the prototype's native setter.
    const nativeSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype, 'value'
    )?.set;
    if (nativeSetter) {
      nativeSetter.call(input, improved);
    } else {
      input.value = improved;          // graceful fallback
    }
  } else if (input.isContentEditable) {
    input.innerText = improved;        // preserves line breaks
  }

  // Both events with bubbles:true so React/Vue/Svelte/Solid all notice.
  input.dispatchEvent(new InputEvent('input', {
    bubbles: true,
    inputType: 'insertReplacementText',
    data: improved,
  }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
}
```

**Why both events:** React 17+ listens to `input`; older single-page apps and form libraries listen to `change`. Dispatching both covers the long tail.

**Why `inputType: 'insertReplacementText'`:** browser InputEvents distinguish between user typing, paste, autocomplete, etc. Setting the `inputType` to `insertReplacementText` is the closest match and lets accessibility tooling render appropriate announcements.

**Test cases (verified during M31-S5):** Reddit comment box (React), Gmail compose (`[contenteditable]` + heavy framework), Odoo backend long-text fields (jQuery + custom widgets). All three pick up the change correctly. The Reddit character counter visibly updates after Apply — that's the unambiguous proof React's state actually rebound.

### Sub-decision 31c: FAB eligibility — strict allowlist over best-effort heuristic

**Problem:** the FAB cannot afford to be a nuisance. Showing it on a password field is a privacy bug; showing it on a code editor is annoying; showing it on a search bar is misleading.

**Decision:** strict allowlist with explicit deny patterns. `_isEligibleInput(el)` accepts only `tagName === 'TEXTAREA'` or `el.isContentEditable === true`, AND rejects when ANY of:

- `readonly` / `disabled` / `type=password` / `type=hidden`
- ancestor `[role="search"]`, role attrs `search` / `searchbox` / `spinbutton`
- code-editor heuristic — `aria-label` / `aria-describedby` / `className` matching `/code|monaco|cm[\-_]editor|codemirror|password|search/i`, plus closest-ancestor check against `.monaco-editor, .CodeMirror, .cm-editor, .ace_editor, [class*="code-editor"]`
- login/signup/password forms — parent `<form>` `name` / `id` / `action` matching `/login|sign[ \-]?in|signup|register|password/i`
- our own overlays — `closest('#lx-ql-shadow-host'), '#lx-writer-shadow-host', '.lx-yt-card', '.lx-known-word')`
- cross-document inputs (`el.ownerDocument !== document`)

**Why strict:** false positives on a password field or code editor cost the user trust permanently. False negatives (failing to show the FAB on a real writing surface) cost one click — the user can always paste into a known-good field. Tradeoff favours the user's privacy and editor experience.

**Failure mode if the deny list misses a new editor:** the FAB appears but the user can ignore it. Adding a new entry to `_WRITER_DENY_LABEL_RE` or the closest-ancestor selector list is a one-line patch. The Options-page toggle gives the user a global escape hatch.

### Sub-decision 31d: Privacy disclosure on the M31 popup

**Decision:** the M31 popup footer always shows the line *"Text is sent to your Lexora server for analysis."* in muted small text.

**Rationale:** unlike `/explain-grammar` (M28) where the user explicitly selects text and clicks a button, M31's FAB is **proactive** — it appears on every eligible field and the click sends the entire field value. Users typing personal messages on Reddit, drafting emails in Gmail, or composing in Odoo backends could otherwise be surprised that their text leaves the page. The disclosure removes that surprise.

**Why "your Lexora server" not "the cloud":** the extension talks to the user's own Lexora instance (configurable in Options). The phrasing is precise — the text doesn't leave the user's infrastructure unless they have explicitly pointed the extension at a third-party server.

**M32 doesn't add an equivalent disclosure** because the action is reactive (the user explicitly clicks the slang button on a phrase they just selected). Same model as `/explain-grammar`, no regression on the existing privacy posture.

### Sub-decision 31e: Server-side safety net for "improved differs but corrections is empty"

**Problem (browser smoke #2):** Qwen 1.5B reliably emits a polished `improved` but often returns an empty `corrections` array when its only edits were stylistic — even after three prompt-engineering iterations and the strengthened few-shot anchor pattern. The user sees their text change with no explanation.

**Decision:** post-process the LLM response in `_analyze_writing`. If whitespace-normalised `improved` differs from whitespace-normalised input AND `corrections` is empty, synthesise a single catch-all entry:

```python
{
  "wrong":   text,
  "correct": improved,
  "note":    "Polished for natural flow and clarity.",
}
```

Log an INFO line per synthesis so future telemetry / a 3B model upgrade can quantify how often the safety net fires (drops to near-zero is the signal that the upgrade is working).

**Rule for the broader stack:** when a 1.5B model fails to follow a structural rule that breaks UX, **don't fight the model — guarantee the contract server-side**. Prompt engineering is a 90 %-solution; server-side post-processing is the floor.

### Sub-decision 32a: Five-key JSON contract for `/explain-slang`

**Decision:** `/explain-slang` returns:

```json
{
  "kind":               "idiom" | "slang" | "phrasal_verb" |
                        "literal" | "unknown",
  "figurative_meaning": "...",
  "literal_meaning":    "...",
  "example":            "...",
  "confidence":         "high" | "medium" | "low"
}
```

Five top-level keys, two enum-clamped values, three free-text fields. The contract is enforced server-side via:

- `response_format={"type":"json_object"}` on the LLM call
- `_VALID_KINDS` and `_VALID_CONFIDENCES` module-level sets — defensive coerce in `_explain_slang` clamps unknown values to `"unknown"` / `"low"`
- The shared `_parse_enrichment_json` tolerant parser handles the Slavic single-quotes-in-JSON quirk (ADR-027 documented limitation)

### Sub-decision 32b: Dual language clamp — figurative/literal in `native_language`, example in `source_language`

**Decision:** the system prompt explicitly distinguishes:

- **Figurative meaning** and **literal meaning** are written in the user's **native_language** (the language they want the explanation IN)
- The **example sentence** stays in the phrase's **source_language** (so the user sees the phrase used naturally, not translated)
- The few-shot anchor (`_SLANG_EXAMPLES`) demonstrates this dual-clamp by always using "kick the bucket" with the figurative + literal in the target native language but the English example sentence kept verbatim across all four anchors

**Why the dual clamp matters:** a Polish user studying English idioms wants the explanation in Polish (so they understand it) but the example in English (so they see the idiom in its natural habitat). A single-language clamp would force a tradeoff.

### Sub-decision 32c: `kind:'literal'` UI branch — never invent a figurative reading

**Decision:** when `kind === 'literal'`, the renderer shows `"This phrase translates literally — no figurative meaning."` plus the literal translation. It does NOT render whatever the model put in `figurative_meaning` (which on the 1.5B model is sometimes a hallucinated "what this REALLY means" for a sentence that's just a sentence).

**Rationale:** showing a fake idiomatic reading for a literal phrase teaches the user something incorrect. Better to acknowledge "this is just a sentence" than to invent an idiom.

### Sub-decision 32d: `confidence:'low'` UI branch — surface the uncertainty

**Decision:** when `confidence === 'low'`, the renderer appends a small italic warning: *"⚠ AI is uncertain — consider checking a dictionary."*

**Rationale:** Qwen 1.5B is wobbly on regional slang and obscure idioms (the M32 smoke caught "give up" misclassified as `idiom` instead of `phrasal_verb`; "mog" Gen-Z slang produces low-confidence guesses). The honest UI affordance is to surface the uncertainty rather than render the answer with the same visual weight as a high-confidence answer.

### Lessons fed back into the codebase

- **Pattern reuse rule for sync endpoints (locked):** every new sync endpoint follows the table in 31a — Pydantic + system prompt + few-shot anchor (when output language is constrained) + `response_format={"type":"json_object"}` + `_parse_enrichment_json` + defensive coerce + stub fallback + server-side `status` injection.
- **Server-side floor over prompt-engineering ceiling:** when the 1.5B model can't be reliably out-prompted on a UX-critical rule, guarantee the contract in Python (M31's empty-corrections safety net is the canonical example).
- **Strict allowlist over best-effort denylist** for any DOM-injection feature: false positives erode trust faster than false negatives erode utility.
- **InputEvent + change pattern** is now the project's canonical write-back to controlled inputs; M32 doesn't need it (the slang button doesn't write into fields) but any future extension feature that does should reuse `_applyWriterImproved`'s shape.

### Revisit triggers

- **Increase Qwen to 3B** if `parse_error: true` rates climb on `/explain-slang` (Slavic JSON-quoting quirk) or if low-confidence rates dominate idiom queries. Server-side INFO log lines from the M31 safety net provide the metric.
- **Add a polling pattern** if M31 latency on the target server pushes past ~45 s p95 — the sync HTTP connection becomes fragile on flaky mobile networks beyond that.
- **Curated-idiom lookup ahead of the LLM** for M32: the M19 `language.idiom` table already has 100+ curated entries with high-quality figurative meanings. A future M-thirty-something could short-circuit `/explain-slang` for any phrase that matches a curated row, falling back to the LLM only for the long tail. M32 deliberately doesn't do this — keeping the milestone scope tight — but the architecture supports it.
- **Per-`(source_lang, native_lang)` few-shot anchors** if the cross-lingual quality gap widens: today `_SLANG_EXAMPLES` is keyed only by `native_language` (with the same English example sentence across all anchors). The 1.5B handles this fine; a 3B might benefit from anchors that vary the source language too.

---

## ADR-032: Webpage Shadowing — extension pronunciation practice (M33)

**Status:** Accepted (M33, 2026-05-09)

**Context:** M33 brings the M30 `/my/speaking` mic-and-feedback flow into the browser extension. A user reading any webpage can select a sentence, click "🎤 Practice Pronunciation", hear a perfect Edge TTS rendering, record themselves saying the same sentence, and receive a 0-100 score plus per-word red/amber annotations within ~30 seconds. This is the first browser-extension feature that records audio. The architectural risks (mic permission UX, structural diffing on a 1.5B model, browser hold-to-record reliability) all surfaced and were resolved during implementation. Six locked sub-decisions document what shipped and why.

### Sub-decision 32a: MV3 microphone strategy — `chrome.offscreen` Document API

**Problem:** content scripts run in the page's origin (`https://example.com`). `getUserMedia()` from a content script triggers a permission prompt **per origin**. A user practising shadowing on Wikipedia, Reddit, and a Polish news site would see the prompt three times. The recording would also be torn down on page navigation.

**Decision:** record audio in `chrome.offscreen` document at `chrome-extension://<id>/offscreen.html`. The offscreen page lives on the **extension's origin**, so:

- Mic permission is granted **once per extension**. Chrome remembers the grant for `chrome-extension://<id>/*` forever.
- Recording survives content-script tear-down (page navigation, tab refresh) — the offscreen doc is its own runtime context.
- Communication is via `chrome.runtime.sendMessage` from the service worker; content scripts never touch the recorder directly.

**Lifecycle:**
```
content.js: click "🎙 Start Recording"
  → bg.js: ensure offscreen exists
      if (!await chrome.offscreen.hasDocument()) {
        await chrome.offscreen.createDocument({
          url: 'offscreen.html',
          reasons: ['USER_MEDIA'],
          justification: 'Record speech for pronunciation practice'
        });
      }
  → bg.js → chrome.runtime.sendMessage({target:'offscreen', action:'mic-start'})
  → offscreen.js: getUserMedia + MediaRecorder.start()

content.js: click "⏹ Stop Recording"
  → bg.js → chrome.runtime.sendMessage({target:'offscreen', action:'mic-stop'})
  → offscreen.js: recorder.stop() → blob → base64 → response back to bg
  → bg.js → relays to content.js's sendResponse callback
```

**Alternatives considered and rejected:**

- **Hidden iframe injection.** Predates `chrome.offscreen` (Chrome 116+). Works on Chrome/Edge but is brittle on Firefox MV3 and on enterprise-locked Chromebooks where iframe injection is blocked by CSP. `chrome.offscreen` is the official MV3 path and the future-proof choice.
- **Popup-based recording.** Popups close when they lose focus. The original M33 plan considered hold-to-record (which would force the popup to stay open while the user's mouse was on the webpage); after the M33-S6-FIX2 pivot to click-to-toggle, the user clicks Stop on the same surface where they clicked Start, but the popup model would still tear the popup down between clicks if focus shifted.
- **Direct content-script `getUserMedia`.** The per-origin permission prompt is the showstopper.

**Manifest changes:** `"offscreen"` added to `permissions`. `host_permissions` unchanged — the offscreen doc is on the extension's own origin, no external host access needed.

### Sub-decision 32b: Mic-permission grant button on the Options page (M33-S6-FIX1)

**Problem found in user smoke:** Chrome auto-blocked `getUserMedia` in the offscreen document on first use with `NotAllowedError`. The permission prompt didn't appear — Chrome silently denied because the offscreen document had no UI surface where a permission prompt could be associated with a user gesture. The original M33-S4 implementation surfaced the error with a hint pointing to the Options page, but the Options page had nowhere to go.

**Decision:** add a "🎙️ Grant Microphone Permission" button to `options.html`. The Options page lives at `chrome-extension://<id>/options.html` — the same origin as `offscreen.html`. When the user clicks the button, `getUserMedia` runs **with a clear user gesture on a visible UI surface**, Chrome shows its standard permission prompt, and the resulting grant is shared by every page on the extension's origin (including the offscreen recorder). Tracks are stopped immediately after the grant lands so we don't leave the mic indicator on.

**Error UX:**
- `NotAllowedError`: shows the `chrome://extensions` → Details → Site permissions → Microphone reset path. Once Chrome has hard-denied, granting again requires a manual reset.
- `NotFoundError` / `OverconstrainedError`: hints at plugging in a microphone.
- Other errors: renders `<code>{err.name}</code>: {err.message}` via a defensive `_escHtml` helper.

**Why this matters:** the alternative (waiting for Chrome to fix the silent-block heuristic) is unbounded. Putting the grant on a visible UI page means the user always has a clear escape hatch when the offscreen recorder fails.

### Sub-decision 32c: Two Odoo proxy endpoints, not one

**Decision:** the orchestration is split across two distinct endpoints so neither one waits unnecessarily on the other:

- **`POST /lexora_api/shadow_tts`** — fetch reference TTS audio.
  - JSON body `{text, language}`. Forwards to audio-service `/tts-sync`.
  - Streams `audio/mpeg` bytes back to the extension; the browser plays an `<audio>` element directly from the response. **Not** wrapped in JSON.
  - 30 s timeout (Edge TTS is normally <1 s; 30 s is a safety bound).
- **`POST /lexora_api/shadow_evaluate`** — orchestrate transcription + evaluation.
  - Multipart body `audio + reference_text + language`.
  - Stage 1: forward audio to `/transcribe-sync` (M30, 120 s timeout).
  - Stage 2: send `{reference_text, transcript, language}` to `/evaluate-pronunciation` (NEW, 60 s timeout).
  - Returns combined JSON `{status, transcript, duration, detected_language, score, missed_words, mispronounced_words, feedback}`.

**Single-endpoint alternative considered:** one `/lexora_api/shadowing` with a `mode=tts | evaluate` flag returning audio-or-JSON depending on payload. Rejected because:

- Mixing binary and JSON responses on the same endpoint forces every caller to inspect `Content-Type` before parsing — uglier than two endpoints with single responsibilities.
- The Play-Original click happens before the user even records; bundling it into the evaluate endpoint would defer audio playback until after recording, breaking the listen-then-mimic learning flow.
- Two endpoints align with the existing M22-M32 proxy pattern (each `/lexora_api/*` route does one thing).

### Sub-decision 32d: Hybrid LLM model — deterministic word-diff is the source of truth, LLM only writes feedback

**Problem found during M33-S1 smoke:** Qwen 1.5B is unreliable at structural diffing. Three prompt iterations + few-shot anchors didn't fix it:

- Byte-identical input → returned `score=85` with literal `"..."` placeholder strings copied verbatim from the few-shot anchor.
- Multi-word divergence → misidentified which words were missed (claimed "lazy" missed when actually the second "the" was dropped).

**Decision:** **deterministic Python word-diff is authoritative** for `score / missed_words / mispronounced_words`. The LLM is consulted **only** for the localised `feedback` string (its actual strength). The 1.5B model's job is reduced to language-localised prose; the structural failure mode is bounded to "feedback is empty or wrong language", which the per-language `_FEEDBACK_FALLBACKS` template handles.

**Diff implementation highlights:**

- **Multiset-correct counting** via `collections.Counter`. The first-pass `set`-based version had a bug — reference `"the X the Y"` with one transcript `"the"` matched both reference `"the"`s against the single transcript token, missing the dropped second occurrence. Counter decrement fixes it.
- **Near-match heuristic**: Levenshtein distance ≤ 2 OR shared 3-character prefix → token classified as `mispronounced`. Distinct from `missed` (no match candidate at all).
- **`_has_target_language_chars`** script-validator on the LLM feedback string. Drift to wrong-script feedback is rejected and the per-language fallback substitutes.

**Same "fight the contract, not the model" rule** as M31's empty-corrections fix and M32's confidence clamping. When a 1.5B model can't be reliably out-prompted on a UX-critical structural rule, **guarantee the contract in Python**. Prompt engineering is a 90 %-solution; server-side post-processing is the floor.

**End-to-end smoke validation:** the proxy chain test fed `/shadow_tts` output (perfect English audio of `"The quick brown fox jumps over the lazy dog."`) back through `/shadow_evaluate` as the user's "recording". Whisper at 32 kbps low-bitrate transcribed it as `"The quick brown fox **dumps** over the lazy dog."` The deterministic diff caught the `jumps→dumps` substitution and returned `{score:89, mispronounced_words:["jumps"], feedback:"Great job!..."}`. **The safety net works even when both sides are AI-generated** — Whisper's own quirks are exactly what the diff machinery is for.

### Sub-decision 32e: Click-to-toggle, not hold-to-record (M33-S6-FIX2)

**Problem found in user browser smoke:** the M33-S5 first cut used `mousedown`/`mouseup` for hold-to-record. Recordings cut off after 1-2 seconds because:

- Micro mouse movements fired `mouseleave` (the cancel-with-autoStop branch).
- Tap-then-tap on touchscreens fired `touchend` between taps.
- Browser quirks on some platforms fire spurious `mouseup` events during scroll.

**Decision:** pivot to **click-to-toggle**. First click starts recording (label "⏹ Stop Recording", `.lx-recording` glow + pulse). Second click stops (label "Analysing…", disabled). Single `click` listener on the record button; no `mousedown` / `mouseup` / `mouseleave` / `touchstart` / `touchend` / `touchcancel` involvement.

**30 s safety auto-stop preserved** so a forgotten Stop click doesn't record forever. The auto-stop fires the same `_stopRecording()` code path as a manual click; status shows "Auto-stopped after 30 s — analysing…" so the user knows what happened.

**Why this matches user mental model better:** voice memo apps (iOS Voice Memos, WhatsApp voice messages, Telegram, Instagram) are all click-to-start / click-to-stop. Hold-to-record is a walkie-talkie metaphor that works for very short messages but breaks down for sentence-length practice (typically 3-10 seconds).

**General rule recorded:** when binding a UI affordance to an audio recorder that needs to stay alive longer than ~1 s, prefer toggle over hold. Hold is an invitation for spurious-event-class bugs.

### Sub-decision 32f: No persistence by default

**Decision:** M33 does NOT write shadowing attempts to `language.speaking.session` or any other model. Every record→evaluate cycle is ephemeral.

**Rationale:**

- The session model from M30 is portal-scoped; reusing it from the extension would require auth-bridging the session creation flow through the extension's session-cookie mechanism. Out of scope for M33.
- Users practising on the open web don't expect every word they say to be logged. Privacy-respecting default.
- An opt-in "Save to my pronunciation history" toggle is an obvious M-thirty-something extension; documented as a revisit trigger, not a milestone scope item.

**Trade-off:** users can't review their progress over time from the extension. The portal-side `/my/speaking` (M30) remains the persistent surface; users who want history-tracking practice there. The extension is the "any webpage" entry point for spontaneous practice.

### Lessons fed back into the codebase

- **Pattern reuse rule extended.** M33 adds two new sync endpoints (`/evaluate-pronunciation`, `/tts-sync`) to the table in ADR-031: same Pydantic + system prompt + few-shot anchor + `response_format={"type":"json_object"}` + tolerant parser + defensive coerce + stub fallback + server-side `status` injection. Eight sync endpoints across M17–M33 now follow the same shape.
- **Server-side floor over prompt-engineering ceiling** (M31/M33 reapplied). Three milestones now have a deterministic Python fallback layered behind the LLM (M31's full-text catch-all correction, M32's enum clamping + confidence floor, M33's word-diff). Each one was added in response to a real smoke failure, not pre-emptively.
- **Mic permission UX requires a visible UI gesture.** Offscreen documents alone aren't enough — the M33-S6-FIX1 mic-grant button on the Options page is the canonical pattern for any future feature that needs `getUserMedia`.
- **Toggle over hold for any non-trivial recorder.** Documented in 32e.

### Revisit triggers

- **Qwen 3B upgrade.** If feedback quality on Slavic / Greek input becomes a complaint, the LLM_MODEL_REPO env var swaps the model. The deterministic diff gives us a perfect telemetry signal — the rate at which `_llm_feedback` returns `""` (rejected by the language-drift validator) is exactly the quality metric to watch.
- **Polling pattern for flaky networks.** Total p50 latency is ~30-40 s (Whisper ~10-20 s + Qwen ~10-30 s). On a flaky mobile connection a single 40 s HTTP request is fragile. If users hit timeouts, the sync endpoints stay but the browser fires-and-checks via a session-status route.
- **Save-to-history opt-in.** Future milestone (32f).
- **Per-`(source_lang, native_lang)` few-shot anchors.** `_PRONUNCIATION_EXAMPLES` is currently keyed only by `native_language`. A 3B model might benefit from cross-lingual anchors when the source and native languages differ.

---

## ADR-033: YouTube Vocab Radar — passive look-ahead caption scanner (M34)

**Status:** Accepted (M34, 2026-05-16)

**Context:** M34 turns YouTube viewing into a passive vocabulary review surface. The
extension fetches the user's saved vocabulary once per page, intercepts the page's
own `/api/timedtext` caption request to get the whole subtitle track up front, and
when the player approaches a known word (~4 s ahead by default) auto-pauses the
video with a glassmorphism alert that surfaces translations and offers a
"⏪ Rewind 5 s & Play" affordance. The architectural questions to lock down for the
record: which vocab endpoint to expose, how to actually achieve look-ahead under
MV3, how to keep the radar non-intrusive on heavy users, where to put the overlay
DOM, how to match multi-word phrases, and whether to persist hits. Six sub-decisions
follow.

### Sub-decision 34a: Separate `/lexora_api/my_vocab` endpoint (not reusing M27's `/get_learned_words`)

**Decision:** New `GET /lexora_api/my_vocab` route on `LexoraApiController`.
Lightweight projection — `{id, word, normalized, lang, translations: {lang_code:
text}}` — with no SRS metadata. Hard cap `_MAX_RADAR_VOCAB = 1000`, env-overridable
via `LEXORA_RADAR_VOCAB_LIMIT`. Filter `owner_id = uid AND status='active' AND
pvp_eligible=True` so the radar always has at least one translation to show on hit.

**Why not reuse M27's `/get_learned_words`?** The two use-cases diverge enough that
bundling them would be a footgun:

| Concern | M27 review-in-the-wild | M34 YouTube radar |
|---|---|---|
| UI surface | Underlines every known word on every page | One alert per known word per cooldown |
| SRS state needed | Yes (`srs_state`, `days_ago` drive tooltip badge colour) | No |
| Cap | 500 (latest reviewed) | 1000 (latest written) |
| Ordering | `last_review_date desc nulls last` | `write_date desc` |
| Filter | All active entries | `pvp_eligible=True` only |

Bundling them behind a `?for=radar` query param would have either (a) made the
M27 consumer pay for fields it doesn't need or (b) made the M34 consumer skip
fields the server still computed. Two endpoints with single responsibilities are
the cleaner pattern, even at the cost of a small amount of join duplication.

**Consequences:** Future shared client helper can consume either endpoint —
they return the same `translations: {lang_code: text}` shape per row, which is
already the canonical multi-language projection used by M27's tooltip
(M27-22 contract). Future M-thirty-something can factor out the shared
"vocab + translations" join into a Python helper once a third consumer
emerges; until then, code duplication is < 30 lines and cheaper to read than a
parameterised mega-endpoint.

### Sub-decision 34b: Look-ahead via main-world XHR / fetch interception (with DOM-observer fallback)

**Problem:** To pause `lookahead_seconds` (default 4) **before** a word is spoken,
the radar needs to know upcoming cue start times. M24's DOM observation of
`.ytp-caption-segment` only shows the **current** cue — by the time the cue is
rendered, the word is already being spoken. Zero look-ahead. Three viable paths:

| Option | Mechanism | Look-ahead | Verdict |
|---|---|---|---|
| A | Intercept `/api/timedtext` XHR / fetch in the page's main world | Full track | **Chosen** |
| B | Read `<track>` / `TextTrack` API | Full track | Rejected — YouTube hides cues inside Shadow DOM and disables the native track on the `<video>` |
| C | MutationObserver on `.ytp-caption-segment` (M24 pattern) | Zero | Kept as graceful fallback |

**Why not `webRequest` / `declarativeNetRequest`?** MV3 service workers cannot
read response bodies via `webRequest.onResponseStarted`, and
`declarativeNetRequest` is rule-based (block / redirect / modify-header only —
no body inspection). The only MV3-compatible way to read a page's own response
body is to inject a script into the page's **main world** and patch
`XMLHttpRequest.prototype` / `window.fetch` from there.

**Implementation** (`extension/youtube_radar_inject.js`):
- Idempotent guard `if (window.__lxRadarInjected) return;` at top — survives SPA
  re-injection on every `yt-navigate-finish`.
- `XMLHttpRequest.prototype.open` patched to stash `this.__lxUrl`;
  `XMLHttpRequest.prototype.send` patched to add an `addEventListener('load')`
  that reads `responseText` on `status 2xx`.
- `window.fetch` patched. URL extraction handles all three input shapes (string,
  `Request.url`, `URL.href`). `response.clone().text().then(_ingest)` — clone
  forks the body so the page's own consumer still reads an un-touched stream.
- JSON3 parser primary (modern YouTube default); SRV3 `<p t="ms" d="ms">` and
  SRV1 `<text start="seconds" dur="seconds">` XML parsers as fallback, with
  correct sec→ms conversion.
- One-time `console.warn` on unknown format so future YouTube format changes
  surface clearly.

**Safety contract:**
- Every patch site wrapped in `try / catch` so an exception inside our hook
  **never** breaks the page's own request flow.
- The original `open` / `send` / `fetch` are always invoked via
  `apply(this, arguments)`.
- `response.clone()` forks the body — the patched `fetch` is fully transparent
  to the page's own consumers.

**Verification:** Browser smoke captured 3621 cues, perfectly formatted as
`{startMs, endMs, text}`, with no observable impact on YouTube's own caption
rendering. Offline sandbox covers JSON3 happy path, SRV3 XML, SRV1 legacy
seconds-based XML, non-timedtext URLs are NOT intercepted, and the idempotent
guard survives double-injection. Recorded in PLAN §M34-S3-OFFLINE and the
commit message of `612a476`.

**DOM-observer fallback:** If no `/api/timedtext` request fires within 10 s of
script load (live streams, alternate caption pipelines), `youtube_radar.js`
falls back to a `MutationObserver` on `.ytp-caption-window-container` and
matches against the **current** cue (zero look-ahead — pauses fire AS the word
is spoken, not before). Documented as a known degraded mode. Not wired in S4
because the JSON3 path covers > 99 % of cases; can be added behind a
"timedtext-not-seen" timer if a user reports trouble.

### Sub-decision 34c: Three-layer control surface; cooldown advances at CLOSE, not at FIRE

**Problem:** A user with 1000 saved words watching a chatty YouTube channel
would see the radar fire every few sentences. Unusable. Need granular controls
without overwhelming the Options page.

**Decision:** Three orthogonal control layers, in order of granularity:

| Layer | Scope | Storage | Default | Configurable |
|---|---|---|---|---|
| Master "Enable Radar" | Extension-wide | `chrome.storage.sync.lexora_radar_enabled` | ON | Options page |
| Cooldown between pauses | Extension-wide | `chrome.storage.sync.lexora_radar_cooldown_seconds` | 120 s (min 10, max 3600) | Options page |
| Look-ahead window | Extension-wide | `chrome.storage.sync.lexora_radar_lookahead_seconds` | 4 s (min 1, max 15) | Options page |
| Per-tab "Skip this word" | This tab's lifetime | In-memory `_tabSkip: Set<word>` | Empty | Footer button |
| Per-video kill switch | This video only | In-memory `_videoKillSwitch: boolean` | False | Footer button |

The user can dial out the radar at any granularity: globally (toggle), temporally
(cooldown), per-word (skip), or per-video (kill switch). Three of the five
layers persist (sync storage); two are intentionally ephemeral (tab / video
scope) so the user's "I already know this one for now" doesn't permanently
poison their review schedule. SPA navigation (`yt-navigate-finish`) clears
both ephemeral layers.

**Cooldown timer starts at OVERLAY CLOSE, not at FIRE.**

This is the subtle but critical UX rule. If the cooldown started at the fire
event, a user who paused the radar to read the alert for 30 s would lose 30 s
of their 120 s cooldown — and the next pause might fire immediately upon
clicking Continue. Instead, `_lastFiredAt = performance.now()` is set inside
`_closeOverlay()`, so the 120 s clock only starts when the user has finished
reading and dismissed the alert.

To prevent re-fire while the overlay is up, `_onTimeUpdate` checks
`if (_overlayOpen) return;` at the top of the gating chain. The
`_overlayOpen` flag is set during render and cleared during close.

**Sandbox bug caught during S5:** `_lastFiredAt` was initially `0`, but
`performance.now()` on a fresh page is a small number (page just opened) — so
`performance.now() - 0` would be < 120 000 ms, and the cooldown gate would
hold for the first ~2 minutes of every page life, blocking the radar from
firing on early-video hits. Fixed by initialising to `-Infinity` so the first
fire on a fresh page isn't gated. SPA reset also resets to `-Infinity`.
Verified with a Node sandbox (recorded in `db15b96`).

### Sub-decision 34d: Top-level overlay host, NOT nested in the M24 Quick Look card

**Problem:** The existing YouTube overlay (`extension/overlay.js`, M24 + M28 +
M32 + M33) is **click-on-subtitle-word** triggered. M34's radar is
**auto-triggered** on a different code path. Putting both in the same DOM
container would guarantee a layout / z-index / visibility-state collision the
first time a user clicked a subtitle word while a radar alert was already up.

**Decision:** New top-level Shadow-DOM host `#lx-radar-shadow-host`, appended
to `document.body`, with `position: fixed; bottom: 24px; left: 50%;
transform: translateX(-50%); z-index: 2147483600`. One below the M28 Quick
Look host's `2147483601` so a click-on-word overlay always wins if both
surfaces happen to be open at the same time — but they're independent and
non-conflicting.

Visual identity intentionally distinct from neighbouring features:

| Surface | Palette | Trigger |
|---|---|---|
| M28 Grammar Explainer | Indigo (`#6366f1`) | User clicks "Explain Grammar" |
| M32 Slang & Idiom Explainer | Amber (`#f59e0b`) | User clicks "💡 Explain Slang/Idiom" |
| M33 Webpage Shadowing | Teal (`#14b8a6`) | User clicks "🎤 Practice Pronunciation" |
| **M34 YouTube Vocab Radar** | **Teal + amber gradient header** | **Auto-pause** |

A user with all four features active on the same YouTube video can see four
colour-coded surfaces at once without mistaking which is which. The M34
teal+amber mix evokes both the M33 mic-recording feature (teal) and the M32
explainer (amber) — the radar is conceptually a "passive review" surface that
sits between them.

**Flex sandwich enforcement (M28-12d reapplied):** every structural
`flex`/`overflow`/`max-height` property in `_RADAR_SHADOW_CSS` carries
`!important` so YouTube's own stylesheet can't reposition our card. The
top-level page CSS for the host element (`_RADAR_HOST_CSS`) also uses
`!important` on the position and z-index because we are competing with
YouTube's `.html5-video-player` overlays.

### Sub-decision 34e: Longest-match sliding window for multi-word phrases

**Problem:** A user has both `kick` and `kick the bucket` in their vocabulary
(real case — single-word verb plus its idiomatic phrase). When a cue contains
"He will kick the bucket soon", which entry should the radar fire on? The
**longer match** — the idiom is much more interesting to surface than the
component verb.

**Decision:** Two-pass sliding window in `_findCueHit(cueText, idx)`:

1. **Phrases pass first.** Phrases (multi-token entries) are pre-sorted
   descending by token count in `_buildIndex`. The window scans each phrase
   length over the cue's tokens (`for i in 0..tokens.length - phLen`); the
   first match accepted is therefore the **longest possible**.
2. **Single-token fallback.** If no phrase matched, iterate over the cue's
   tokens and check the `Map<normalized, entry>`. First hit wins.

**Per-cue limit:** at most one hit per cue. A long sentence with three
vocabulary words contributes one entry to `_radarHits`. Combined with the
cooldown gate, this prevents the radar from pausing twice within the same
caption line.

**Tokenisation regex:** `/[\wÀ-ɏͰ-Ͽἀ-῿Ѐ-ӿ'\-]+/gu`. Covers ASCII (`\w`),
Latin Extended (including Polish ą / ć / ę / ł / ń / ó / ś / ź / ż), Greek
basic + extended ranges (modern and polytonic transcripts), and Cyrillic.
Same regex M27 used for review-in-the-wild and M33 used for pronunciation
diffing, just extended with the polytonic Greek block `ἀ-῿` since older
YouTube transcripts occasionally carry polytonic accents in Ancient-Greek
videos.

**Verification:** 13 / 13 cue-match cases pass in the offline sandbox (recorded
in `db15b96`):

- `ephemeral` matches single-token.
- `kicked the bucket` → `null` (inflection not in vocab; we deliberately don't
  stem since users explicitly add specific forms).
- `kick the bucket` → `kick the bucket` (longest-match beats `kick`).
- `give up` matches the 2-gram phrase.
- `Look up the answer please.` → `up` (single-token fallback when no phrase
  matches).
- Empty cue → `null`.
- Polish single (`książka`), Greek single (`καλημέρα`), Ukrainian single
  (`привіт`) all match.
- `UP up uP` → `up` (case-insensitive via `_normToken`'s `toLowerCase()`).

### Sub-decision 34f: No persistence by default

**Decision:** Radar events are ephemeral. No DB write per fire, no
`language.review` update, no "user encountered this word on YouTube" telemetry
log. The user closes the alert → state evaporates → next cooldown begins.

**Rationale:**
- **M27 already covers passive review-in-the-wild on web pages.** Its SRS
  integration is the right place for "user has seen this word recently". If
  M34 also wrote to SRS state, a single 90-minute video binge would skew
  review scheduling — the user might encounter the same word 5× in one video
  and have its `last_review_date` advanced 5× when no real review happened.
- **Privacy.** The user's YouTube watch history never leaves their browser.
  The only data Lexora's backend sees is the static GET to
  `/lexora_api/my_vocab` (which it serves freely anyway). What the user
  watches, when they pause, which words triggered — all of that stays
  client-side.
- **Same default as M33** (ADR-032 § 32f). Consistency across the
  no-persistence-by-default cluster of features.

**Trade-off:** users can't review their YouTube practice over time from the
portal. The portal's `/my/practice` (M9 SRS) and `/my/speaking` (M30) remain
the persistent surfaces. An opt-in "Save to my watch history" toggle is the
obvious M-thirty-something extension — documented in revisit triggers.

### Lessons fed back into the codebase

- **Pattern reuse rule extended.** M34 adds the seventh `/lexora_api/*`
  endpoint following the same auth pattern (`auth='none'` +
  `_require_session()`, cookie ∥ `X-Lexora-Session-Id` bridge, CORS reflection
  via `_cors_headers()`, JSON envelope via `_json_response()`). Future API
  additions should clone this template verbatim — it's been stable since M22
  and survives every CORS / SameSite quirk we've hit.
- **Sandbox-first verification pays for itself.** The `_lastFiredAt = 0` →
  `-Infinity` bug was caught by a hand-ported Node sandbox of the tick logic
  before any browser smoke. A real browser test would have shown "radar
  doesn't fire on the first hit of every fresh page" and we'd have spent 30
  minutes diagnosing in Chrome DevTools. The sandbox caught it in 30 seconds.
- **Main-world injection is now a locked-in capability.** Any future feature
  that needs page-level network sniffing (M-thirty-something Netflix
  subtitle radar, custom video player overlays, a watch-history tracker)
  has a working template in `extension/youtube_radar_inject.js`. The
  manifest-side `web_accessible_resources` entry is the only new permission
  surface — no new content-script permissions needed.
- **Cooldown-advances-at-close is the right default for any auto-trigger.**
  M32 / M33 don't have an "auto-trigger" surface (both are user-clicked), so
  M34 is the first feature to need this rule. Future auto-trigger features
  (radar variants, idle-detection nudges) should follow the same
  fire-doesn't-advance / close-advances pattern, gated by an `_overlayOpen`
  flag.
- **Defensive input clamping in the Options page** mirrors the
  server-side-floor rule from ADR-031. The cooldown input clamps to
  `[10, 3600]` and the lookahead clamps to `[1, 15]` on every change —
  including writing the clamped value back to the `<input>` so the user
  sees the corrected number immediately. Cheap UX courtesy, prevents
  pathological values from breaking the radar.

### Revisit triggers

- **YouTube changes the caption pipeline.** The XHR / fetch interception
  depends on `/api/timedtext` being the URL and JSON3 (or SRV3 / SRV1 XML)
  being the response format. If YouTube migrates to gRPC, WebSocket, or a
  completely new endpoint, the DOM-observer fallback (sub-decision 34b) is
  the safety net — the radar still works at zero look-ahead. Log signal:
  the one-time `console.warn('[lx-radar inject] unknown timedtext format')`
  fires.
- **Save-to-history opt-in.** A future M-thirty-something can add a
  `chrome.storage.sync.lexora_radar_save_history` toggle that POSTs each
  fire to a new `/lexora_api/radar_log` endpoint. Storage shape:
  `{user_id, entry_id, video_id, video_url, fired_at, cue_text}`. SRS
  integration: opt-in flag inside that endpoint to also call
  `language.review.action_register_review(grade=2)` so the YouTube
  encounter counts as a recall. Default off; user explicitly enables.
- **Per-tab skip set persistence.** Heavy users with many short videos
  might want skipped words to survive tab close. Swap `_tabSkip` from
  in-memory `Set` to `chrome.storage.session.lexora_radar_skip` keyed by
  `tab id + word`. `chrome.storage.session` is the right backing store
  (auto-clears on browser restart, survives tab close within a session).
- **5th language addition.** The `FLAGS` map inside `_renderRadarOverlay`
  is the only Lexora-side surface that hardcodes the 4-language set.
  Adding a fifth language is a single-line change: `{en:'🇬🇧', uk:'🇺🇦',
  el:'🇬🇷', pl:'🇵🇱', xx:'🏴'}`. ADR-029's canonical
  `LANGUAGE_SELECTION` import handles the server side.
- **Netflix / Disney+ / Coursera expansion.** The architecture is portable
  — each new platform needs (a) a new content-script entry in the manifest
  scoped to its origin, (b) a platform-specific cue-extraction inject
  script (Netflix has its own subtitle delivery format, etc.), (c) an
  equivalent `<video>` element discovery + `timeupdate` subscription.
  `_findCueHit`, the cooldown gate, the overlay UI, and the Options page
  are all platform-agnostic and reusable.

---

## ADR-034: Multi-word YouTube Subtitle Selection — Ctrl/⌘-Click multi-select (M35)

**Status:** Accepted (M35, 2026-05-16)

**Context:** M24 wraps each YouTube subtitle word in an isolated
`<span class="lx-sub-word">` with a `click` listener that opens a single-word
Quick Look. This breaks down for phrasal verbs ("give up"), idioms ("kick the
bucket"), and any multi-token expression: the user can only ever look up the
single word their cursor happens to land on. M35's goal is to let the user
operate on whole phrases — and have every downstream Quick Look feature
(Explain Grammar M28, Explain Slang/Idiom M32, Practice Pronunciation M33)
inherit phrase support for free, because the card reads its word from
internal state rather than re-querying the DOM.

The decision is **how** to capture multi-word user intent on a player surface
whose owner (YouTube) has explicit countermeasures against text selection.

### Sub-decision 35a: Strategy A (native browser selection) — IMPLEMENTED, then DISCARDED

**What we tried** (commit `ad92887`):

1. Override `user-select: none` on the caption subtree:
   ```css
   .ytp-caption-window-container,
   .ytp-captions-container,
   .ytp-caption-segment,
   .lx-sub-word {
     user-select: text !important;
     -webkit-user-select: text !important;
   }
   ```
2. Bind capture-phase `mousedown` / `mousemove` / `mouseup` listeners on the
   persistent `.ytp-caption-window-container`, each calling
   `e.stopPropagation()` (only when `target.closest('.lx-sub-word')` matches)
   and intentionally NOT calling `preventDefault` — preserving the browser's
   native selection-extension behaviour on `mousemove`.
3. On `mouseup`, defer one `queueMicrotask` so the browser finalises the
   selection range, then read `window.getSelection().toString()`, normalise,
   and route through the Quick Look pipeline if the result has ≥1 internal
   whitespace.
4. Suppress the per-span `click` that follows `mouseup` via a
   `_lxSwallowNextClick` flag drained inside `_onWordClick`.

**Why it failed:**

The user-reported verdict after browser smoke was unambiguous: **"щось воно
ніфіга не тягнеться"** ("the thing doesn't drag at all"). The native
selection range never extended past the click anchor.

Root cause: YouTube's player is more aggressive than the M35 architectural
analysis anticipated. Three concrete obstructions stacked together:

1. **`user-select: none` is re-applied by JS on every cue render.** Setting
   `user-select: text !important` in our extension stylesheet wins on the
   FIRST render, but YT writes a new inline style on the new `.lx-sub-word`
   spans during the next cue swap (~every 2-4 s). Our static CSS rule
   loses to a dynamically-applied inline style — `!important` doesn't help
   because YT's inline rule is also effectively `!important` (inline styles
   beat external CSS at the same specificity level when both are
   `!important`-tagged, by spec).
2. **Selection-extension interception runs below event listeners.** Even
   when we successfully kept `user-select: text` on a span at the moment
   of `mousedown`, YT's player has an `onselectstart` handler (or
   equivalent at the JS-event level) that calls `event.preventDefault()`
   on `selectstart`. Without a `selectstart` listener of our own that
   beats theirs, the selection never starts.
3. **Even capture-phase event firewalling can't help.** Our capture-phase
   `stopPropagation` keeps YT's `mousedown` / `mouseup` listeners on
   `.html5-video-player` silent — that part worked. But the
   `selectstart` interception isn't on the player surface; it's tied to
   the captions container itself.

**The cost-to-recover would have been:** patching a `selectstart` listener
on the caption container that calls `e.stopPropagation()` AND finding a way
to block YT's repeated re-application of `user-select: none` on every cue
render — likely a MutationObserver on the caption container that re-asserts
our CSS class on every span as it appears, OR injecting a main-world script
(à la M34) that monkey-patches whatever YT JS is rewriting the inline
style. Both options add fragile machinery for a UX (drag-to-select on a
fast-changing inline element) that has its own intrinsic problems —
cue-segment volatility means a drag that crosses a `.ytp-caption-segment`
boundary at the moment YT swaps in fresh spans loses the selection anyway.

**Decision:** abandon Strategy A entirely. Revert the code. Find a
different UX that doesn't fight the platform owner.

### Sub-decision 35b: Strategy B (manual drag state machine) — REJECTED without smoke

**What it would have been:**

`mousedown` on a span sets `_drag.anchor`; `mouseenter` on each subsequent
span appends to `_drag.spans`; `mouseup` finalises and concatenates
`_drag.spans.map(s => s.textContent).join(' ')`. Custom `.lx-sub-selected`
highlight CSS. The browser's native selection is bypassed entirely — we'd
draw our own visual feedback via CSS classes.

**Why we didn't try it:**

- **Cue-segment volatility still hurts.** YT replaces `.ytp-caption-segment`
  every 2-4 s. A drag that crosses a swap moment loses its anchor `<span>`
  (now an orphaned DOM node) and the in-progress selection breaks. We'd
  have to add cue-change detection and either pause the timeline-display
  during drags (impossible — we don't control the player) or accept that
  half of all drag attempts fail.
- **No native selection feedback.** The user sees a custom highlight
  instead of the browser's familiar blue. That's a "downgrade" UX —
  custom highlight color clashes with whatever theming YT uses in
  ambient mode / dark mode / TV-mode shell.
- **No protection against the platform owner's next move.** If YT
  decides to disable pointer events on subtitles tomorrow (they have
  before), Strategy B breaks too. Strategy C — using only `click` —
  inherits M24's existing event-surface stability (a year of production
  use without YT breaking it).

Documented as available in PLAN.md but not implemented. Re-evaluate only
if Strategy C develops issues that pure-`click` UX can't address.

### Sub-decision 35c: Strategy C (Ctrl/⌘-Click multi-select) — CHOSEN

**The user proposed it** after Strategy A failed in browser smoke. The
key insight: **don't try to drag at all.** Each Ctrl-click is just a
regular `click` event with `e.ctrlKey === true` (or `e.metaKey` on
macOS) — the exact event surface M24 already handles with stable
production reliability.

**State machine:**

```
        [idle, buffer empty]
              │
   Ctrl-click on .lx-sub-word
              │
              ▼
        [selecting, buffer ≥ 1]   ← Ctrl-click another span: append
              │                     Ctrl-click selected span:  toggle-out
              │                     Esc:                       _clearMultiSelection
              │                     plain click anywhere:      _clearMultiSelection
              │                     yt-navigate-finish:        _clearMultiSelection
              │
   release Ctrl/⌘ (keyup; ctrlKey && metaKey both false)
              │
              ▼
       _finaliseMultiSelection()
              │
              ▼
       _normalisePhrase(words.join(' '))
              │
              ▼
       _openLookupOverlay(phrase, 'phrase')
              │
              ▼
        [idle, buffer empty]
```

**Why it wins where Strategy A failed:**

| Concern | Strategy A (native) | Strategy C (Ctrl-click) |
|---|---|---|
| `user-select: none` | Has to be defeated | Irrelevant — never call `getSelection()` |
| `selectstart` interception | Has to be defeated | Irrelevant — no selection events |
| Cue-segment volatility | Selection lost on cue change | Buffer holds span refs; if a span is recycled, `classList.remove` is try/caught and we proceed gracefully |
| YT bubble-phase listeners | Have to be silenced | M24's existing `e.stopPropagation()` on `click` already handles it |
| User feedback | Native blue highlight | Custom `.lx-multi-selected` indigo highlight (stronger than M24's `:hover`) |
| Partial selection | Possible (mid-word) | Impossible (always whole-word) |
| Code surface | New listener trio + queueMicrotask + swallow flag + WeakSet | One modifier branch on existing `_onWordClick` + two helpers + four document listeners |
| Stability against platform owner | Fragile (every YT player update is a re-evaluation) | Stable (only depends on `click` + `keyup` events working) |

**Verification:** 16/16 sandbox cases pass on the state machine logic,
covering the happy path, toggle in/out, out-of-order Ctrl-clicks
(click order preserved, NOT spatial), deselect-in-middle, abort via
plain click or Escape, empty-buffer finalise no-op, single Ctrl-click
degenerates cleanly to the single-word case, and Polish / Greek /
Ukrainian token preservation through join+normalise. Browser smoke
confirmed by the user: multi-word selection works, all four downstream
features (Add to Vocabulary, Explain Grammar, Explain Slang/Idiom,
Practice Pronunciation) inherit phrase support unchanged.

### Sub-decision 35d: Buffer order = click order, NOT spatial order

When the user Ctrl-clicks "bucket" first, then "kick", then "the", the
resulting phrase is **"bucket kick the"**, NOT "kick the bucket".

**Rationale:**

- **Deterministic and discoverable.** The user sees their click order
  reflected in the visual highlight (they Ctrl-clicked "bucket" first, so
  "bucket" is highlighted first). When they release Ctrl, the phrase they
  hear ends up in the lookup is the phrase their click order produced.
  No surprise reordering.
- **The user already controls the order.** If they want "kick the
  bucket", they Ctrl-click "kick" first. If they accidentally clicked
  out of order, the toggle semantics (35e) let them un-click and re-click
  without releasing the modifier.
- **No clean rule for "spatial order".** Spans can appear across two
  simultaneous cue lines (top + bottom dual-track subtitles), or in
  right-to-left script (Arabic / Hebrew if added). "Spatial order" is
  ambiguous in those cases — DOM order? Bounding-box `top` then `left`?
  Every choice creates new edge cases. Click order is unambiguous.
- **Future opt-in toggle remains possible.** A future Options-page
  toggle could add "Sort buffer by DOM order before finalise" for users
  who prefer that semantics. Default off.

### Sub-decision 35e: Toggle semantics on re-Ctrl-click (undo without releasing modifier)

If the user Ctrl-clicks "kick" → "the" → "bucket" → realises they meant
to include "the" twice, they can Ctrl-click "the" once more to
**deselect** it. Re-clicking the now-deselected "the" re-selects it.

**Rationale:**

- **Forgiveness.** The buffer is fluid until the user releases Ctrl.
  Mis-clicks are one click away from being undone.
- **Discoverable.** Standard OS behaviour for Ctrl-click in file pickers
  / multi-select lists — users already know it.
- **Implementation cost is zero.** A single `indexOf` check at the top
  of the Ctrl branch in `_onWordClick`:
  ```js
  const existing = _multiWordSelection.indexOf(span);
  if (existing >= 0) {
    _multiWordSelection.splice(existing, 1);
    span.classList.remove(_MULTI_SELECTED_CLASS);
  } else {
    _multiWordSelection.push(span);
    span.classList.add(_MULTI_SELECTED_CLASS);
  }
  ```

### Sub-decision 35f: Finalisation on the LAST modifier release (multi-key safe)

The keyup listener checks `e.ctrlKey || e.metaKey` AFTER the event has
fired. When the user releases one Ctrl key while still holding the
other (left Ctrl + right Ctrl), `keyup` fires for the released key but
the modifier flag stays true. We only finalise when both flags are
false — i.e., the LAST Ctrl/Meta key has been released.

**Rationale:**

- **Multi-key keyboards exist.** Many users press Ctrl with the side
  they prefer; some users have remapped both sides. Finalising on the
  first release would surprise them.
- **The flag check is one line.** No state machine bookkeeping needed
  — the browser already tracks which modifiers are held.
- **Defensive against keyboard repeat / sticky keys.** Accessibility
  features that synthesise multiple keyup events are handled
  transparently because we ignore keyups that leave a modifier still
  held.

```js
window.addEventListener('keyup', (e) => {
  if (e.key !== 'Control' && e.key !== 'Meta') return;
  if (e.ctrlKey || e.metaKey) return;
  if (!_multiWordSelection.length) return;
  _finaliseMultiSelection();
}, true);
```

### Defensive escape hatches (cross-cutting)

Three independent paths clear the buffer if the natural keyup-finalise
path doesn't fire:

1. **Plain click anywhere (no modifier held).** Document-level capture-
   phase `click` listener — drops the buffer silently. Defends against
   the case where keyup is missed (browser loses focus, alt-tab,
   keyboard shortcut intercepts the keyup at the OS level).
2. **Escape key.** Existing document keydown handler extended to also
   clear the buffer alongside closing any open Quick Look overlay.
   Mirrors the user's mental model of "Escape cancels everything".
3. **`yt-navigate-finish`.** SPA navigation between videos clears the
   buffer before YT recycles the caption container — span references
   in the buffer would otherwise point at soon-to-be-orphaned DOM.

### Lessons fed back into the codebase

- **Browser smoke before declaring victory.** Strategy A had a clean
  16-case offline sandbox AND `node --check` passing — both green
  indicators. The browser test was where it died. Architectural
  analysis can ALWAYS underestimate platform-owner aggression. Plan
  every UX milestone with a browser smoke before the docs flip.
- **Engineering-honest documentation.** The PLAN.md M35 section
  preserves the full Strategy A / B writeups with the user's
  verbatim Ukrainian quote ("щось воно ніфіга не тягнеться"). Future
  readers will see exactly what we tried, why it failed, and won't
  waste a day re-attempting the same dead end. This is the
  cost-effective documentation pattern — capture the failure modes
  in-line with the success narrative.
- **M24's per-span event surface is still the right primitive.**
  Strategy A introduced a parallel event surface (capture-phase
  firewall on the persistent container). Strategy C used the
  existing per-span `click` listener with one modifier branch.
  The simpler approach won — fewer event types, fewer DOM
  reference points, fewer ways for YT's next update to break us.
- **Click-order over spatial-order for multi-select buffers.**
  Documented for future radar-history / batch-import features that
  might also need an ordered user-selected sequence. Click order
  is unambiguous; spatial order is platform-dependent.
- **User-proposed UX often beats developer-engineered UX.** The
  pivot from drag-to-Ctrl-click came directly from the user after
  the failure. Cheaper to listen than to keep engineering harder.

### Revisit triggers

- **Touch device support.** Ctrl-click doesn't exist on mobile.
  A future M-thirty-something could add a long-press → multi-select
  mode that uses `pointerdown` + a 400 ms hold detector to start a
  selection state machine. Tap each subsequent word to append, lift
  the hold to finalise. Same `_multiWordSelection` buffer, same
  `_finaliseMultiSelection` — just a different entry trigger.
- **Bulk select-all-cue option.** A keyboard shortcut (Shift+Ctrl-click
  on a span?) could select the entire cue line at once. Useful for
  grammar explanations on long sentences. Same buffer + finalisation,
  just a different append rule.
- **Spatial-order option.** Future Options-page toggle "Sort selection
  by DOM order before finalise". Default OFF (click order is the
  current contract). Single sort step inside `_finaliseMultiSelection`.
- **Modifier-key remapping.** A future Options-page setting could let
  the user choose Alt instead of Ctrl (some users have Ctrl
  remapped for accessibility reasons). One-line change inside
  `_onWordClick`'s modifier branch.
- **Auto-finalise on a small inactivity timer.** Some users might
  forget they still have Ctrl held. A 5-second inactivity timer
  (no Ctrl-click for 5 s while buffer non-empty → finalise) is a
  possible UX nudge. Default off.
