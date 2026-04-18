# Lexora — Active Task Tracker

> **Purpose:** Canonical resume point for interrupted implementation sessions.
> Read this first when continuing work mid-milestone.
>
> **Update discipline:** Update this file after each meaningful sub-step — not only at the end of
> a milestone. A sub-step is meaningful if skipping its record would cause a future session to
> re-implement it or miss it.
>
> **Scope:** Covers the current or most recently active milestone only.
> When a milestone is verified complete, archive it in the "Completed Milestones" section below
> and start a fresh "Current Milestone" block.

---

## Current Milestone

### M4b — Real CPU-only Local LLM Inference

**Status:** In progress
**Started:** 2026-04-18
**Branch:** `m4b`

**Scope:** Replace the current stub enrichment in `services/llm/main.py` with a
real local, CPU-only model. No GPU assumed. No cloud API fallback. The existing
Odoo ↔ RabbitMQ ↔ FastAPI flow stays intact; only the `_init_llm()` /
`_enrich()` bodies and the service's build/deps change. Result shape must stay
compatible with `language.enrichment._handle_completed()` (synonyms, antonyms,
example_sentences, explanation).

This is a follow-up slice to M4, not part of M5.

#### Host environment baseline (2026-04-18)

- Cores: 16 · RAM: 30 GiB (19 GiB available) · Swap: 8 GiB
- Container platform: Docker Compose, `python:3.11-slim` base
- Target: Lexora dev host; production spec assumed comparable (≥4 cores, ≥8 GiB RAM)

#### Runtime / model options evaluated

| Option | Runtime | Model | RAM (inference) | Image cost | Inference latency | Pros | Cons |
|---|---|---|---|---|---|---|---|
| A | `llama-cpp-python` | Qwen2.5-3B-Instruct GGUF Q4_K_M | ~2.5 GiB | ~200 MB wheel + build tools; model ~2 GiB (volume) | 5–25 s on 16 cores | Smallest image delta, quantized from day one, multilingual (en/uk/el ok) | Needs `cmake`/`gcc` at build; model file must be downloaded (HF) |
| B | `llama-cpp-python` | Qwen2.5-1.5B-Instruct GGUF Q4_K_M | ~1.2 GiB | same wheel; model ~0.9 GiB | 2–10 s | Lightest real option; good fallback if host is constrained | Quality clearly below 3B, especially for antonyms and Greek |
| C | `transformers` + `torch` (CPU) | Qwen2.5-1.5B-Instruct (safetensors) | ~3 GiB | `torch` CPU wheel ~200 MB; transformers ~50 MB; model ~3 GiB | 10–40 s | Pure-Python path, canonical HF ergonomics | 3–4× larger image delta; torch pulls many transitive deps; no built-in grammar-constrained JSON |
| D | `ctransformers` | Qwen2.5 GGUF | similar to A | similar | similar | Simpler loader | Less actively maintained than llama-cpp-python |
| E | `transformers` 7B+ (unquant) | Qwen2.5-7B-Instruct | 14+ GiB | very large | minutes | High quality | Too slow / RAM-heavy for interactive enrichment on CPU |

**Recommended:** Option **A — `llama-cpp-python` + Qwen2.5-3B-Instruct GGUF Q4_K_M**, downloaded on first start from Hugging Face to a Docker-managed volume. Rationale in ADR-027 (to be added).

**Reasoning summary:**
- llama-cpp-python has a **much smaller image footprint** than `torch` CPU (no
  ~200 MB torch wheel, no CUDA stubs, no triton). That matters for a dev stack
  already rebuilding 4 worker images.
- GGUF Q4_K_M runs comfortably in ≤3 GiB RAM on 16 cores, well under our headroom.
- llama-cpp-python supports **grammar-constrained sampling** (GBNF) and
  `response_format={"type":"json_object"}`, which dramatically reduces the risk of
  malformed JSON from a small model — the #1 failure mode for this feature.
- Qwen2.5 3B has noticeably better multilingual coverage than 1.5B, especially
  for Ukrainian and Greek (still weaker for `el`, consistent with SPEC §4.4
  and OD-3).
- Model is **not baked into the image**: it's fetched once to a named Docker
  volume on first start, so image rebuilds stay cheap and the 2 GiB artefact
  survives container recreation.

#### What must change in the LLM service

1. `services/llm/requirements.txt` — pin `llama-cpp-python` and
   `huggingface-hub`.
2. `docker_compose/llm/Dockerfile` — install build deps (`build-essential`,
   `cmake`, `git`) needed by the `llama-cpp-python` source wheel on slim, and
   keep the final image lean by pruning apt caches.
3. `docker_compose/llm/docker-compose.yml` — add `llm_models` named volume
   mounted at `/models`; add env vars `LLM_MODEL_REPO`, `LLM_MODEL_FILENAME`,
   `LLM_N_CTX`, `LLM_N_THREADS`, `LLM_AUTO_DOWNLOAD`.
4. `env.example` — document the new env vars with sensible defaults.
5. `services/llm/main.py` —
   - `_init_llm()`: resolve model path under `/models`; if missing and
     `LLM_AUTO_DOWNLOAD=1`, call `huggingface_hub.hf_hub_download`. Load via
     `llama_cpp.Llama(model_path=..., n_ctx=N, n_threads=T, verbose=False)`.
     Set `_llm_ready=True` on success; on any exception log and return False
     (the service must still start so /health is honest about the failure).
   - `_enrich()`: build a compact prompt asking for JSON with the four required
     keys; invoke the model with `response_format={"type":"json_object"}`; parse
     the result; if parse fails, log and fall back to `_stub_enrich()` so the
     portal never deadlocks on bad output.
   - Latency-aware timeouts: `prefetch_count=1` already set; add a per-request
     generation cap (e.g. `max_tokens=512`) so a pathological prompt cannot
     stall the consumer.

