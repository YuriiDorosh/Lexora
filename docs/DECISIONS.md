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
