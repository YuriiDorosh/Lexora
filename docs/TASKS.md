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

None in progress. M3 complete and verified. Awaiting confirmation to begin M4.

---

## Completed Milestones

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