#### Odoo integration — unchanged

- Event names (`enrichment.requested`, `enrichment.completed`,
  `enrichment.failed`) stay the same.
- Payload shape (`synonyms[]`, `antonyms[]`, `example_sentences[]`,
  `explanation`) stays the same — that is the implicit contract with
  `language.enrichment._handle_completed()`.
- No Odoo-side changes needed. If this turns out to be wrong during
  verification, revisit and record as a blocker.

#### Docker / build strategy

- **Model not baked in.** Keep the image reproducible and small; model fetched
  lazily. `llm_models` named volume survives `make down-llm` / `up-llm`.
- **Build tools only in build stage (single-stage acceptable for now).**
  `build-essential` + `cmake` add ~300 MB to the image but are required by
  `llama-cpp-python`'s source wheel. A future multi-stage refactor could trim
  this; out of scope for M4b.
- **Prebuilt wheels path:** if `llama-cpp-python` publishes a manylinux wheel
  for Python 3.11 on x86_64 at pinned version, pip will prefer it and skip the
  source build entirely. That is the happy path; the build-tools install is
  the safety net when no wheel matches.
- **Startup time:** first start = download model (~2 GiB over HF CDN, 1–10 min
  depending on network) + load. Subsequent starts = load only (~2–5 s). Health
  endpoint should report `llm_ready=false` during download/load and flip to
  true once ready.

#### Verification strategy

1. Image rebuild succeeds (`make up-llm-no-cache`).
2. `/health` reports `llm_ready: true` after model load completes.
3. End-to-end via portal: add entry `apple` (en) → click *Enrich with AI* →
   within ~60 s, synonyms/antonyms/examples/explanation appear and are **not**
   prefixed with `[stub:…]`.
4. Ukrainian entry (`яблуко`, uk) — enrichment returns recognisable Ukrainian
   synonyms. Greek (`μήλο`, el) — accept weaker quality; document if
   unusable.
5. Re-enrich twice → no duplicate `language.enrichment` rows created (M4
   idempotency still holds).
6. Existing 71 tests still pass (no regression).
7. Latency measurement recorded: p50 and p95 over 5 sample runs per language.

#### Likely blockers / risks

1. **Source build of llama-cpp-python inside slim is slow/flaky.** Mitigation:
   pin a version known to publish x86_64 manylinux wheels; keep
   `build-essential` + `cmake` as a safety net.
2. **First model download bottleneck.** 2 GiB over HF CDN can exceed 10 minutes
   on a constrained network. Mitigation: document that `make up-llm-no-cache`
   may appear to "hang" the first time; `make logs-llm` shows download
   progress. Acceptable for dev.
3. **Malformed JSON from a small model.** Mitigation: `response_format=json_object`
   plus a strict parser with stub fallback. Log the raw output when falling back
   so we can inspect real failures.
4. **Greek quality.** SPEC §4.4 and OD-3 already acknowledge thin Greek
   support. M4b does not promise Greek parity; it promises the **mechanism** is
   real, and Greek output may remain visibly lower quality.
5. **Memory pressure under parallel requests.** `prefetch_count=1` already
   serialises consumption, so only one inference runs at a time inside the
   worker. Safe.
6. **License/redistribution.** Qwen2.5 is Apache-2.0 — no redistribution issue
   for the GGUF on HF. Confirmed in ADR-027.

#### Sub-steps (checkpoint-friendly — each one safely stoppable)

**Phase 1 — Planning & decisions (no code yet)**

- [x] M4b-01 · Write M4b plan block in `docs/TASKS.md` (this section).
- [x] M4b-02 · Add ADR-027 to `docs/DECISIONS.md` covering runtime/model choice,
  alternatives considered, revisit triggers.

**Phase 2 — Dependency & infra wiring (safe, reversible)**

- [x] M4b-03 · `services/llm/requirements.txt`: pin `llama-cpp-python==0.3.2`
  and `huggingface-hub==0.26.2`. (No rebuild triggered yet — deferred to M4b-07.)
- [ ] M4b-04 · `docker_compose/llm/Dockerfile`: install `build-essential`,
  `cmake`, `git` before `pip install`; clean apt lists at the end.
- [ ] M4b-05 · `docker_compose/llm/docker-compose.yml`: add `llm_models` named
  volume at `/models`; add new env vars with defaults.
- [ ] M4b-06 · `env.example`: document `LLM_MODEL_REPO`,
  `LLM_MODEL_FILENAME`, `LLM_N_CTX`, `LLM_N_THREADS`, `LLM_AUTO_DOWNLOAD`.
- [ ] M4b-07 · `make up-llm-no-cache` — confirm build succeeds; service starts
  in stub mode (no model yet); health reports `llm_ready:false` as expected.

**Phase 3 — Model loading**

- [ ] M4b-08 · `services/llm/main.py`: implement model download helper
  (`_ensure_model_file()`) using `huggingface_hub.hf_hub_download`. Idempotent
  via filesystem check. Controlled by `LLM_AUTO_DOWNLOAD`.
