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