- [ ] M4b-09 · `services/llm/main.py`: implement `_init_llm()` — load GGUF via
  `llama_cpp.Llama`. Set `_llm_ready=True` on success; return False on any
  error with a clear log message.
- [ ] M4b-10 · Rebuild + start service; confirm model downloads to volume on
  first start and `/health` flips `llm_ready:true` within the download+load
  window. Confirm re-start is fast (seconds).

**Phase 4 — Inference logic**

- [ ] M4b-11 · Write the enrichment prompt template. Language-aware: target
  output language is `payload.language`; source text is `payload.source_text`.
  Ask for a single JSON object with keys `synonyms`, `antonyms`,
  `example_sentences`, `explanation`.
- [ ] M4b-12 · `_enrich()`: call `Llama.create_chat_completion(...)` with
  `response_format={"type":"json_object"}`, `max_tokens=512`, `temperature=0.3`.
- [ ] M4b-13 · Parse the JSON; coerce into the shape
  `language.enrichment._handle_completed()` expects (lists for synonyms /
  antonyms / examples, string for explanation). On parse failure, log the raw
  payload and fall back to `_stub_enrich()`.
- [ ] M4b-14 · Add a minimal retry-once path on generation exceptions (not on
  parse failures — those fall to stub). Keeps the queue flowing.

**Phase 5 — Verification**

- [ ] M4b-15 · Portal E2E: add entry `apple` → Enrich → real results appear,
  no `[stub:…]` prefix.
- [ ] M4b-16 · Ukrainian entry `яблуко` → real results. Greek `μήλο` → record
  observed quality.
- [ ] M4b-17 · Re-run `language_enrichment` + `language_translation` tests:
  still 71 green.
- [ ] M4b-18 · Record p50/p95 latency across 5 sample runs per language in
  this section.

**Phase 6 — Close**

- [ ] M4b-19 · Update ADR-027 with verified latency numbers and any surprises.
- [ ] M4b-20 · Move M4b block to "Completed Milestones"; add "Known
  limitations at M4b exit".
- [ ] M4b-21 · Commit on branch `m4b`; open PR against `main` or merge locally
  per user's choice.

#### Verification already passed

(none yet — nothing built)

#### Files expected to change (summary for resume)

- `docs/TASKS.md` — this block (M4b-01) ✅
- `docs/DECISIONS.md` — ADR-027 (M4b-02)
- `services/llm/requirements.txt` — new pins (M4b-03)
- `docker_compose/llm/Dockerfile` — build tools (M4b-04)
- `docker_compose/llm/docker-compose.yml` — volume + env (M4b-05)
- `env.example` — new env vars (M4b-06)
- `services/llm/main.py` — real `_init_llm()`, `_enrich()` (M4b-08 → M4b-14)

#### Assumptions / temporary decisions

- Model repo assumed to be `Qwen/Qwen2.5-3B-Instruct-GGUF` with filename
  `qwen2.5-3b-instruct-q4_k_m.gguf`. To be confirmed in M4b-02/08 by reading
  the actual HF repo listing; adjust if file name differs.
- `LLM_N_CTX=2048`, `LLM_N_THREADS=0` (0 = let llama-cpp pick based on
  cores) as starting defaults.
- Auto-download on by default in dev; can be disabled via
  `LLM_AUTO_DOWNLOAD=0` for air-gapped installs.
- Test of real inference is a manual portal flow, not an automated pytest,
  to avoid making CI/dev bootstrap download 2 GB of model weights.

#### Blockers

(none yet)

---

## Completed Milestones

### M4 — LLM Enrichment Service

**Status:** Complete and verified.
**Started:** 2026-04-14
**Completed:** 2026-04-18

#### M4 preflight — UX gap analysis (2026-04-18)

Audit of the visible UX state of M1–M3 features before finalizing M4.
Goal: make the enrichment milestone produce a visibly more usable product, not just
more backend logic.

**Implemented-but-not-visible gaps (must fix inside M4):**

1. **Backend menu incomplete.**
   `view_language_translation_list/form` and `view_language_enrichment_list/form`
   exist and their `ir.actions.act_window` records are defined, but neither has a
   `menuitem`. Today only `Lexora → Vocabulary` and `Lexora → User Profiles` are
   reachable from the Odoo top menu. An admin cannot navigate to translation or
   enrichment job queues without crafting a URL.
   → Fix in M4: add `Translations` and `Enrichments` menu items under the `Lexora`
   root menu.

2. **Portal profile page is missing.**
   `language.user.profile` can only be edited from the backend, which portal users
   cannot reach. Since M3 auto-enqueues translations for every language listed in
   `profile.learning_languages`, a newly-signed-up user with no profile or empty
   `learning_languages` gets **zero translations on save** and has no way to fix
   this from the UI. The portal currently suggests "configure your learning
   languages in your profile" but there is no profile page to link to.
   → Fix in M4: add `/my/profile` portal page so users can set
   `native_language`, `learning_languages`, `default_source_language`, and
   `is_shared_list` themselves.

3. **Enrichment status is invisible from the vocabulary list.**
   The entry detail page now shows a state-aware "Enrich with AI" button (built in
   the earlier M4 UX pass), but the list page shows no signal whether an entry
   has been enriched, is pending enrichment, or has failed. Users have to open
   each entry to find out.
   → Fix in M4: small badge/icon in the list's flags column.

4. **Portal home (`/my`) has no direction-setting links.**
   Only the `My Vocabulary` docs-entry widget is present. A new user lands on
   `/my` and sees one box. There's no onboarding nudge toward their profile, the
   shared list, or adding an entry.
   → Fix in M4: add a Lexora quick-links card to the portal home with links to
   vocabulary, profile, and shared browse. Keeps existing portal.portal_my_home
   layout.

**Partially productized (acknowledge, defer):**

5. **Website root redirects to `/odoo` (Odoo backend).**
   Unauthenticated visitors hitting `http://localhost:5433/` get 303 → `/odoo`.
   There is no branded Lexora landing page. `website_require_login` is in the
   module list but the main website layout/theme has not been productized.
   → Out of M4 scope. A proper public landing page is a cross-cutting UX task that
   belongs next to posts/articles (M7) where the portal gains more public surface.

6. **No portal surface for Anki import (M5), audio (M6), posts/chat (M7/M8),
   dashboards (M9), PvP (M10).** By design — these are future milestones.

7. **Translations / enrichments backend menus only serve admins.** Portal-only
   users never see them. Portal-level visibility (e.g., `/my/jobs`) is not in any
   SPEC section and would duplicate the entry detail page's status. Defer.

**Makefile / docker workflow audit:**

- `up-dev` currently chains: `check-network → up-db → rabbitmq → redis →
  up-odoo (odoo + nginx + nginx-exporter + promtail + loki) → translation → llm
  → anki → audio`. That covers every running service for the current project
  state (M1–M4). ✓
- `down-dev` mirrors this in reverse. ✓
- Per-service `up-*-no-cache`, `down-*`, `logs-*` targets exist for all four
  worker services and for rabbitmq. ✓
- **Gap:** no aggregate `logs-dev` or `ps-dev` convenience target. When the
  stack grows it's useful to tail every container at once or list all dev-stack
  containers in one place.
  → Fix in M4: add `logs-dev` and `ps-dev` following the existing per-service
  idiom (no new build system, no `docker compose` profiles — just grouped
  Bash invocations consistent with the rest of the Makefile).
- **Note:** `make up-odoo` also starts `nginx-exporter`, `promtail`, `loki` via
  the odoo compose file. These are not part of the MVP data plane but are
  harmless in dev and expected by the existing production path. Keep as-is.

#### Sub-steps

- [x] Update TASKS.md to mark M4 started
- [x] M4 preflight — UX gap analysis written (this section)
- [x] `language_enrichment`: implement `language.enrichment` model (SPEC §3.5)
  - `src/addons/language_enrichment/models/language_enrichment.py`
  - Inherits `language.job.status.mixin`; fields: entry_id, language, synonyms, antonyms, example_sentences, explanation
  - `_handle_completed` / `_handle_failed` with idempotency check; UNIQUE(entry_id, language)
  - `_synonyms_list()`, `_antonyms_list()`, `_example_sentences_list()` JSON-parse helpers for portal
- [x] `language_enrichment`: extend `language.entry` with `enrichment_ids`
  - `src/addons/language_enrichment/models/language_entry_enrichment.py`
- [x] `language_enrichment`: security rules (ir.model.access.csv + record rules)
  - Language Users: read own enrichments only; admin: full CRUD
- [x] `language_enrichment`: cron scheduled action for consuming result queues
  - `data/ir_cron_enrichment.xml` — runs every 1 minute, calls `action_consume_results()`
- [x] `language_enrichment`: backend views (list/form)
  - `views/language_enrichment_views.xml` — list with status colors, form with retry button
- [x] `language_enrichment`: portal template extending entry detail (enrich button + results)
  - `views/portal_enrichment.xml` — inherits language_words.portal_vocabulary_detail
  - Injects "Enrich with AI" button + results card (synonyms/antonyms/examples/explanation)
  - Retry button on failed; spinner on processing
- [x] `language_enrichment`: portal controller (trigger + retry routes)
  - `controllers/portal.py` — POST /my/vocabulary/<id>/enrich + /retry_enrichment/<eid>
- [x] `language_enrichment`: manifest update (depends portal; all data files listed)
- [x] LLM service (FastAPI): pika consumer thread + stub enrichment + result publish
  - `services/llm/main.py` — daemon consumer thread + `_enrich()` + stub fallback
  - Stub returns clearly-marked `[stub:src→lang]` synonyms/antonyms/examples/explanation
- [x] LLM service: docker-compose env_file + RabbitMQ env vars; removed obsolete `version:` field
- [x] Tests: 17 tests covering model, state machine, idempotency, retry, enqueue, JSON helpers
  - Fixed: user created with `group_language_user`; used `cls.Entry = cls.env['language.entry'].sudo()`

#### Verification steps passed

- [x] `--update language_enrichment --stop-after-init` — 0 errors, module loaded (129 queries)
- [x] 17 language_enrichment tests pass (0 failures, 0 errors)
- [x] All prior tests still pass: language_security (3), language_core (4), language_words (29), language_translation (18)
- [x] `make up-llm-no-cache` — container rebuilt and running
- [x] `curl http://localhost:8002/health` — `{"status":"ok","service":"llm","llm_ready":false,"consumer_alive":true}`

#### Decisions made during this milestone

- ADR-025: LLM service follows same stub/graceful-fallback pattern as translation (ADR-024)
- ADR-026: LLM is CPU-only; no GPU assumed; recommended model is Qwen2.5 1.5B–3B for production
- Portal enrichment section injected via QWeb template inheritance (`views/portal_enrichment.xml` inherits `language_words.portal_vocabulary_detail`) — keeps language_enrichment self-contained
- Enrichment is user-triggered only (not auto on entry create); controller enqueues in source_language context
- Test user must have `group_language_user` (not `base.group_user`) to pass `check_access` on language.entry create

#### Post-implementation UX pass (same milestone)

- [x] Vocabulary list: language codes → human names ("en" → "English"); pvp_eligible indicator; cleaner empty state
- [x] Entry detail: lang_names throughout; pvp_eligible "⚡ PvP ready" badge; section separators (border-bottom + hr); structured action bar; improved empty state for no-translations with profile link hint
- [x] Enrichment button: state-aware — shows "Enrich with AI" / "Re-enrich" / disabled spinner based on current enrichment status for source language
- [x] Shared view: language names in badges
- [x] Portal controller: passes `lang_names` dict and `user_profile` to all templates
- [x] ARCHITECTURE.md: rewrote §3.3 hardware note — CPU-only, no GPU assumed, model strategy documented
- [x] SPEC.md: updated §4.4 model reference — Qwen2.5 1.5B–3B recommended, no GPU
- [x] `services/llm/main.py`: expanded `_init_llm()` docstring with CPU-safe model paths and explicit "do not use" warning for unquantized FP16 on CPU
- [x] DECISIONS.md: added ADR-026 (CPU-only LLM strategy)
- [x] All 71 tests still pass after UI changes

#### Discoverability pass (post-preflight, 2026-04-18)

- [x] Backend menu: add `Lexora → Translations` menuitem pointing at the existing
  `action_language_translation` (sequence 30), under the `menu_lexora_root` parent.
  `src/addons/language_translation/views/language_translation_views.xml`.
- [x] Backend menu: add `Lexora → Enrichments` menuitem (sequence 40) pointing at
  `action_language_enrichment`. `src/addons/language_enrichment/views/language_enrichment_views.xml`.
- [x] Portal profile page at `/my/profile` — `GET` renders the form, `POST` validates
  (native/default_source must be in `{en, uk, el}`) and writes via sudo to
  `language.user.profile._get_or_create_for_user()`. Form fields: native_language
  (select), learning_languages (checkbox group), default_source_language (select),
  is_shared_list (checkbox). Success banner + error banner. Route in
  `src/addons/language_words/controllers/portal.py`, template
  `portal_profile` in `src/addons/language_words/views/portal_vocabulary.xml`.
- [x] Portal home: `portal_my_home_lexora_quicklinks` template inherits
  `portal.portal_my_home` and injects a "Lexora — quick actions" card with links to
  `/my/vocabulary`, `/my/vocabulary/new`, `/my/vocabulary/shared`, `/my/profile`.
  Keeps the stock portal home untouched.
- [x] Vocabulary list: enrichment flag badge in the flags cell. New template
  `portal_vocabulary_list_enrichment_flag` in
  `src/addons/language_enrichment/views/portal_enrichment.xml` that inherits
  `language_words.portal_vocabulary_list` and adds `✦ enriched / ✦ pending /
  ✦ failed` badges based on the source-language enrichment status.
- [x] Makefile: add `logs-dev` (tails last 50 lines from every dev-stack container)
  and `ps-dev` (one-shot `docker ps` filtered to the dev stack). Matches the
  existing per-service target convention; no Compose profiles introduced.

#### Verification steps passed (discoverability pass)

- [x] `--update language_translation,language_enrichment,language_words
  --stop-after-init --no-http` — 0 errors; all menuitems / templates registered.
- [x] HTTP probes with a logged-in session cookie:
  `/my` → 200 (quick-actions card visible),
  `/my/profile` → 200 (form renders),
  `/my/profile` POST with `native_language=en&default_source_language=en&learning_languages=en&learning_languages=uk`
  → 200 + "Preferences saved" alert,
  `/my/vocabulary`, `/my/vocabulary/new`, `/my/vocabulary/shared` → 200.
- [x] 71 tests still pass after the changes (`language_security 3 +
  language_core 4 + language_words 29 + language_translation 18 +
  language_enrichment 17`).

#### Fixes during the discoverability pass

- **QWeb loop variable collision on `/my/profile`.** First render crashed with
  `AttributeError: 'language.lang' object has no attribute 'replace'` coming from
  the frontend layout (`lang.replace('_', '-')`). Root cause: the profile
  template used `t-foreach="all_langs" t-as="lang"`, which shadowed the reserved
  `lang` context variable Odoo's frontend layout uses for locale URL handling.
  Fix: renamed the loop variable to `lrec` everywhere in the template.

#### Known limitations at M4 exit

- **LLM is in stub mode.** `llm_ready:false` in the health check; `_enrich()`
  falls back to `[stub:src→lang] ...` synonyms/antonyms/examples/explanation.
  Real inference requires wiring `_init_llm()` to a CPU-safe model (Qwen2.5
  1.5B–3B via `llama-cpp-python` or `transformers`) and adding deps to a
  `requirements-full.txt` + rebuild. Documented in ADR-026 and in
  `services/llm/main.py` docstring.
- **Website root (`/`) still redirects to `/odoo`.** There is no branded public
  Lexora landing page yet. `website_require_login` is installed but the website
  layout has not been productized. Out of M4 scope (see preflight gap #5) —
  belongs with the posts/articles surface in M7.
- **Backend Translations / Enrichments menus are admin-only.** Portal users
  still see status only through the vocabulary list badges and the entry detail
  page. No `/my/jobs` surface; SPEC does not require one.
- **Portal profile page does not let users add new languages** beyond
  `{en, uk, el}`; the MVP language set is fixed. `language.lang` is a lookup
  model (ADR-020) — adding codes requires a seed change.
- **One-minute cron latency between completion and Odoo pickup** persists from
  M3 (ADR-023). Enrichment results appear within ~1 minute on the entry detail
  page after the LLM service publishes the completed event.

#### Blockers

(none)

---

### M3 — Translation Service

**Status:** Complete and verified.
**Started:** 2026-04-14
**Completed:** 2026-04-14

#### Sub-steps completed

- [x] Update TASKS.md to mark M3 started
- [x] `language_core`: real RabbitMQ publisher (pika connection + publish)
  - `src/addons/language_core/models/rabbitmq_publisher.py` — real pika BlockingConnection
- [x] `language_core`: add RabbitMQ config params to system_parameters.xml
  - host/port/vhost/user/password with dev defaults (rabbitmq/5672/guest/guest)
- [x] `language_core`: RabbitMQ consumer utility (basic_get cron-based drainer)
  - `src/addons/language_core/models/rabbitmq_consumer.py` — `drain(queue, handler)` method
  - passive=True declare: if queue absent, returns 0 cleanly (publisher creates it on first job)
- [x] `language_translation`: implement `language.translation` model (SPEC §3.4)
  - `src/addons/language_translation/models/language_translation.py`
  - Inherits `language.job.status.mixin`; fields: entry_id, target_language, translated_text
  - `_handle_completed` / `_handle_failed` with idempotency check (skip if already terminal)
  - UNIQUE constraint on (entry_id, target_language)
- [x] `language_translation`: extend `language.entry` with `translation_ids` + `_enqueue_translations()`
  - `src/addons/language_translation/models/language_entry_translation.py`
  - Overrides `create()` to auto-enqueue for user's learning languages
  - `pvp_eligible` computed from `@api.depends('translation_ids.status')` — True when any completed
- [x] `language_translation`: security rules (ir.model.access.csv + record rules)
  - Language Users: read own translations only; admin: full CRUD
- [x] `language_translation`: cron scheduled action for consuming result queues
  - `data/ir_cron_translation.xml` — runs every 1 minute, calls `action_consume_results()`
  - Fixed: removed `numbercall` field (removed in Odoo 17+)
- [x] `language_translation`: backend views (list/form)
  - `views/language_translation_views.xml` — list with status colors, form with retry button
  - Fixed: replaced `attrs=` with Odoo 18 `invisible=` syntax
- [x] `language_translation`: manifest with all data files listed
- [x] Portal view: show translations on entry detail; spinner for processing; retry button for failed
  - `src/addons/language_words/views/portal_vocabulary.xml` — translations table added
  - Retry route: `language_translation/controllers/portal.py` (avoids reverse dep on language_words)
- [x] Translation service (FastAPI): daemon consumer thread + `_translate()` + result publish
  - `services/translation/main.py` — auto-reconnects on failure; graceful argostranslate fallback
  - Stub translation: `[stub:src→tgt] text` (argostranslate deferred — see ADR-024)
- [x] Translation service: requirements.txt — lean (no argostranslate/torch); ~16s build
  - Comment in requirements.txt explains how to enable real translation in production
- [x] Translation service: docker-compose env_file + RABBITMQ_* env vars with defaults
- [x] Tests: 18 tests covering model, state machine, enqueue-on-save, idempotency, pvp_eligible, retry
  - `_patch_publish()` context manager; `_get_auto_translation()` to avoid UNIQUE constraint
- [x] `language_words/models/language_user_profile.py`: `_get_or_create_for_user` accepts recordset or int

#### Verification steps passed

- [x] `--update language_core,language_translation --stop-after-init` — 0 errors, modules loaded
- [x] 18 language_translation tests pass (0 failures, 0 errors)
- [x] All prior tests still pass: language_security (3), language_core (4), language_words (29)
- [x] `make up-translation-no-cache` — image rebuilt in ~16s; container running
- [x] `curl http://localhost:8001/health` — `{"status":"ok","service":"translation","argos_ready":false,"consumer_alive":true}`
- [x] `make logs-translation` — pika connected to RabbitMQ; "Translation consumer started. Waiting for messages…"
- [x] E2E test via rabbitmqadmin: published `translation.requested` → service processed → `translation.completed` contains `[stub:en→uk] apple`
- [x] Cron confirmed in DB: `id=20, cron_name='Lexora: Consume Translation Results', active=t, interval_number=1, interval_type=minutes`

#### Decisions made during this milestone

- ADR-023 (see DECISIONS.md): cron-based `basic_get` consumer for Odoo side (not push-based)
- ADR-024 (see DECISIONS.md): argostranslate deferred from image; stub fallback in service
- Odoo 18 cron: `numbercall` field removed; `attrs=` replaced by `invisible=` in views
- `_get_or_create_for_user` now handles both recordset and int user_id
- Retry route in `language_translation/controllers/portal.py` to avoid reverse dep on language_words

#### Known limitations at M3 exit

- argostranslate not installed → all translations are stubs (`[stub:src→tgt] text`). Real translation requires `argostranslate==1.9.6` added to a separate `requirements-full.txt` and a dedicated Dockerfile build.
- Portal entry detail page with translations was not verified in a browser (automation covers model layer; UI QA deferred).
- Cron fires every 1 minute; there may be up to 1 minute of latency between a job completing and Odoo picking it up in dev.

---

### M2 — Learning Entries

**Status:** Complete and verified.
**Started:** 2026-04-13
**Completed:** 2026-04-13

#### Sub-steps completed

- [x] `language_words`: implement `language.entry` model (all SPEC §3.1 fields)
  - type, source_text, normalized_text, source_language, owner_id, is_shared, status,
    created_from, copied_from_user_id, copied_from_entry_id, media_links, pvp_eligible
  - Deferred: copied_from_post_id (M7), translations/enrichments/audio One2manys (M3-M6)
- [x] `normalize()` function per SPEC §3.2
  - NFC, lowercase, strip, collapse whitespace, smart punctuation → ASCII, strip trailing .!?
- [x] Dedup check on `create()` and `write()` — raises ValidationError on collision
  - Dedup key = normalize(source_text) + source_language + owner_id (ADR-003)
  - Type NOT in key (ADR-003 verified by test)
- [x] `language.user.profile` model (SPEC §3.3)
  - native_language, learning_languages (Many2many → language.lang), default_source_language,
    pvp stats, is_shared_list; `_get_or_create_for_user()` lazy helper
- [x] `language.lang` lookup model — seeded uk/en/el (ADR-020)
- [x] Language detection via `langdetect==1.0.9` (added to base-requirements.txt)
  - Confidence threshold 0.7; falls back to user profile default (ADR-022)
- [x] Portal views: vocabulary list, detail, add-entry form, shared view (in language_words, ADR-021)
- [x] Sharing: `is_shared` toggle; record rules: owner full CRUD; shared entries readable by all Language Users
- [x] `language.media.link` model with URL format validation
- [x] Portal controller: /my/vocabulary, /new, /<id>, /shared, /share, /archive, /copy, /detect_language
- [x] Backend views: list/form/search for language.entry and language.user.profile

#### Verification steps passed

- [x] Scripted M2 verification (all 7 PLAN steps):
  1. Add 'apple' (en) → saved, normalized='apple'
  2. Add 'Apple ' (en) → ValidationError (duplicate)
  3. Add 'яблуко' (uk) → saved
  4. Add 'How are you?' (en) → saved, normalized='how are you'
  5. Add 'How are you' (en) → ValidationError (trailing ? stripped)
  6. Share 'apple' → user_b can find it via search (record rule)
  7. user_b copies 'apple' → new entry with correct provenance fields
- [x] 29 automated tests pass: 16 normalize tests + 13 language_entry tests

#### Decisions made during M2

- ADR-020: language.lang lookup model for learning_languages
- ADR-021: portal views in language_words (follow PLAN, not ARCHITECTURE)
- ADR-022: langdetect with 0.7 threshold; single-word detection unreliable (known limitation)
- `langdetect` installed in running container; persisted to base-requirements.txt; rebuild needed for new containers

#### Known limitations at M2 exit

- Single short-word language detection is unreliable (e.g. "яблуко" → "ru"). User can always correct manually.
- `langdetect` is installed in running container; permanent only after `make up-odoo-no-cache` rebuilds the image.
- Portal views are functional but unstyled beyond Bootstrap basics — no custom CSS yet.
- copied_from_post_id field deferred to M7 (language.post doesn't exist).
- pvp_eligible always False until M3 adds translation records.
- `--no-http` required for all CLI init/test commands while main Odoo service is running.

---

### M1 — Core Module Scaffold + Auth

**Status:** Complete and verified.
**Started:** 2026-04-13
**Completed:** 2026-04-13

#### Sub-steps completed

- [x] Create 11 module scaffolds (manifests, __init__ files, security CSVs, views dirs)
  - All modules in `src/addons/language_*` created with `__init__.py`, `__manifest__.py`,
    `models/__init__.py`, `security/ir.model.access.csv`, `views/`, `data/`, `tests/`
- [x] `language_security`: security groups XML + auto-assignment hook on res.users
  - Three groups defined: `group_language_user`, `group_language_moderator`, `group_language_admin`
  - Implication chain: moderator → user; admin → moderator (ADR-004)
  - Auto-assignment via `implied_ids` on `base.group_portal` (no code hook needed)
  - `password_security` declared as dependency
- [x] `language_core`: system parameters XML + job status mixin + RabbitMQ publisher stub
  - `ir.config_parameter`: `language.pvp.min_entries=10`, `language.audio.max_upload_bytes=10485760`
  - `language.job.status.mixin` abstract model: `job_id`, `status`, `error_message`, helpers
  - `RabbitMQPublisher` stub class with `publish(event_type, payload, job_id)` interface
  - `web_notify` declared as dependency
- [x] Tests for language_security (groups exist, implication chain, portal signup hook)
  - `language_security/tests/test_security_groups.py`: 3 tests
- [x] Tests for language_core (system parameter defaults + mixin)
  - `language_core/tests/test_system_parameters.py`: 2 tests
  - `language_core/tests/test_job_status_mixin.py`: 2 tests
- [x] Verify all modules install cleanly via --init
  - 55 modules loaded (11 custom + 44 pulled-in deps), 0 errors
  - All 7 tests pass, 0 failures

#### Verification steps passed

- [x] All 11 `language_*` modules install via `--init --no-http --stop-after-init` — 0 errors
- [x] All 7 tests pass (language_security: 3, language_core: 4) — 0 failures
- Note: manual "Register portal user → confirm Language User group" is the remaining human
  verification step; automated tests confirm the implied_ids mechanism is in place.

#### Decisions made during M1

- **Auto-assignment via XML `implied_ids`**: `base.group_portal.implied_ids` includes
  `group_language_user`. This is the idiomatic Odoo approach; no Python `res.users.create()`
  override needed. Simpler, no risk of missing portal signup edge cases.
- **OCA addons as manifest deps**: `password_security` → `language_security`;
  `web_notify` → `language_core`; `base_search_fuzzy` → `language_words`;
  `website_require_login` + `website_menu_by_user_status` → `language_portal`.
  Ensures they install when our modules install without needing to list them separately in
  the `--init` command.
- **`--no-http` required for CLI init/test while Odoo service is running**: Port 8069 is
  held by the main Odoo process. All `--stop-after-init` and `--test-enable` commands must
  include `--no-http`. Document this in the M2 verification section.

#### Known limitations at M1 exit

- All language_* modules except language_security and language_core are pure stubs (no models
  or views yet). They install cleanly but do nothing.
- Manual human verification pending: register a portal user via the web UI and confirm they
  appear in `group_language_user` in the Odoo backend.

---

### M0 — Infrastructure Foundation

**Status:** Complete and verified by user.
**Completed:** 2026-04-13

#### Sub-steps completed

- [x] Created `docker_compose/redis/docker-compose.yml`
  - Redis 7-alpine, AOF persistence, no password (dev default)
- [x] Created `docker_compose/rabbitmq/docker-compose.yml`
  - RabbitMQ 3-management, ports 5672 + 15672
  - Credentials: `${RABBITMQ_USER:-guest}` / `${RABBITMQ_PASS:-guest}`, overridable via `.env`
- [x] Created `services/translation/` — FastAPI stub, `/health` endpoint
- [x] Created `services/llm/` — FastAPI stub, `/health` endpoint
- [x] Created `services/anki/` — FastAPI stub, `/health` endpoint
- [x] Created `services/audio/` — FastAPI stub, `/health` endpoint
- [x] Created `docker_compose/translation/` — Dockerfile + docker-compose.yml, port 8001
- [x] Created `docker_compose/llm/` — Dockerfile + docker-compose.yml, port 8002
- [x] Created `docker_compose/anki/` — Dockerfile + docker-compose.yml, port 8003
- [x] Created `docker_compose/audio/` — Dockerfile + docker-compose.yml, port 8004
- [x] Updated `src/configs/odoo.conf`: `workers = 3` → `workers = 4`
- [x] Updated `Makefile`: added `up-dev`, `down-dev`, per-service up/down/logs targets for rabbitmq/translation/llm/anki/audio, and `up-*-no-cache` variants
- [x] Updated `env.example`: added `RABBITMQ_USER/PASS/VHOST/HOST/PORT` and `REDIS_HOST/PORT`
- [x] Fixed `docs/PLAN.md` M0 verification commands: Odoo port 8069 → 5433 (nginx-exposed)

#### Verification steps passed (confirmed by user)

- [x] `make up-dev` — all services start without errors
- [x] `http://localhost:15672` — RabbitMQ management UI accessible
- [x] `docker exec redis redis-cli ping` — returns PONG
- [x] `http://localhost:8001/health` — `{"status":"ok","service":"translation"}`
- [x] `http://localhost:8002/health` — `{"status":"ok","service":"llm"}`
- [x] `http://localhost:8003/health` — `{"status":"ok","service":"anki"}`
- [x] `http://localhost:8004/health` — `{"status":"ok","service":"audio"}`
- [x] `http://localhost:5433` — Odoo setup wizard accessible via nginx

#### Decisions made during M0

- **Workers = 4**: nginx already routes `/websocket` → `odoo:8072`; no nginx change needed.
- **Build context `../..`** for all worker Dockerfiles: follows existing Odoo/nginx pattern; source code lives in `services/<name>/`.
- **No `env_file` in worker composes yet**: stubs have no env-var dependencies. Add `env_file: ../../.env` to each worker compose when real RabbitMQ consumers are implemented (M3–M6).
- **Redis no-password for dev**: acceptable; production will need `requirepass`.
- **`elasticsearch==9.1.1` left in `base-requirements.txt`**: not blocking; can be removed in M1 cleanup.

#### Known limitations at M0 exit

- Worker services are stubs only; no RabbitMQ consumers yet.
- Odoo database not initialised; `/web/health` requires setup wizard completion.
- No Odoo custom modules installed yet (begins M1).

---

## How to use this file

### Starting a new milestone

Add a block at the top under "Current Milestone":

```markdown
### M<N> — <Name>

**Status:** In progress
**Started:** <date>

#### Sub-steps

- [ ] Step 1
- [ ] Step 2
...

#### Verification steps passed

(none yet)

#### Decisions made during this milestone

(none yet)

#### Blockers

(none)
```

### During implementation

After completing each sub-step, change `[ ]` to `[x]` and add a one-line note if a decision was made.
After each verification step passes, mark it under "Verification steps passed."
If a blocker is encountered, add it under "Blockers" with a short description and whether it is resolved.

### Completing a milestone

1. Mark all sub-steps and verifications complete.
2. Move the completed block to "Completed Milestones."
3. Reset "Current Milestone" to "None in progress."
4. Commit `docs/TASKS.md` together with the final sub-step of the milestone.
