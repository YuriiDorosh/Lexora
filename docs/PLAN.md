# Lexora — Implementation Plan (MVP)

> Version: 2.8 (M35 — Multi-word YouTube Subtitle Selection — Complete)
> Last updated: 2026-05-16
> Status: M0–M25 complete; M26 postponed (resource constraints); M27–M35 complete

---

## Guiding Principles

- Work in **vertical slices**: each milestone delivers a complete, testable user-facing capability.
- Each milestone has explicit **verification commands** to run locally.
- No milestone is marked complete until its verification criteria pass.
- Changes must remain testable; prefer small focused commits per feature.
- Do not implement milestone N+1 until milestone N is verified.

---

## Milestone Overview

> **Note (2026-04-20):** Implementation proceeded in a different order than originally planned.
> M9 (Dashboards/SRS) and M10 (PvP Arena) were built before M7 (Posts) and M8 (Chat).
> The table below reflects **actual** completion status.

| # | Name | Status | What it delivers |
|---|---|---|---|
| M0 | Infrastructure Foundation | ✅ Complete | Docker Compose stack boots; Odoo reaches the setup screen |
| M1 | Core Module Scaffold + Auth | ✅ Complete | All custom modules installed; signup assigns Language User role |
| M2 | Learning Entries | ✅ Complete | Manual add, dedup, visibility, language detection prefill |
| M3 | Translation Service | ✅ Complete | RabbitMQ-backed translation events flow end-to-end |
| M4 | LLM Enrichment Service | ✅ Complete | Enrichment events flow; results visible on entry |
| M4b | Real CPU-only LLM | ✅ Complete | Qwen2.5-1.5B GGUF via llama-cpp-python (ADR-027) |
| M4c | Translation / Enrichment split | ✅ Complete | `deep_translator` online API; LLM restricted to source-language enrichment (ADR-028) |
| M5 | Anki Import Service | ✅ Complete | .apkg and .txt import with dedup and persistent import log |
| M6 | Audio (Recording + TTS) | ✅ Complete | Record button works; TTS generation via async service |
| M7 | Posts, Articles, Comments | ✅ Complete | Draft → review → publish flow; comments with @mentions; copy-to-list from posts |
| M8 | Chat & DMs | ✅ Complete | Public language channels + private DMs; save-to-list from chat (killer feature) |
| M9 | SRS Core + Dashboards | ✅ Complete (resequenced) | SM-2 spaced repetition, `/my/practice`, leaderboard, vocabulary pro dashboard |
| M10 | PvP Arena + XP System | ✅ Complete (resequenced) | Async word duels, XP/streak/levels, personal dashboard, Lexora Bot |
| M11 | XP Shop | ✅ Complete | Spend XP on Streak Freeze, Profile Frames, Double XP Booster; `/my/shop` portal |
| M12 | Knowledge Hub | ✅ Complete | Gold Vocabulary (3184 most common EN words with CEFR/POS); Grammar Encyclopedia (6 sections); `/useful-words` + `/grammar` portal |
| M13 | PDF Export Suite | ✅ Complete | Printable PDF cheat sheets from personal vocabulary, Gold Vocabulary (by CEFR level), and Grammar sections |
| M14 | Premium Visual Identity | ✅ Complete | Dark animated hero, glassmorphism, Inter/Montserrat fonts, Avantgarde Systems branding, premium login page |
| M15 | AI Translator Tool | ✅ Complete | Google-Translate-style `/translator` page; en/uk/el; sync deep_translator API; Add to Vocabulary integration |
| M16 | Legal Protection + Documentation | ✅ Complete | Proprietary LICENSE; professional README overhaul (Avantgarde Systems branding, full feature catalogue, tech stack) |
| M17 | AI Situational Roleplay | ✅ Complete | 6 AI-powered conversation scenarios; `/my/roleplay` glassmorphism chat UI; LLM `/roleplay` sync endpoint; grammar corrections in-context |
| M18 | Grammar Pro — Cloze Tests | ✅ Complete | 110 EN+Greek fill-in-the-blank exercises; `/my/grammar-practice`; multiple-choice with instant green/red feedback; CEFR A1–B2 filters |
| M18.5 | Header UI Redesign | ✅ Complete | Category dropdown navbar (Practice / Library / Tools); glassmorphism mobile-friendly |
| M19 | Natural Speech Hub — Idioms & Phrasal Verbs | ✅ Complete | 100+ phrasal verbs (EN) + idioms (EL/UK); interactive flip-card expression cards; `/idioms` portal |
| M20 | Survival Phrasebook — Tourist Kits | ✅ Complete | Essential phrase sets grouped by scenario; one-click Copy to Roleplay Chat; `/phrasebook` portal |
| M21 | Sentence Builder — Syntax Master | ✅ Complete | Word-ordering game using M18 sentence dataset; click-to-order mechanics; XP award; `/my/sentence-builder` |
| M22 | Browser Extension — Scaffold & Odoo API | ✅ Complete | Chrome Extension MV3 scaffold; `/lexora_api/add_word` Odoo endpoint; glassmorphism popup |
| M23 | Browser Extension — Contextual Capture | ✅ Complete | Right-click "Add to Lexora" context menu; surrounding sentence capture for Sentence Builder |
| M24 | Browser Extension — Media & Subtitles | ✅ Complete | YouTube/Netflix subtitle overlay; click-word mini-popup with definition + Add to List |
| M25 | Browser Extension — Mini-Practice New Tab | ✅ Complete | New Tab override with daily vocabulary card; animated dark gradient; OdooBot greeting |
| M26 | AI Helpdesk — RAG Auto-Reply | ⏸ Postponed | Requires pgvector + llama-cpp + fastembed (~2.5 GiB RAM on top of existing stack); postponed until a higher-RAM server is available |
| M27 | Browser Extension — Review in the Wild | ✅ Complete | Known vocabulary highlighted on any webpage; SRS-aware tooltip with simultaneous 🇺🇦/🇬🇷 translations; 15-min cached word list; MutationObserver debounced re-scan |
| M28 | Browser Extension — Grammar Explainer | ✅ Complete | "Explain Grammar" button in Quick Look + YouTube overlays; Qwen 1.5B via Odoo proxy; draggable scrollable overlays with `!important` flex enforcement |
| M29 | Polish Language Support (System-Wide) | ✅ Complete | Polish (`pl` / 🇵🇱) is a first-class language across DB selectors, controllers, FastAPI services (`pl-PL` MyMemory locale, `pl-PL-ZofiaNeural` Edge TTS, `espeak-ng pl`, LLM `LANG_NAMES`), browser extension (Polish-diacritic detection regex, Quick Look + tooltip 🇵🇱 row, New Tab card), portal templates, and Anki/profile/translator forms. Auto-translates all new entries to en/uk/el/pl. 1055 existing entries backfilled. Canonical `LANGUAGE_SELECTION` import enforced across translation/enrichment/audio (ADR-029) |
| M30 | AI Speaking Coach & Oral Practice | ✅ Complete | `/my/speaking` portal with topic generation, browser mic recording, Faster-Whisper sync transcription, and Qwen2.5-1.5B feedback (corrections / synonyms / improved version). `language.speaking.session` persists transcripts + feedback per user. 4-language support; 90 s soft cap; sync HTTP pipeline (no RabbitMQ) per ADR-030 |
| M31 | Browser Extension — Lexora Writer | ✅ Complete | Active-writing assistant. Floating "L" FAB on every focused `<textarea>` / `[contenteditable]`; strict eligibility (skips passwords / search / code editors / login forms). Click → `POST /lexora_api/writer_check` → LLM `POST /analyze-writing` → corrections + improved JSON. Apply-to-text uses the React-compatible native-setter + InputEvent pattern. Server-side safety net guarantees every text change is documented (ADR-031) |
| M32 | Browser Extension — Slang & Idiom Explainer | ✅ Complete | New "💡 Explain Slang/Idiom" button alongside the M28 "Explain Grammar" button in both Quick Look and YouTube overlays. `POST /lexora_api/explain_slang` → LLM `POST /explain-slang`; returns kind enum (idiom / slang / phrasal_verb / literal / unknown), figurative + literal meaning in the user's native language, example in source language, confidence enum. UI handles the literal and low-confidence branches honestly (ADR-031) |
| M33 | Browser Extension — Webpage Shadowing | ✅ Complete | Pronunciation practice on any webpage. "🎤 Practice Pronunciation" button in QL + YouTube overlays expands a Shadowing block with ▶ Play Original (Edge TTS via `POST /tts-sync`) and click-to-toggle Start/Stop Recording (mic on `chrome.offscreen` doc — granted once per extension). User audio runs through `/transcribe-sync` → `/evaluate-pronunciation`; deterministic Python word-diff is the source of truth for score + missed/mispronounced words; LLM contributes only the localised feedback string (ADR-032) |
| M34 | Browser Extension — YouTube Vocab Radar | ✅ Complete | Passive vocabulary radar for YouTube. Background fetches the user's vocabulary via new `GET /lexora_api/my_vocab`; main-world inject patches `XMLHttpRequest.prototype` + `window.fetch` to sniff `/api/timedtext` (JSON3 primary, SRV3/SRV1 XML fallback, DOM-observer for live streams). Content script builds a longest-match sliding-window index over the cue track and pauses the video ~4 s before a known word. Glassmorphism Shadow-DOM card shows the word + all-language translations (🇺🇦/🇬🇷/🇵🇱/🇬🇧) + the surrounding cue with the word highlighted, plus ⏪ Rewind 5 s & Play / ▶ Continue / 🔕 Skip this word / ✖ Disable for this video. Cooldown timer (default 120 s) starts at overlay close, not at fire, so the user can read the alert at their pace. Three Options-page controls + per-tab skip set + per-video kill switch. No persistence by default (ADR-033) |
| M35 | Browser Extension — Multi-word YouTube Subtitle Selection | ✅ Complete | Multi-word phrase lookup on YouTube subtitles via **Ctrl/⌘-Click multi-select** (Strategy C). Native browser selection (Strategy A) was implemented end-to-end and failed in browser smoke — YT's player aggressively re-applies `user-select: none` via JS on every cue render and the `selectstart` interception runs below event listeners. Strategy B (manual drag state machine) was rejected without smoke for the same cue-segment-volatility reason. Strategy C wins: the user Ctrl-clicks each word in the phrase (toggle semantics on re-click); the buffer is finalised on the LAST `Control`/`Meta` keyup (multi-key safe via post-event `e.ctrlKey \|\| e.metaKey` check); the concatenated phrase routes through the same `_openLookupOverlay` pipeline as M24's single-word click. Plain-click anywhere / Escape / `yt-navigate-finish` clear the buffer. Click order preserved (NOT spatial). Every downstream Quick Look feature (Add to Vocabulary, Explain Grammar M28, Explain Slang/Idiom M32, Practice Pronunciation M33) inherits phrase support unchanged. Visually robust, deterministic (always whole-word), immune to YT's selection-suppression. 16/16 sandbox cases pass; browser smoke confirmed (ADR-034) |

---

## M0 — Infrastructure Foundation

**Goal:** All Docker services start without errors. Odoo reaches the web setup page.

**Work:**
1. Create `docker_compose/redis/docker-compose.yml` — this file does not exist yet despite the Makefile already having `up-redis` / `down-redis` / `logs-redis` targets.
2. Create `docker_compose/rabbitmq/docker-compose.yml` — RabbitMQ is referenced in requirements (`pika==1.3.2`) but has no compose file yet.
3. Create stub `docker_compose/translation/`, `docker_compose/llm/`, `docker_compose/anki/`, `docker_compose/audio/` directories with minimal FastAPI Dockerfiles and `/health` endpoints.
4. Add a `docker-compose.dev.yml` (or update the existing Makefile structure) that brings up: `postgres`, `odoo`, `rabbitmq`, `redis`, `nginx`, and all four worker service stubs.
5. Confirm network connectivity between all services.
6. Update `Makefile` with a single `make up-dev` command that starts the full dev stack.

**Note on existing compose files:** PostgreSQL (`postgres:15`) and Odoo compose files already exist under `docker_compose/db/` and `docker_compose/odoo/`. Use them as-is; do not change the Postgres version.

**Verification:**
```bash
make up-dev
# Wait ~60 seconds for Odoo to initialise

# Odoo is exposed through nginx on host port 5433 (not 8069 directly)
curl http://localhost:5433/web/health         # {"status": "pass"} — Odoo HTTP server up
                                              # Note: requires database to be initialised;
                                              # on first boot, use the Odoo setup wizard at
                                              # http://localhost:5433 to create the database.

curl http://localhost:15672                   # RabbitMQ management UI (guest/guest)
docker exec redis redis-cli ping              # PONG
curl http://localhost:8001/health             # {"status":"ok","service":"translation"}
curl http://localhost:8002/health             # {"status":"ok","service":"llm"}
curl http://localhost:8003/health             # {"status":"ok","service":"anki"}
curl http://localhost:8004/health             # {"status":"ok","service":"audio"}
```

---

## M1 — Core Module Scaffold + Auth

**Goal:** All 11 custom Odoo modules install cleanly. Signup automatically assigns `Language User` group.

**Work:**
1. Create stub `__manifest__.py` + `__init__.py` for all modules in install order:
   `language_security` → `language_core` → `language_words` → `language_translation` → `language_enrichment` → `language_audio` → `language_anki_jobs` → `language_chat` → `language_dashboard` → `language_pvp` → `language_portal`
2. `language_security`: define security groups (`group_language_user`, `group_language_moderator`, `group_language_admin`). Add auto-assignment hook on `res.users` write for portal signup.
3. `language_core`: define system parameters (min PvP entries = 10, audio max upload = 10 MB). Stub RabbitMQ publisher class. Stub job status mixin.
4. Install and configure `website_require_login` and `website_menu_by_user_status` addons (files present in `src/addons/`, must be initialised in the database) so unauthenticated users see only the login/signup page.
5. Install `password_security` addon (files present in `src/addons/`, must be initialised) and verify it is active.

**Note on OCA addons in src/addons/:** The following addons are present as files (mountable) but are NOT yet installed in the Odoo database. They must be explicitly initialised:
- `base_search_fuzzy` — requires `pg_trgm` PostgreSQL extension; install via `--init base_search_fuzzy`
- `web_notify`, `password_security`, `website_menu_by_user_status`, `website_require_login`

**Verification:**
```bash
# Install all modules via Odoo CLI (creates/updates the database)
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora \
  --init language_security,language_core,language_words,\
language_translation,language_enrichment,language_audio,language_anki_jobs,\
language_chat,language_dashboard,language_pvp,language_portal,\
base_search_fuzzy,web_notify,password_security,\
website_menu_by_user_status,website_require_login \
  --stop-after-init

# Register a new user via the portal signup page
# → Log in as that user
# → Confirm they appear in group_language_user (Odoo backend > Users)
```

---

## M2 — Learning Entries

**Goal:** A Language User can add, view, edit, and archive entries. Dedup works. Sharing toggle works.

**Work:**
1. `language_words`: implement `language.entry` model with all fields from SPEC §3.1.
2. Implement `normalize()` function per SPEC §3.2 dedup rules.
3. Implement dedup check on `create()`: if duplicate found, raise `ValidationError` with user-friendly message.
4. Implement `language.user.profile` model (§3.3).
5. Integrate language detection library (e.g., `langdetect` or `lingua-py`) for source language prefill.
6. Portal views: vocabulary list page, entry detail page, add-entry form with language detection.
7. Sharing: `is_shared` toggle on the entry; record rules to expose shared entries to other Language Users.
8. `language.media.link` model: URL + title/description, basic URL format validation.

**Verification:**
```bash
# Manual test via portal:
# 1. Add entry "apple" (en) → saved successfully
# 2. Add entry "Apple " (en) → duplicate detected, blocked
# 3. Add entry "яблуко" (uk) → auto-detected as uk, saved
# 4. Add "How are you?" (en) → saved
# 5. Add "How are you" (en) → duplicate detected (trailing ? stripped in dedup)
# 6. Mark "apple" as shared → confirm another user can see it in shared entries view
# 7. Second user copies shared "apple" → new entry created in second user's list
```

---

## M3 — Translation Service

**Goal:** Translation requests flow end-to-end. Results appear on the entry page.

**Work:**
1. `language_core`: implement RabbitMQ publisher (publish event with `job_id` UUID).
2. `language_core`: implement RabbitMQ consumer (Odoo scheduled action or thread polling result queues).
3. `language_translation`: implement `language.translation` model with status state machine.
4. On entry save (manual or copy-from-post): automatically publish `translation.requested` for each user learning language.
5. Translation Service (FastAPI): consume `translation.requested`, run Argos Translate, publish `translation.completed` / `translation.failed`.
6. Odoo consumer: on `translation.completed`, update `language.translation` record with result and `status = completed`.
7. Portal view: show translation results on entry detail page. Show spinner while `status = processing`.
8. Retry button on `status = failed`.

**Verification:**
```bash
# 1. Add entry "apple" (en), user's learning language = uk
# 2. Check RabbitMQ management UI: translation.requested message published
# 3. Wait ~10 seconds
# 4. Check entry detail page: translation shows "яблуко" (or equivalent Argos output)
# 5. Check language.translation record: status = completed
# 6. Kill translation service, add new entry, wait → status = failed, retry button shown
# 7. Restart service, press retry → translation completes
```

---

## M4 — LLM Enrichment Service

**Goal:** User can request enrichment from the entry detail page. Results (synonyms, antonyms, examples, explanation) appear.

**Work:**
1. `language_enrichment`: implement `language.enrichment` model with status state machine.
2. Portal view: "Enrich" button on entry detail page; publish `enrichment.requested`.
3. LLM Service (FastAPI): load Qwen3 8B (or configured model), consume `enrichment.requested`, generate structured output, publish `enrichment.completed`.
4. Odoo consumer: on `enrichment.completed`, populate `language.enrichment` record.
5. Display enrichment results on entry detail page (synonyms list, antonyms list, example sentences, explanation paragraph).
6. Handle `enrichment.failed`: show error badge + retry button.

**Verification:**
```bash
# 1. Open entry "apple" detail page
# 2. Click "Enrich"
# 3. Status shows "processing" (spinner or badge)
# 4. LLM service logs show job received and processed
# 5. After completion (may take 30–120s on CPU): page shows synonyms, antonyms, examples, explanation
# 6. Check language.enrichment record: status = completed, fields populated
```

---

## M4c — Translation / Enrichment responsibility split

**Status:** Planned (branch `m4c`, follows M4b on `main`).

**Motivation:** M4b deployed Qwen2.5-1.5B on the target server and produced demonstrably wrong Ukrainian translations (e.g. `strut → труси`, `arrogant → арган`, `vice versa → Віка універсальна`). A 1.5B local model cannot be trusted for translation, and upgrading to 3B or 8B is impractical on an 8 GiB AVX-only host (ADR-027). M4c formalises the split documented in ADR-028:

- **LLM service** → enrichment only, always in the entry's source language.
- **Translation service** → free online API wrapper (`deep_translator`) with provider fallback. Internet-dependent; offline commitment in SPEC §4.3 is dropped.

**Goal:** Translation accuracy matches a production Google-Translate-quality baseline for en/uk/el in all six directions. No Odoo-side schema, event, or test changes. Enrichment behaviour is unchanged in practice (it was already passing `source_language`).

**Work:**
1. ADR-028 in `docs/DECISIONS.md` ✅ (already landed with this plan).
2. `docs/SPEC.md`: amend §4.3 to describe the online-API translation path, record the internet dependency, and close OD-2 (Argos uk↔el) by removal. Amend §4.4 to state explicitly that enrichment is source-language-only.
3. `services/translation/requirements.txt`: add `deep_translator==1.11.4`. Drop the Argos comment block from M3/ADR-024.
4. `services/translation/main.py`: replace the current stub `_translate()` with a real implementation:
   - Primary provider via `deep_translator.GoogleTranslator(source=src, target=tgt).translate(text)`.
   - Timeout enforced with `socket.setdefaulttimeout()` or a requests-level timeout.
   - On any provider exception → fallback to `MyMemoryTranslator` once, then mark the job `failed`.
   - Log every provider switch so production can trace blocks / outages.
   - Retain the existing event shape and the RabbitMQ consumer thread.
5. `docker_compose/translation/docker-compose.yml`: add env vars `TRANSLATE_PROVIDER=google`, `TRANSLATE_FALLBACK_PROVIDER=mymemory`, `TRANSLATE_TIMEOUT_SECONDS=10`. Propagate to `env.example`.
6. `docker_compose/translation/Dockerfile`: verify no extra build tooling is required (`deep_translator` is pure Python). Keep `python:3.11-slim`.
7. `services/llm/main.py`: tighten `_SYSTEM_PROMPT` to "Output in the same language as the input text." The service already only ever receives `source_language`; this is defence-in-depth.
8. Keep Odoo modules untouched. Do not touch `language.translation` or `language.enrichment` schemas, events, or tests.

**Verification:**

```bash
# 1. Rebuild translation service with new deps
make up-translation-no-cache
curl http://localhost:8001/health
# → {"status":"ok","service":"translation","provider":"google","ready":true}

# 2. End-to-end via RabbitMQ — all six pairs
for pair in "en uk" "en el" "uk en" "uk el" "el en" "el uk"; do
  set -- $pair
  docker exec rabbitmq rabbitmqadmin --username=guest --password=guest \
    publish exchange=amq.default routing_key=translation.requested \
    payload="{\"job_id\":\"m4c-$1-$2\",\"event_type\":\"translation.requested\",\"payload\":{\"entry_id\":9000,\"source_text\":\"apple\",\"source_language\":\"$1\",\"target_language\":\"$2\"}}" \
    properties='{"content_type":"application/json"}'
done
# Fetch translation.completed, confirm real values, no [stub:…] prefix.

# 3. Portal click-through (on dev host or server):
#    Add entry "strut" (en), profile.learning_languages = [uk, el]
#    → translation.uk and translation.el appear on the entry detail page
#    → must be "розпірка/виставлятися" (not "труси") and a correct Greek rendering.

# 4. Regression: existing 71 tests remain green.
docker exec odoo odoo --config /etc/odoo/odoo.conf -d lexora \
  --test-enable --no-http --stop-after-init -u language_translation,language_enrichment

# 5. Provider-outage drill:
#    Temporarily set TRANSLATE_PROVIDER=mymemory, restart service, re-run step 2.
#    Confirm MyMemory path works. Restore the default.
```

**Acceptance:** Real en/uk/el translations for all six pairs; no stub output; Odoo-side tests green; provider swap demonstrated.

---

## M5 — Anki Import Service

**Goal:** User can upload .apkg or .txt; entries are created with dedup; import log is persistent.

**Work:**
1. `language_anki_jobs`: implement `language.anki.job` model.
2. Portal upload page: file upload form with source language selection and field mapping UI.
3. Auto-detect field mapping for `.apkg` (Front/Back convention); fall back to manual field selection UI.
4. On submit: store upload in temp, publish `anki.import.requested`.
5. Anki Import Service: parse `.apkg` (SQLite extract), parse `.txt` (TSV), apply dedup normalization, extract audio from `.apkg` if present, return results.
6. Odoo consumer: on `anki.import.completed`, create new `language.entry` records (skipping duplicates), create `language.audio` records (`audio_type = 'imported'`) for extracted audio, update `language.anki.job` with counts and skipped details.
7. Import result page: show created/skipped/failed counts. Show reviewable list of skipped items.

**Verification:**
```bash
# 1. Export a simple Anki deck as .apkg (use a test deck)
# 2. Upload via portal; confirm source language, accept auto-detected field mapping
# 3. Import completes: N entries created, 0 skipped
# 4. Re-import the same .apkg → 0 created, N skipped
# 5. Import a .txt file with 3 entries (2 new, 1 overlapping with .apkg import)
#    → 2 created, 1 skipped
# 6. Check persistent import log in portal: all 3 import jobs visible with details
# 7. If .apkg contains audio: verify language.audio records created
```

---

## M6 — Audio (Recording + TTS)

**Goal:** Audio button appears on every entry. User can record or generate pronunciation. Audio plays back.

**Work:**
1. `language_audio`: implement `language.audio` model.
2. Portal: add audio section to entry detail page.
   - Record button: browser MediaRecorder API → upload blob to Odoo endpoint → create `language.audio` (type=recorded).
   - Generate button: publish `audio.generation.requested` → show processing state → on completion, play audio.
3. Audio/TTS Service: consume `audio.generation.requested`, run piper (or espeak-ng fallback), return audio bytes.
4. Odoo consumer: on `audio.generation.completed`, create `ir.attachment` with audio data, link to `language.audio` record.
5. Audio player: HTML5 `<audio>` element with Odoo attachment URL.
6. Enforce 10 MB upload limit (configurable system parameter).

**Verification:**
```bash
# 1. Open any entry detail page → audio section visible
# 2. Click Record → browser asks for mic permission → record 5 seconds → save
#    → audio player appears; playback works
# 3. Click Generate → status shows processing
#    → after completion: audio player appears for generated audio
# 4. Try to upload a >10MB audio file → rejected with error message
# 5. Verify ir.attachment record exists for both recorded and generated audio
```

---

## M7 — Posts, Articles, Comments

**Goal:** Users can create draft posts; moderators approve. Comments with @mentions work. "Copy to my list" from article text works.

**Work:**
1. `language_portal`: implement `language.post` model (title, body, status: draft/pending/published/rejected, author, tags, media links).
2. Portal: post creation/editing UI for Language Users.
3. Submit-for-review action → status = pending; moderator notification.
4. Moderator backend view (or portal moderator panel): approve/reject actions.
5. Comments model: flat, chronological, with author and @mention parsing.
6. "Copy to my list" inline popup: JavaScript text selection listener → popup → side panel form → entry creation + auto-translation.
7. Provenance tracking: `copied_from_post_id` on created entry.

**Verification:**
```bash
# 1. Log in as Language User → create post draft → submit for review
# 2. Log in as Moderator → see pending post → approve
# 3. Post appears in published posts list
# 4. Add comment with @mention of another user
# 5. Select a word in the post body → popup appears → save to my list
#    → new entry created, translation auto-queued
# 6. Verify entry has copied_from_post_id set
# 7. Moderator can delete comment; user can report comment
```

---

## M8 — Chat

**Goal:** Public channels and private DMs work. "Save to my list" from chat messages works.

**Work:**
1. `language_chat`: configure/extend Odoo Discuss for public channels with language context.
2. Add "start DM" action to user profile pages.
3. "Save to my list" from chat: text selection in chat → same inline popup as posts → entry creation.
4. Moderator access: can see and moderate public channels; DM content only via report flow.
5. Report message feature: user action → creates a moderation report record.
6. Moderator report review UI.

**Verification:**
```bash
# 1. Create a public channel "General" → two users join and exchange messages
# 2. Select text in a message → "Save to my list" popup → save entry
#    → entry appears in vocabulary with created_from = copied_from_chat
# 3. Start a DM from user A's profile as user B → DM thread works
# 4. Report a message → moderation report record created
# 5. Moderator sees the report and can delete the message
# 6. WebSocket connectivity: chat messages appear without page refresh
```

---

## M9 — Dashboards & Search

**Goal:** Personal and global dashboards render with real data. Vocabulary search (fuzzy + cross-language) works.

**Work:**
1. `language_dashboard`: implement dashboard views using Odoo ORM aggregations.
2. Personal dashboard: entry counts by type, recent activity, PvP stats placeholder, translation/enrichment counts.
3. Global dashboard: popular words (weighted score), word of the day (scheduled daily cron), most translated, most enriched, top language pairs.
4. Leaderboard page (PvP data; stub for now, populated in M10).
5. Vocabulary search: extend entry list view with ILIKE + `base_search_fuzzy` (must be installed and `pg_trgm` extension active — confirmed in M1), JOIN against translations for cross-language lookup.
6. Post/article search: simple ILIKE on title + body.

**Verification:**
```bash
# 1. Add 10 entries → personal dashboard shows correct count
# 2. Request translations for 5 entries → "most translated" dashboard reflects them
# 3. Search "apple" in vocabulary → finds entries with source text "apple" AND entries
#    whose translation is "apple" (e.g., a Ukrainian entry "яблуко")
# 4. Search with a typo ("appel") → fuzzy search returns "apple"
# 5. Word of the day widget shows a word → manually trigger cron → word changes
# 6. Popular words widget shows entries ordered by weighted score
```

---

## M10 — PvP Battle System

**Goal:** Full PvP battle flow works end-to-end: matchmaking → battle → result → leaderboard.

**Work:**
1. `language_pvp`: implement `language.pvp.battle`, `language.pvp.round` models.
2. Player stats on `language.user.profile`: wins, losses, draws, win_rate.
3. Matchmaking: Redis sorted set for queue per `(practice_lang, native_lang)`. 60s timeout then bot.
4. Bot logic: configurable difficulty with server-side answer simulation (medium = ~60% correct picks).
5. Battle UI: portal page, round display (source text + 4 translation choices), 30s countdown via Odoo bus push, answer submission.
6. Distractor selection: query player's own entries for other translations; fall back to shared distractor pool (small curated table of common words per language).
7. Disconnection: Redis grace key (15s TTL) per player; on expiry, forfeit + opponent win.
8. Result: write battle record, update player stats, push result via Odoo bus.
9. Leaderboard page: rank by win count, filterable by language pair.
10. Minimum entry gate: check against system parameter before allowing battle start.

**Verification:**
```bash
# Pre-condition: two users each have ≥10 entries in the same language pair

# 1. User A starts battle (practice: en, native: uk)
# 2. User B starts battle (same language pair) within 60s
#    → both matched; battle starts; both see round 1 simultaneously
# 3. Play 20 rounds; verify countdown timer works
# 4. Winner determined by correct answers; result appears for both players
# 5. Check language.pvp.battle record: both players, 20 rounds, correct counts, outcome
# 6. Check player profile: win/loss/win_rate updated correctly

# Bot battle:
# 7. Start battle with no other player waiting → 60s pass → bot battle starts
# 8. Complete 20 rounds against bot → result saved in history
# 9. Bot battle counts in win_rate

# Disconnection:
# 10. Start matched battle → close browser tab for one player
#     → after 15s grace: forfeit, opponent gets win, result saved

# Leaderboard:
# 11. Leaderboard page shows both players ranked by win count
# 12. Filter by language pair works
```

---

## Cross-Cutting Work (any milestone)

- **Security review:** ensure all portal endpoints validate user ownership before read/write.
- **GDPR / account deletion:** implement delete-account flow (private entries deleted, chat/posts anonymized, audio files removed, leaderboard entry removed). Can be done in M2 or M7.
- **Error observability:** job failure events must write error messages to the job record. Admin can query stuck or failed jobs.
- **System parameters UI:** admin panel for configurable values (min PvP entries, audio max size, bot difficulty).

---

## M11 — XP Shop

**Goal:** Users can spend XP on meaningful in-app items. XP becomes a full economy: earned through practice/duels, spent in the shop.

**Items (initial catalogue):**

| Item | XP Cost | Effect |
|---|---|---|
| Streak Freeze | 50 XP | Prevents streak reset for 1 missed day |
| Profile Frame | 100 XP | Cosmetic border on leaderboard avatar |
| Double XP Booster | 80 XP | Next 5 practice reviews award 2× XP |

**Work:**

1. `language.shop.item` model: `name`, `description`, `xp_cost` (Integer), `item_type` (Selection: `streak_freeze`/`profile_frame`/`double_xp`), `icon` (Char emoji or ir.attachment), `is_active` (Boolean).
2. `language.user.item` model: junction between user and owned/active items. Fields: `user_id`, `item_id`, `quantity`, `activated_at`, `expires_at`.
3. Purchase logic: `action_buy(user_id)` on `language.shop.item` — checks XP balance ≥ cost, deducts via `language.xp.log` (`reason='shop_purchase'`, negative amount), creates `language.user.item` record. Floor at 0 enforced.
4. Item effect hooks wired into existing systems:
   - `streak_freeze`: `_record_duel_activity` / `_update_gamification_for_user` checks for an active freeze before resetting streak.
   - `double_xp`: `_update_gamification_for_user` checks for active booster and doubles `xp_delta`; decrements remaining uses.
   - `profile_frame`: leaderboard template checks `user.active_frame` and applies a CSS class.
5. Portal `/my/shop`: grid of items with XP cost badge; "Buy" button; "Owned" badge if already held.
6. Portal `/my/inventory`: list of owned items with activation status and expiry.

**Verification:**

```bash
# 1. Admin seeds shop items via backend or data fixture
# 2. Portal /my/shop renders with 3 items; XP cost visible
# 3. Buy Streak Freeze (50 XP) → XP deducted, language.user.item created
# 4. Buy item when XP < cost → blocked with "Insufficient XP" message
# 5. Miss a day → streak NOT reset (freeze consumed)
# 6. Buy Double XP Booster → next 5 reviews award double XP, then normal resumes
# 7. language.xp.log shows entries with reason='shop_purchase', negative amounts
```

---

## M12 — Knowledge Hub

**Goal:** Users have a curated Gold Vocabulary of 3000 most common English words (with CEFR level, POS, and Ukrainian/Greek translations) and a Grammar Encyclopedia. Both are accessible from a new "Library" navbar dropdown.

**Part A — Gold Vocabulary (`language.seeded.word`)**

Items: word, CEFR level (A1–C2), part of speech, Ukrainian translation, Greek translation, sort order, translation status.

| Item | Detail |
|---|---|
| Model | `language.seeded.word` in `language_portal` |
| Portal route | `GET /useful-words` — tabbed by CEFR level, paginated (50/page), "➕ Add to My List" button per word |
| Add-to-list | `POST /useful-words/add` → creates `language.entry` (dedup via existing logic), auto-queues translation, `created_from='seeded_content'` |
| Seed data | Post-init hook reads `data/gold_vocabulary.json` (~3000 words); A1/A2 have full UK+EL translations; B1–C2 have English+metadata only (translations filled later by cron or user trigger) |

**Part B — Grammar Encyclopedia (`language.grammar.section`)**

Items: title, slug, category (selection), content_html (Html), sequence, is_published.

Initial content (6 sections):
1. **All 12 English Tenses** — form + usage + timeline example + Ukrainian/Greek equivalents
2. **Irregular Verbs** — table of ~200 verbs (Base / Past / Past Participle) with Ukrainian translation
3. **Articles (a/an/the/zero)** — rules with examples in EN/UK/EL
4. **Conditionals 0–3** — form + usage + translation pairs
5. **Modal Verbs** — can/could/may/might/must/should/would + equivalents
6. **Passive Voice & Reported Speech** — transformation rules + examples

| Item | Detail |
|---|---|
| Model | `language.grammar.section` in `language_portal` |
| Portal route | `GET /grammar` — sidebar nav by category; `GET /grammar/<slug>` — section detail |
| Seed | Post-init hook or XML fixture |

**Work:**
1. `language.seeded.word` model — `language_portal/models/language_seeded_word.py`
2. `language.grammar.section` model — `language_portal/models/language_grammar_section.py`
3. Update `language_portal/models/__init__.py`
4. Update `language_portal/security/ir.model.access.csv` with new model access rows
5. Generate `language_portal/data/gold_vocabulary.json` (3000 words from Volka English list)
6. Post-init hook: seed words + grammar sections from JSON/Python if not already present
7. `language_portal/controllers/portal_library.py` — `/useful-words`, `/useful-words/add`, `/grammar`, `/grammar/<slug>`
8. Update `controllers/__init__.py` to import `portal_library`
9. `language_portal/views/portal_library.xml` — useful words (CEFR tabs + pagination) + grammar (sidebar + section detail)
10. Update `data/website_menus.xml` — "Library" dropdown: "Useful Words" + "Grammar Guide"
11. Update `language_portal/__manifest__.py` — new files in `data`/`views`
12. Tests: word seeding idempotency, add-to-list, grammar section queries

**Verification:**
```bash
# 1. Install/update
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init

# 2. Word count
docker exec odoo odoo-bin shell -d lexora -c /etc/odoo/odoo.conf << 'EOF'
count = env['language.seeded.word'].sudo().search_count([])
print(f"Seeded words: {count}")  # expect ~3000
EOF

# 3. Portal smoke test
curl -b session_cookie http://localhost:5433/useful-words       # 200
curl -b session_cookie http://localhost:5433/grammar            # 200
curl -b session_cookie http://localhost:5433/grammar/tenses     # 200

# 4. Add-to-list
# POST /useful-words/add with {word_id: 1}
# → language.entry created with created_from='seeded_content'

# 5. Tests
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal \
  --test-enable --no-http --stop-after-init
# → all language_portal tests green
```

---

---

## M13 — PDF Export Suite

**Goal:** Users can generate beautiful, printable PDF "cheat sheets" from three sources: their personal vocabulary list, the Gold Vocabulary filtered by CEFR level, and any Grammar section. Uses Odoo's native QWeb-to-PDF engine (wkhtmltopdf 0.12.6.1, available in the container).

**Routes:**
- `GET /my/vocabulary/print` — personal vocabulary PDF (word | translation | example)
- `GET /useful-words/print?level=<CEFR>` — Gold Vocabulary for one CEFR level
- `GET /grammar/<slug>/print` — Grammar section with styled tables + code blocks

**UI integration:**
- "🖨️ Print Cheat Sheet" button on vocabulary list page
- "🖨️ Print Level" button on each CEFR tab in Useful Words
- "🖨️ Print" button in Grammar section sidebar

**Design:** 2-column layout for word lists, A4 page, minimal margins, repeating table headers across pages, dedicated `print_style.css`.

**Work:**
1. `language_portal/static/src/css/print_style.css` — print-optimised CSS (A4, 2-col grid, table headers).
2. `language_portal/views/pdf_vocabulary.xml` — QWeb report template for personal vocabulary.
3. `language_portal/views/pdf_gold_vocab.xml` — QWeb report template for CEFR-level Gold Vocabulary.
4. `language_portal/views/pdf_grammar.xml` — QWeb report template for grammar sections.
5. `language_portal/controllers/portal_print.py` — three print routes that render via `request.env['ir.actions.report']._render_qweb_pdf(...)` and return the PDF bytes as a werkzeug Response.
6. Update `__manifest__.py` — add new CSS, views, controller.
7. Add print buttons to `portal_library.xml` (useful-words + grammar) and inherit `language_words.portal_vocabulary_list` for the vocabulary print button.

**Verification:**
```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init

# Personal vocabulary PDF
curl -b cookies.txt -o /tmp/vocab.pdf \
  'http://localhost:5433/my/vocabulary/print'
file /tmp/vocab.pdf   # → PDF document

# Gold Vocabulary A1 PDF
curl -b cookies.txt -o /tmp/a1.pdf \
  'http://localhost:5433/useful-words/print?level=A1'
file /tmp/a1.pdf      # → PDF document

# Grammar tenses PDF
curl -b cookies.txt -o /tmp/tenses.pdf \
  'http://localhost:5433/grammar/tenses/print'
file /tmp/tenses.pdf  # → PDF document
```

---

## M17 — AI Situational Roleplay

**Goal:** Users can practice conversational language in 6 AI-powered scenarios.
The AI acts as a native speaker, provides in-context grammar corrections, and
maintains conversation history across page reloads.

**Architecture:** Synchronous HTTP call from Odoo portal controller to LLM service
(no RabbitMQ). The LLM service exposes `POST /roleplay` (FastAPI sync endpoint)
distinct from the async `POST /enrich` consumer. `language.scenario.session` stores
`chat_history` as a JSON string in Postgres so conversation context is preserved.

**Work:**

1. `language_portal/models/language_scenario.py` — `language.scenario` model:
   `name`, `description`, `icon`, `target_language`, `initial_prompt`, `is_active`, `sequence`.
   6 scenario records seeded via `data/scenarios.xml` (café, job interview, doctor, hotel, airport, market).
2. `language_portal/models/language_scenario_session.py` — `language.scenario.session`:
   `scenario_id`, `user_id`, `chat_history` (JSON string). UNIQUE(scenario_id, user_id).
   Methods: `get_or_create_session`, `get_history`, `append_message`.
3. `services/llm/main.py` — `POST /roleplay` FastAPI sync endpoint added.
   Accepts `{system_prompt, history, user_message, target_language}`;
   builds chat list; calls `Llama.create_chat_completion`; returns `{"reply":"..."}`.
4. `language_portal/controllers/portal_roleplay.py` — 4 routes:
   `GET /my/roleplay` (grid), `GET /my/roleplay/<id>` (chat), `POST /my/roleplay/<id>/send`
   (JSON-RPC, synchronous LLM call via `requests.post` with 90s timeout),
   `POST /my/roleplay/<id>/reset`.
5. `language_portal/views/portal_roleplay.xml` — glassmorphism grid + dark chat UI.
6. Security, menus, manifest updates.

**Synchronous LLM call pattern (replicate this for future sync AI features):**

```python
import requests as _requests  # NOT urllib.request — fails in Odoo worker context
import json as _json

resp = _requests.post(f"{LLM_SVC}/roleplay", json={...}, timeout=90)
resp.raise_for_status()
raw = resp.content.decode("utf-8", errors="replace")  # NOT resp.json() — content-type agnostic
data = _json.loads(raw)
reply = str(data.get("reply") or "").strip()
```

**Verification:**
```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http

curl http://localhost:5433/my/roleplay           # → 200 (logged-in session required)

# LLM service health (model must be ready)
curl http://localhost:8002/health
# → {"llm_ready":true,"consumer_alive":true}

# Test /roleplay endpoint directly
curl -X POST http://localhost:8002/roleplay \
  -H "Content-Type: application/json" \
  -d '{"system_prompt":"You are a café waiter.","history":[],"user_message":"Hello","target_language":"en"}'
# → {"reply":"Welcome! What can I get for you today?"}
```

---

## M18 — Grammar Pro — Cloze Tests

**Goal:** Users can practice grammar with fill-in-the-blank exercises. 110 exercises
covering EN (A1–B2) and Greek (A1–A2). Multiple-choice buttons, instant colour-coded
feedback, CEFR filters, and XP award on completion.

**Work:**

1. `language_portal/data/cloze_exercises.py` — static Python data file with
   `CLOZE_EXERCISES`, `CATEGORIES`, `LEVELS`, `LANGUAGES`. Loaded via
   `importlib.util.spec_from_file_location` (avoids Odoo module system import).
   Each exercise: `{language, category, level, sentence, answer, choices[4], hint}`.
2. `language_portal/controllers/portal_grammar_practice.py` — `GrammarPracticePortal`:
   - `GET /my/grammar-practice` — filters pool by lang/category/level, samples 10,
     shuffles choices (build `shuffled = []` list; do NOT reassign loop variable `ex`).
   - `POST /my/grammar-practice/score` (JSON-RPC) — 5 XP per correct answer;
     writes to `language.xp.log` (registry guard) + updates `language.user.profile.xp_total`.
3. `language_portal/views/portal_grammar_practice.xml` — dark glassmorphism UI:
   filter bar with language/category/level selects, exercise cards with `data-answer`
   attribute, multiple-choice buttons, inline JS for green/red feedback, score summary
   with XP badge (`lx-xp-badge`).
4. `language_portal/data/website_menus.xml` — "Grammar Pro" navbar entry (sequence=25).
5. `__manifest__.py`, `controllers/__init__.py` updated.

**Shuffle fix — critical pattern:**
```python
# WRONG — reassigns local variable, never updates batch:
for ex in batch:
    ex = dict(ex)  # ← 'ex' rebound locally, original batch unchanged
    random.shuffle(ex["choices"])

# CORRECT:
shuffled = []
for ex in batch:
    ex_copy = dict(ex)
    choices = list(ex_copy["choices"])
    random.shuffle(choices)
    ex_copy["choices"] = choices
    shuffled.append(ex_copy)
batch = shuffled
```

**XP registry guard pattern (use for all cross-module XP writes in language_portal):**
```python
if correct_count > 0 and "language.xp.log" in request.env.registry:
    xp_gained = correct_count * 5
    request.env["language.xp.log"].sudo().create({
        "user_id": request.env.user.id,
        "amount": xp_gained,
        "reason": "grammar_practice",
        "note": f"{correct_count} correct in grammar practice",
    })
```

**Verification:**
```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal,language_learning --stop-after-init --no-http

curl http://localhost:5433/my/grammar-practice   # → 200

# Smoke: 10 exercises rendered, filter changes produce different shuffled sets,
# correct answer turns green, wrong turns red, score summary shows XP badge.
```

---

## Dependency Graph

```
M0 → M1 → M2 → M3
               ↓
               M4
               ↓
          M5   M6
          ↓    ↓
          M7 ←→ M8
          ↓
          M9 → M10 → M11 → M12 → M13
```

M3, M4, M5, M6 can be worked in parallel after M2 is stable.
M7 and M8 can be worked in parallel after M3 (auto-translate after copy depends on M3).
M9 can begin in parallel with M7/M8 (dashboards only need entry data from M2+).
M10 requires M2 (entries), M3 (translations for distractors), M9 (leaderboard UI).
M11 requires M10 (XP system, xp.log model, profile fields).
M12 requires M2 (language.entry + dedup), M3 (auto-translation), M11 (portal navigation patterns).

---

## M15 — AI Translator Tool

**Goal:** A dedicated `/translator` page giving users a Google-Translate-style interface
for instant en↔uk↔el translations backed by the same `deep_translator` engine (Google/MyMemory)
that powers automatic vocabulary translation. Results can be saved directly to the user's
vocabulary in one click.

**Work:**

1. `services/translation/main.py`: add `POST /translate` synchronous FastAPI endpoint —
   calls `_translate()` directly, returns `{"status":"ok","result":"..."}` without RabbitMQ.
2. `language_portal/controllers/portal_translator.py`:
   - `GET /translator` — public page, passes `lang_names`, `lang_flags`, defaults.
   - `POST /translator/translate` — AJAX endpoint; calls translation service HTTP API; returns JSON.
   - `POST /translator/add` — auth-required; creates `language.entry` + `language.translation` (status=completed).
3. `language_portal/views/portal_translator.xml` — premium glassmorphism UI:
   language selectors, swap button, two textareas, Ctrl+Enter shortcut, copy button,
   char counter, "Add to Vocabulary" CTA (hidden for public), tips row.
4. `premium_ui.css` — translator-specific CSS tokens appended.
5. `data/website_menus.xml` — "Translator" navbar entry (sequence=22, always visible).
6. `__manifest__.py` — `portal_translator.xml` added to data list.
7. `controllers/__init__.py` — `portal_translator` import added.

**Verification:**
```bash
# 1. Rebuild translation service (new /translate endpoint)
make up-translation-no-cache
curl -X POST http://localhost:8001/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"apple","source":"en","target":"uk"}'
# → {"status":"ok","result":"яблуко"}

# 2. Update Odoo module
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http

# 3. Route check
curl -o /dev/null -w "%{http_code}" http://localhost:5433/translator
# → 200

# 4. Manual: open /translator in browser, translate "hello" en→uk
#    → "привіт"; click Add to Vocabulary; entry appears in /my/vocabulary

# 5. Regression
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --test-enable --no-http --stop-after-init
```

---

## M18.5 — Header UI Redesign

**Goal:** Replace the flat navbar link list with a category-dropdown system that scales
gracefully as the feature set grows. Full specification in `docs/UI_REDESIGN_HEADER.md`.

**Work:**
1. Define three dropdown groups in `data/website_menus.xml` for each portal module:
   - **Practice** — AI Roleplay, Grammar Pro, Daily Practice, PvP Arena, Sentence Builder (M21)
   - **Library** — Word Library, Useful Words, Grammar Guide, Idioms Hub (M19), Phrasebook (M20)
   - **Tools** — AI Translator, PDF Exports, XP Shop, My Inventory
2. Implement glassmorphism dropdown CSS in `premium_ui.css` (`.lx-nav-dropdown`, `.lx-nav-group`).
3. Ensure mobile hamburger collapse works with Bootstrap's navbar toggler.
4. Remove or re-sequence individual `website.menu` records that become children of groups.
5. Update `branding.xml` navbar logo template to coexist with the new dropdown structure.

**Verification:**
```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal,language_learning,language_pvp \
  --stop-after-init --no-http

# All three groups render in navbar; each expands on hover (desktop) or tap (mobile)
# No orphaned flat links remain; "My Profile" and "My Dashboard" stay top-level
```

---

## M19 — Natural Speech Hub (Idioms & Phrasal Verbs)

**Goal:** Users can browse, search, and save 100+ phrasal verbs (English) and idioms
(Ukrainian, Greek) via interactive expression cards at `/idioms`.

**Architecture:** Static seed data in `language_portal/data/idioms_data.py` (same
`importlib` pattern as `cloze_exercises.py`). Model `language.idiom` in `language_portal`
stores the records with full-text search. No async services needed.

**Data shape per entry:**

| Field | Example |
|---|---|
| `expression` | "kick the bucket" |
| `literal_meaning` | "to kick a bucket" |
| `idiomatic_meaning` | "to die" |
| `example_sentence` | "He kicked the bucket at the age of 90." |
| `language` | `en` |
| `category` | `death_and_life` / `emotions` / `money` / `work` / … |
| `level` | `B1` |
| `origin_note` | optional etymology note |

**Work:**
1. `language_portal/models/language_idiom.py` — `language.idiom` model with full-text
   search field (`_rec_name = 'expression'`). Fields: `expression`, `literal_meaning`,
   `idiomatic_meaning`, `example_sentence`, `language` (Selection en/uk/el), `category`
   (Selection), `level` (Selection A1–C2), `origin_note`.
2. `language_portal/models/__init__.py` — import new model.
3. `language_portal/security/ir.model.access.csv` — Language Users: read-only; Admin: full.
4. `language_portal/data/idioms_data.py` — 100+ entries (40 EN phrasal verbs, 35 UK idioms,
   30 EL idioms). Loaded via post-init hook (same pattern as `seed_vocab.py`).
5. `language_portal/controllers/portal_idioms.py`:
   - `GET /idioms` — grid of cards, filter by language/category/level, paginated 20/page.
   - `GET /idioms/<id>` — full expression detail page.
   - `POST /idioms/<id>/save` — auth=user; creates `language.entry` with
     `source_text=expression`, `created_from='seeded_content'`.
6. `language_portal/views/portal_idioms.xml` — dark glassmorphism card grid with:
   expression badge, literal → idiomatic flip animation, example sentence, "Save to
   My Vocabulary" button.
7. `data/website_menus.xml` — "Idioms Hub" under Library dropdown (M18.5) or as a
   standalone entry (sequence=26) until M18.5 ships.
8. `__manifest__.py`, `controllers/__init__.py` — updated.

**Verification:**
```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http

# Model count
docker exec odoo odoo-bin shell -d lexora -c /etc/odoo/odoo.conf << 'EOF'
count = env['language.idiom'].sudo().search_count([])
print(f"Idioms seeded: {count}")  # expect ≥100
EOF

curl -b cookies.txt http://localhost:5433/idioms  # → 200
# Cards render; filter by language works; "Save to My Vocabulary" creates language.entry
```

---

## M20 — Survival Phrasebook (Tourist Kits)

**Goal:** Users can browse scenario-grouped phrase collections (Hotel, Taxi, Restaurant,
Emergency, Shopping, Airport) in three languages and copy any phrase directly into an AI
Roleplay session at `/phrasebook`.

**Architecture:** Fully static — phrase data in a Python file, no model or DB table needed.
`language_portal/data/phrasebook_data.py` provides `PHRASEBOOK` dict keyed by scenario.
No async services. "Copy to Roleplay" opens a new Roleplay session pre-filled with the
phrase as the first user message.

**Data shape:**

```python
PHRASEBOOK = {
    "hotel": {
        "icon": "🏨",
        "label": "Hotel Check-In",
        "phrases": [
            {
                "en": "I have a reservation under the name ...",
                "uk": "У мене є бронювання на ім'я ...",
                "el": "Έχω κράτηση στο όνομα ...",
                "tags": ["check-in", "beginner"],
            },
            ...
        ],
    },
    ...  # taxi, restaurant, emergency, shopping, airport
}
```

**Work:**
1. `language_portal/data/phrasebook_data.py` — 6 scenarios × ~15 phrases = ~90 entries,
   all three languages side-by-side.
2. `language_portal/controllers/portal_phrasebook.py`:
   - `GET /phrasebook` — scenario grid (6 cards). Loaded via `importlib` pattern.
   - `GET /phrasebook/<scenario>` — phrase list for one scenario, language tabs.
   - `POST /phrasebook/copy-to-roleplay` — auth=user; redirects to
     `/my/roleplay/<scenario_id>` with `?prefill=<phrase_url_encoded>`. The Roleplay
     portal controller already accepts a `prefill` query param and injects it as the
     first user message.
3. `language_portal/views/portal_phrasebook.xml` — scenario grid + phrase list with:
   language tab switcher (EN / UK / EL), copy-to-clipboard button per phrase,
   "Practice in Roleplay" CTA linking to the most relevant scenario (e.g., Hotel
   phrases → Hotel Check-In roleplay scenario).
4. `data/website_menus.xml` — "Phrasebook" under Library dropdown (sequence=27).
5. `__manifest__.py`, `controllers/__init__.py` — updated.

**Note:** `POST /my/roleplay/<id>/send` already supports arbitrary first messages.
The `prefill` integration requires a one-line addition to `portal_roleplay.py`'s
`GET /my/roleplay/<id>` route: read `kw.get('prefill', '')` and pass it to the
template; JS auto-submits it as the first user turn.

**Verification:**
```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http

curl -b cookies.txt http://localhost:5433/phrasebook           # → 200
curl -b cookies.txt http://localhost:5433/phrasebook/hotel     # → 200
# Language tabs switch correctly; "Practice in Roleplay" redirects to correct scenario
# "Copy to Roleplay" opens roleplay with phrase pre-filled in chat input
```

---

## M21 — Sentence Builder (Syntax Master)

**Goal:** A new game mode at `/my/sentence-builder` where users reconstruct a scrambled
sentence word-by-word. Reuses the M18 `cloze_exercises.py` dataset (entries with longer
`sentence` fields). Awards XP on completion. No new data files or async services.

**Mechanics:**

- A sentence is split into individual words (tokens), shuffled, and displayed as
  draggable/clickable tiles.
- User clicks tiles in order to build the sentence in an answer tray.
- On "Check": correct order turns green; wrong order shows the correct sentence.
- Score = number of sentences built correctly out of 5 (one session).
- XP: 10 XP per correct sentence (same `language.xp.log` + registry guard pattern as M18).

**Tokenisation rule:** Split on whitespace only; preserve punctuation attached to words
(e.g., "day." stays as one token). The answer is compared after joining tokens with spaces
and stripping trailing punctuation from the joined string (same normalise logic as M18's
`answer.trim()`).

**Work:**
1. `language_portal/controllers/portal_sentence_builder.py`:
   - `GET /my/sentence-builder` — filters M18 exercises with `level` and `language` params;
     picks 5 sentences with ≥5 words; shuffles tokens per sentence; renders template.
   - `POST /my/sentence-builder/score` (JSON-RPC, auth=user) — awards 10 XP per correct
     sentence via `language.xp.log` (registry guard identical to M18).
2. `language_portal/views/portal_sentence_builder.xml` — dark glassmorphism UI:
   - Token tiles: `.lx-token-tile` pill buttons in a scramble tray.
   - Answer tray: `.lx-answer-tray` — click a tile to move it here; click in tray to
     move back. No drag-and-drop library dependency (pure click-to-move JS, ~50 lines).
   - "Check" button reveals green/red feedback per sentence; "Next" advances to the
     next sentence.
   - Score summary (same `#lx-score-summary` + XP badge pattern as Grammar Pro).
3. `data/website_menus.xml` — "Sentence Builder" under Practice dropdown (sequence=24).
4. `__manifest__.py`, `controllers/__init__.py` — updated.

**Reuse pattern (copy from M18, not re-invent):**

```python
# Controller: load exercises via importlib (identical to grammar practice)
_EXERCISES_PATH = os.path.join(os.path.dirname(__file__), "../data/cloze_exercises.py")

def _load_exercises():
    spec = importlib.util.spec_from_file_location("cloze_exercises", _EXERCISES_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CLOZE_EXERCISES  # reuse existing dataset, filter for sentence length

# XP award: identical registry guard and xp.log write as grammar_practice_score()
```

**Verification:**
```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http

curl -b cookies.txt http://localhost:5433/my/sentence-builder  # → 200
# 5 scrambled sentences render; tiles are clickable; answer tray fills correctly;
# "Check" shows green/red; XP badge appears on final score summary.
```

---

## Dependency Graph (updated)

```
M0 → M1 → M2 → M3
               ↓
               M4 → M4b → M4c
               ↓
          M5   M6
          ↓    ↓
          M7 ←→ M8
          ↓
          M9 → M10 → M11 → M12 → M13 → M14 → M15 → M16 → M17 → M18
                                                                    ↓
                                                              M18.5 (Header)
                                                                    ↓
                                                  M19 ←──────── parallel ──────→ M20
                                                                    ↓
                                                                   M21
```

M19, M20, M21 can be developed in parallel after M18 is stable.
M18.5 (Header) is a pure UI refactor — safe to interleave with any of M19–M21.
M21 has a hard dependency on M18's `cloze_exercises.py` dataset.
M22–M25 form the **Browser Ecosystem** track, parallel to the portal track.
M23 depends on M22 (extension scaffold). M24 and M25 each depend on M22.

---

## M22 — Browser Extension: Scaffold & Odoo API

**Goal:** A working Chrome Extension (Manifest V3) that can authenticate against a
running Lexora instance and add words to the user's vocabulary without leaving the
current browser tab.

**Architecture:**

```
Chrome Extension popup
    ↓ fetch POST (same-origin session cookie)
Odoo: POST /lexora_api/add_word  (auth='user', JSON)
    ↓
language.entry.create()  ← dedup-safe (existing normalize + UNIQUE constraint)
    ↓
translation auto-queued (same as manual entry save in M3)
    ↓
{"status":"ok","entry_id":N,"duplicate":false}
```

**Work:**

1. `extension/manifest.json` — MV3 manifest: `name`, `version`, `manifest_version:3`,
   `action` (popup), `permissions` (`storage`, `activeTab`, `contextMenus`),
   `host_permissions` (user-configurable Lexora URL), `content_scripts` entry for `content.js`.
2. `extension/popup.html` — glassmorphism popup UI: Lexora logo, word input, language
   select (en/uk/el), optional translation field, optional context input, Submit button,
   status banner (success / error / not-logged-in).
3. `extension/popup.js` — reads `lexora_url` from `chrome.storage.sync`; POSTs to
   `/lexora_api/add_word` with credentials; handles 200 (show entry ID), redirect-to-login
   (show "Please log in to Lexora first"), and network errors.
4. `extension/content.js` — stub for M23; currently just logs "Lexora content script loaded".
5. `extension/background.js` — stub service worker for M23 context menu registration.
6. `extension/options.html` + `extension/options.js` — single text field for Lexora base URL
   (default `http://localhost:5433`); saved to `chrome.storage.sync`.
7. `extension/icons/` — 16×16, 48×48, 128×128 placeholder PNG icons (simple "L" on dark gradient).
8. `language_portal/controllers/portal_api.py`:
   - `POST /lexora_api/add_word` — `auth='user'`, `type='json'`, `csrf=False` (extension
     cannot get a CSRF token; we rely on `SameSite` cookie + `auth='user'` session guard instead).
   - Validates `word` (required, ≤500 chars). `translation`, `context_sentence`, `source_url`
     are optional.
   - Calls `env['language.entry'].sudo(env.user).create(...)` — dedup raises `ValidationError`,
     caught and returned as `{"status":"duplicate","entry_id":existing_id}`.
   - If `translation` is provided: creates `language.translation` directly with
     `status='completed'` (bypasses async queue for user-supplied translations).
   - Always enqueues RabbitMQ translation jobs for the user's remaining learning languages.
   - Returns `{"status":"ok","entry_id":N,"duplicate":false}`.
9. `language_portal/controllers/__init__.py` — import `portal_api`.
10. `language_portal/__manifest__.py` — no data change needed (controller auto-loaded).

**CORS note:** Browser extensions running `fetch` from an `moz-extension://` or
`chrome-extension://` context are treated as cross-origin by Odoo's default CORS policy.
Add `Access-Control-Allow-Origin: *` response header only on `/lexora_api/*` routes, plus
`Access-Control-Allow-Headers: Content-Type` and a preflight `OPTIONS` handler.

**Verification:**

```bash
# 1. Update language_portal
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http

# 2. Test endpoint with curl (simulate extension call, requires valid session cookie)
curl -X POST http://localhost:5433/lexora_api/add_word \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=<your_session>" \
  -d '{"word":"ephemeral","source_language":"en","context_sentence":"The ephemeral nature of clouds."}'
# → {"status":"ok","entry_id":N,"duplicate":false}

# 3. Duplicate detection
# → {"status":"duplicate","entry_id":N}

# 4. Load extension in Chrome: chrome://extensions → Load unpacked → select extension/
# 5. Open Options, set URL to http://localhost:5433
# 6. Navigate to any page, click the extension icon, type a word, click Add
# 7. Verify entry appears at http://localhost:5433/my/vocabulary
```

---

## M23 — Browser Extension: Contextual Capture & Smart Selection

**Goal:** Right-clicking selected text on any page shows "Add to Lexora" in the context
menu. The surrounding sentence is automatically captured as `context_sentence`.

**Work:**

1. `extension/background.js` — `chrome.runtime.onInstalled` creates a context menu item
   (`id: "add-to-lexora"`, contexts: `["selection"]`). `chrome.contextMenus.onClicked`
   listener calls `chrome.tabs.sendMessage` to the active tab's content script.
2. `extension/content.js` — listens for `{action:"capture"}` message; finds the surrounding
   sentence by walking the DOM text node containing the selection and splitting on `.!?`
   boundaries. Sends `{word: selectedText, context_sentence: surrounding}` back to background,
   which calls the Odoo API directly via `fetch` (background scripts can make cross-origin
   requests without CORS restrictions).
3. `extension/popup.js` — pre-fills the word input when the popup is opened immediately
   after a context-menu action (passes data via `chrome.storage.session`).

**Verification:**

```bash
# 1. Reload extension after manifest change
# 2. Select "ephemeral" on any webpage → right-click → "Add to Lexora"
# 3. Verify entry created with context_sentence populated
# 4. Open popup immediately → word field pre-filled from context menu selection
```

---

## M24 — Browser Extension: Media & Subtitles Integration

**Goal:** On YouTube and Netflix, clicking a word in the subtitle track opens a
mini-overlay inside the page with the word's translation/definition and an "Add to List"
button. The source link includes a timestamp.

**Architecture:**

```
YouTube/Netflix page
    content.js injects MutationObserver on subtitle DOM
    → subtitle text node changed → wrap each word in <span class="lx-word">
    → user clicks span → overlay rendered adjacent to span
    overlay: word | fetched definition (GET /lexora_api/define?word=X&lang=Y)
             "Add to List" button → POST /lexora_api/add_word with source_url=<tab_url+timestamp>
```

**Work:**

1. `extension/content.js` — YouTube/Netflix URL detection; `MutationObserver` watching
   `.ytp-caption-segment` (YouTube) and `[data-uia="player-timedtext-text-container"]`
   (Netflix). Each text node split into clickable `<span class="lx-word">` elements.
2. `extension/overlay.js` + `extension/overlay.css` — floating glassmorphism card
   positioned at the clicked word; shows definition from `/lexora_api/define` if available
   (falls back to translation service result); "Add to List" button.
3. `language_portal/controllers/portal_api.py` — add `GET /lexora_api/define`:
   looks up `language.translation` records for the given word and returns the best match;
   falls back to empty result (extension shows "No definition yet — save to enrich").
4. `extension/manifest.json` — add `https://www.youtube.com/*` and `https://www.netflix.com/*`
   to `host_permissions` and `content_scripts` matches.

**Verification:**

```bash
# 1. Open YouTube with subtitles enabled
# 2. Click a subtitle word → overlay appears with definition (or "save to enrich" prompt)
# 3. Click "Add to List" → entry created with source_url containing timestamp
# 4. Verify entry at /my/vocabulary has source_url set
```

---

## M25 — Browser Extension: Mini-Practice (New Tab)

**Goal:** Optional New Tab override showing one Idiom card (M19 data) or one Sentence
Builder exercise (M21 data) each time a new tab is opened. Extension popup also offers
"Quick Explain" via the `/enrich` or `/roleplay` endpoint.

**Work:**

1. `extension/newtab.html` + `extension/newtab.js` — fetches one random idiom from
   `GET /lexora_api/daily_card` (new endpoint) and renders a glassmorphism flip card.
   Falls back to a Sentence Builder exercise if no idiom is available.
2. `language_portal/controllers/portal_api.py` — `GET /lexora_api/daily_card`:
   returns a random published `language.idiom` record as JSON; or a random sentence
   exercise from the cloze dataset.
3. `extension/manifest.json` — add `"chrome_url_overrides": {"newtab": "newtab.html"}`;
   add a toggle in Options to enable/disable the override.
4. `extension/popup.js` — "Quick Explain" button sends the currently selected text on
   the active tab to `POST /lexora_api/quick_explain`, which proxies to the LLM service's
   `/enrich` endpoint and returns synonyms + explanation; rendered inline in the popup.
5. `language_portal/controllers/portal_api.py` — `POST /lexora_api/quick_explain`:
   looks up or creates a `language.enrichment` job; if already completed, returns cached
   result immediately; otherwise triggers the async job and returns `{"status":"pending"}`.

**Verification:**

```bash
# 1. Enable New Tab override in extension Options
# 2. Open new tab → idiom card renders with flip animation
# 3. Flip card → idiomatic meaning revealed
# 4. Select text on any page → open extension popup → click "Quick Explain"
#    → synonyms and explanation appear within the popup
```

---

## Dependency Graph (updated)

```
M0 → M1 → M2 → M3
               ↓
               M4 → M4b → M4c
               ↓
          M5   M6
          ↓    ↓
          M7 ←→ M8
          ↓
          M9 → M10 → M11 → M12 → M13 → M14 → M15 → M16 → M17 → M18
                                                                    ↓
                                                              M18.5 (Header)
                                                                    ↓
                                                  M19 ←──────── parallel ──────→ M20
                                                                    ↓
                                                                   M21
                                                                    ↓
                                            M22 (Extension scaffold + Odoo API)
                                                 ↓              ↓           ↓
                                               M23          M24           M25
                                          (Contextual)   (Subtitles)  (New Tab)
```

M22 is the foundation for M23–M25; all three extension milestones can be developed
in parallel once M22's extension scaffold and Odoo API are stable.
M24 has no dependency on M19–M21 but benefits from M19 idiom data for M25.
M25 requires M19 (`language.idiom` model) and M21 (`cloze_exercises.py` dataset).

---

## M26 — AI Helpdesk: CPU-Only RAG Auto-Reply *(Postponed)*

**Status:** ⏸ Postponed — removed from the active stack on 2026-05-02.

**Reason:** The RAG pipeline (pgvector + fastembed ONNX + llama-cpp Qwen2.5-1.5B
Q4_K_M) requires ~1.5–2.0 GiB of additional resident RAM on top of the already
fully-loaded M25 stack (Odoo × 4 workers + Postgres + RabbitMQ + Redis + 4 FastAPI
services). On the 8 GiB KVM host this leaves under 0.5 GiB headroom, causing OOM
kills under normal portal traffic. The feature is architecturally complete but
operationally unsafe on current infrastructure.

**Resumption criteria:** Upgrade the server to ≥16 GiB RAM *or* migrate Odoo to a
dedicated VM so the LLM service has ≥4 GiB reserved.

**What was built (preserved in git history on `m26_ai_helpdesk`):**
- `services/ai_mentor/` — FastAPI RAG service (pgvector + fastembed + llama-cpp)
- `docker_compose/ai_mentor/` — Dockerfile + compose file
- `src/addons/lexora_helpdesk/` — self-contained Odoo addon with `lexora.ticket`
  model, OdooBot auto-reply, portal ticket history at `/my/tickets`

**To re-enable:** checkout the `m26_ai_helpdesk` branch, revert the postgres image
to `pgvector/pgvector:pg15`, restore the Makefile ai_mentor targets, run
`make up-ai-mentor-no-cache`, and init the addon via
`docker exec odoo odoo ... --init lexora_helpdesk --stop-after-init`.

---

## M27 — Browser Extension: Review in the Wild

**Goal:** Turn any webpage into a passive review session. Known vocabulary words are
highlighted with a subtle underline; hovering reveals an SRS-aware tooltip ("You
learned this 3 days ago — do you remember the translation?") with a one-click Reveal
button showing the stored translation.

**Architecture:**

```
Content script loads word list
    ← chrome.storage.local cache (TTL 15 min)
    ← GET /lexora_api/get_learned_words (on cache miss)

DOM scan: TreeWalker over all Text nodes
    → split on word boundaries
    → match against normalized word set (Map lookup, O(1) per word)
    → wrap match in <span class="lx-known-word" data-entry-id="..." data-days-ago="...">

Hover on .lx-known-word
    → show .lx-review-tooltip (positioned via getBoundingClientRect)
    → "Reveal" button fetches best_translation from cached entry data
    → no additional network call needed
```

**New Odoo API endpoint (`GET /lexora_api/get_learned_words`):**

Response shape:
```json
{
  "status": "ok",
  "words": [
    {
      "id": 42,
      "word": "ephemeral",
      "normalized": "ephemeral",
      "lang": "en",
      "translations": {"uk": "короткочасний", "el": "εφήμερος"},
      "srs_state": "review",
      "days_ago": 3
    }
  ],
  "generated_at": 1746300000
}
```

- Capped at 500 active entries per user (active SRS cards ordered by most-recently reviewed).
- `translations`: dict of `{lang_code: translated_text}` for all completed translations; tooltip renders all simultaneously (🇺🇦 UA · 🇬🇷 EL rows).
- `days_ago`: computed from `language.review.last_review_date`; `None` if card never reviewed.
- `srs_state`: `new` / `learning` / `review` — drives tooltip badge colour (indigo/green/amber underline).
- `generated_at`: Unix timestamp for cache TTL computation in the extension.

**Extension content script (`extension/content.js`) additions:**

```javascript
// Cache management
const CACHE_KEY = 'lx_word_cache';
const CACHE_TTL_MS = 15 * 60 * 1000;  // 15 minutes

async function _getWordList() {
    const { lx_word_cache: cached } = await chrome.storage.local.get(CACHE_KEY);
    if (cached && (Date.now() - cached.generated_at * 1000) < CACHE_TTL_MS) {
        return cached.words;
    }
    const resp = await _bgFetch('GET', '/lexora_api/get_learned_words');
    if (resp && resp.status === 'ok') {
        await chrome.storage.local.set({ [CACHE_KEY]: resp });
        return resp.words;
    }
    return [];
}

// DOM highlighter — O(n) single pass via TreeWalker
function _highlightPage(wordMap) {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
        acceptNode: n => {
            const tag = n.parentElement?.tagName;
            if (['SCRIPT','STYLE','TEXTAREA','INPUT','CODE','PRE'].includes(tag)) {
                return NodeFilter.FILTER_REJECT;
            }
            return NodeFilter.FILTER_ACCEPT;
        }
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => _wrapMatchesInNode(node, wordMap));
}
```

**Tooltip CSS:** `.lx-known-word` gets `border-bottom: 2px dotted rgba(99,102,241,0.6)` (indigo,
subtle); colour varies by SRS state (indigo=review, green=learning, amber=new). Tooltip is a
`position:fixed` glassmorphism card using the same design language as the Quick Look overlay.
CSS is embedded as `_REVIEW_CSS` in `content.js` — no separate `.css` file.

**Work:**
1. `language_portal/controllers/portal_api.py` — `GET /lexora_api/get_learned_words` endpoint.
   Joins `language.entry` ↔ `language.review` ↔ `language.translation`. Returns ≤500 words
   ordered by `last_review_date desc nulls last`. Returns `translations: {uk, el}` dict (not a
   single `best_translation` string) so the tooltip can show all languages simultaneously.
2. `extension/content.js` — `_getWordList()` cache layer; `_highlightPage(wordMap)` DOM walker;
   `_wrapMatchesInNode(node, wordMap)` stores `data-trans-uk` / `data-trans-el` attributes;
   `_showReviewTooltip(entry, anchorEl)` renders 🇺🇦/🇬🇷 rows; `_hideReviewTooltip()`.
   Invalidate `lx_word_cache` after `lexora-add-word-overlay` success.
3. `_REVIEW_CSS` string constant in `content.js` (injected via `_ensureReviewStyles()`):
   `.lx-known-word` underline keyed by SRS state (indigo=review, green=learning, amber=new);
   `#lx-review-tooltip` glassmorphism card with opacity fade transition.
   Note: no `extension/overlay.css` file — the extension uses embedded CSS strings in JS.
4. `extension/background.js` — add `lexora-get-learned-words` message handler (GET proxy).
5. `extension/manifest.json` — no changes needed (content.js already injected on all pages).

**Performance contract:**
- `_highlightPage` is called once on `document.idle` via `requestIdleCallback`.
- Re-highlighting on SPA navigation: `MutationObserver` on `document.body` with
  `subtree:true, childList:true`; debounced 500 ms to avoid thrashing on React/Vue apps.
- Word matching uses a `Map<normalized_word, entry>` — O(1) lookup per token.
- Known sites that inject huge DOMs (e.g. Google Docs) are excluded via a denylist in options.

**Verification:**
```bash
# 1. Update language_portal (new endpoint)
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http

# 2. Test endpoint
curl -H "X-Lexora-Session-Id: <sid>" \
  http://localhost:5433/lexora_api/get_learned_words
# → {"status":"ok","words":[...],"generated_at":...}

# 3. Verify SRS data included
# Each word entry should contain srs_state and days_ago when language.review installed

# 4. Load extension in Chrome; navigate to any English-language article
# → known words underlined in indigo; hover shows tooltip with translation reveal
```

---

## M28 — Browser Extension: One-Click Grammar Explainer

**Goal:** From the existing Quick Look overlay (M24 content script) and subtitle overlay
(M24 YouTube), a single "Explain Grammar" button sends the selected phrase to the local
Qwen 1.5B model, which returns a 2-sentence linguistic explanation. Result renders inside
the overlay with no new tabs or page navigations.

**Architecture:**

```
User selects text → Quick Look overlay renders (existing M24 flow)
    → "Explain Grammar" button clicked
    → content.js sends {action:"lexora-explain-grammar", phrase, lang} to background
    → background.js POSTs to /lexora_api/explain_grammar (Odoo proxy)
    → Odoo controller calls requests.post("http://llm-service:8000/explain-grammar", timeout=60)
    → LLM service: Qwen 1.5B inference, ~10–40 s on E5-2680v2
    → {"status":"ok","explanation":"..."}
    → overlay renders explanation in .lx-grammar-block (scrollable, max-height 200px)
```

**LLM service (`services/llm/main.py`) new endpoint:**

```python
class GrammarExplainRequest(BaseModel):
    phrase: str
    language: str = "en"

@app.post("/explain-grammar")
def explain_grammar_endpoint(req: GrammarExplainRequest):
    if _llm is None:
        return {"status": "unavailable", "explanation": "LLM not ready — try again in 30s."}
    _SYSTEM = (
        "You are a linguistics expert. Explain the grammar of the given phrase in "
        "exactly 2 sentences. Focus on: what grammatical rule applies, and why the "
        "phrase is structured this way. Be precise and educational. "
        "Reply in the same language as the phrase."
    )
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user",   "content": f'Explain the grammar of: "{req.phrase}"'},
    ]
    try:
        result = _llm.create_chat_completion(
            messages=messages,
            max_tokens=150,
            temperature=0.3,
            repeat_penalty=1.1,
        )
        explanation = result['choices'][0]['message']['content'].strip()
        return {"status": "ok", "explanation": explanation}
    except Exception as exc:
        _logger.error("explain-grammar failed: %s", exc)
        return {"status": "error", "explanation": ""}
```

**Prompt engineering notes:**
- `max_tokens=150` enforces the 2-sentence contract at the generation level.
- `temperature=0.3` keeps output factual; higher values cause linguistic hallucination.
- `repeat_penalty=1.1` prevents the model from repeating the input phrase verbatim.
- System prompt explicitly says "same language as the phrase" — the model uses this
  for Greek/Ukrainian input (though quality is lower, consistent with SPEC §4.4).

**Odoo proxy (`portal_api.py`) new endpoint:**

```python
POST /lexora_api/explain_grammar
Body: {"phrase": "...", "language": "en"}
Response: {"status": "ok", "explanation": "..."}
          {"status": "unavailable", "message": "LLM not ready"}
          {"status": "error", "message": "..."}
```

- Auth required (session check via `_require_session()`).
- `phrase` capped at 500 chars. Empty → 400.
- `requests.post(LLM_SVC/explain-grammar, timeout=60)` — same pattern as roleplay proxy.
- On timeout or connection error → `{"status":"unavailable","explanation":"LLM timed out"}`.

**Extension UI changes:**

`extension/content.js` Quick Look overlay additions:
```javascript
// Add to _renderQlOverlay() after the translations block:
const grammarBtn = shadow.querySelector('#lx-explain-grammar');
if (grammarBtn) {
    grammarBtn.addEventListener('click', async () => {
        grammarBtn.disabled = true;
        grammarBtn.textContent = 'Explaining…';
        const result = await _bgFetch('POST', '/lexora_api/explain_grammar',
            { phrase: _currentWord, language: _currentLang });
        const block = shadow.querySelector('#lx-grammar-block');
        if (block) {
            block.textContent = result?.explanation || 'Could not generate explanation.';
            block.classList.remove('d-none');
        }
        grammarBtn.textContent = 'Explain Grammar';
        grammarBtn.disabled = false;
    });
}
```

`extension/background.js` additions:
- `lexora-explain-grammar` message handler: POST `/lexora_api/explain_grammar`.

**Work:**
1. `services/llm/main.py` — `POST /explain-grammar` FastAPI sync endpoint (see spec above).
   Rebuild image: `make up-llm-no-cache`.
2. `language_portal/controllers/portal_api.py` — `POST /lexora_api/explain_grammar` proxy endpoint.
   Update module: `--update language_portal --stop-after-init --no-http`.
   Selection length cap raised to 1000 chars (`_MAX_WORD_LEN`) for sentence-length phrase support.
3. `extension/content.js` — "Explain Grammar" button in `_renderQlOverlay()` HTML string;
   click handler with 65s timeout guard; `#lx-ql-grammar` scrollable block.
   `_QL_MAX_LEN` raised to 1000 chars to allow sentence-length selections for grammar queries.
4. `extension/overlay.js` — same "Explain Grammar" button + `#lx-yt-grammar` block in
   YouTube subtitle overlay; same `_sendMessage` + timeout pattern.
5. `extension/background.js` — `lexora-explain-grammar` fetch handler.
6. CSS embedded as string constants (no separate `.css` file — consistent with extension pattern).
   `.lx-ql-explain-btn` + `.lx-ql-grammar-block` appended to `_QL_CSS` in `content.js`.
   `.lx-yt-explain-btn` + `.lx-yt-grammar-block` appended to `_OVERLAY_CSS` in `overlay.js`.
   Both overlays use a flex-column sandwich layout (`header / scroll-body / footer`) with
   `!important` on all structural flex/overflow properties to survive YouTube's stylesheet.
   Both overlays are **draggable** by their header bars: `_makeQlDraggable(shadow)` for the
   Shadow DOM Quick Look card; `_makeDraggable(overlayEl)` for the YouTube page overlay
   (converts `bottom/transform` → `top/left` on first drag). Viewport-clamped repositioning.

**Latency UX contract:**
- Button text changes to "Explaining…" immediately on click.
- Overlay stays open (user can read translations while waiting).
- No spinner animation — text feedback is sufficient given expected 10–40 s latency.
- On timeout (>60 s): show "LLM timed out — try again" in the grammar block.

**Verification:**
```bash
# 1. Rebuild LLM service with new endpoint
make up-llm-no-cache
curl -X POST http://localhost:8002/explain-grammar \
  -H "Content-Type: application/json" \
  -d '{"phrase":"She had been waiting for two hours","language":"en"}'
# → {"status":"ok","explanation":"This sentence uses the past perfect continuous..."}

# 2. Update Odoo
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http

# 3. Test proxy endpoint
curl -X POST http://localhost:5433/lexora_api/explain_grammar \
  -H "Content-Type: application/json" \
  -H "X-Lexora-Session-Id: <sid>" \
  -d '{"phrase":"She had been waiting","language":"en"}'
# → {"status":"ok","explanation":"..."}

# 4. Extension: select any text on any page → Quick Look overlay
#    → "Explain Grammar" button visible
#    → click → "Explaining…" → after ~15s → explanation text renders in overlay
```

---

## Dependency Graph (final)

```
M0 → M1 → M2 → M3
               ↓
               M4 → M4b → M4c
               ↓
          M5   M6
          ↓    ↓
          M7 ←→ M8
          ↓
          M9 → M10 → M11 → M12 → M13 → M14 → M15 → M16 → M17 → M18
                                                                    ↓
                                                              M18.5 (Header)
                                                                    ↓
                                                  M19 ←──────── parallel ──────→ M20
                                                                    ↓
                                                                   M21
                                                                    ↓
                                            M22 (Extension scaffold + Odoo API)
                                                 ↓              ↓           ↓
                                               M23          M24           M25
                                          (Contextual)   (Subtitles)  (New Tab)
                                                 ↓              ↓
                                               M27            M28
                                          (Highlighting)  (Grammar LLM)
                                                    (M26 — AI Helpdesk — postponed ⏸)
```

M28 is the current stable baseline — all extension milestones M22–M28 are complete.
M27 required M22 (API infrastructure) + M9 (SRS review data); M28 required M22 +
M4b (LLM service). M26 is built on `m26_ai_helpdesk` but postponed due to RAM.
M29 (Polish language support) is a horizontal expansion — touches every layer
but introduces no new endpoints or flows.

---

## M29 — Polish Language Support (System-Wide)

**Goal:** Add Polish (`pl` / 🇵🇱) as a first-class supported language alongside the
existing English (`en`), Ukrainian (`uk`), and Greek (`el`). After M29, the user
can pick `pl` as a `source_language`, `target_language`, `practice_language`, or
`native_language` anywhere in the app — vocabulary entries, translations, PvP
duels, posts, idioms, scenarios, and chat all accept Polish equally.

**Scope:** Pure horizontal expansion. No new endpoints, no new models, no new
async services. The only logic change is a single Latin-diacritic regex added to
the extension's `_detectLang()` heuristic so Polish input is routed correctly
when Cyrillic and Greek are absent.

### Architecture decisions

- **Polish flag emoji:** 🇵🇱 (U+1F1F5 U+1F1F1).
- **MyMemory locale:** `pl-PL` (standard ISO; verified via `deep_translator`'s
  `MyMemoryTranslator` language list).
- **Edge TTS voice:** `pl-PL-ZofiaNeural` (female, consistent with the existing
  uk/el female-voice convention). Fallback: `espeak-ng -v pl`.
- **`langdetect`:** ships Polish out of the box (`pl` is in its supported set).
  No extra dependency.
- **Extension `_detectLang()`:** add `if (/[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/.test(text)) return 'pl';`
  **before** the `'en'` fallback. The Cyrillic and Greek branches stay first.
- **Graceful content fallback:** for static datasets that don't yet have Polish
  content (`phrasebook_data.py`, `cloze_exercises.py`), the UI hides the
  language tab/option when no Polish entries exist — no `null` placeholders,
  no broken cards. The data structures accept `pl` keys; populating them is a
  content task that can run in parallel with the schema rollout.

### Step-by-step work plan

**Step 1 — Database & backend (Odoo / Python)**
1. `language_words/data/language_lang.xml`: add `<record id="lang_pl">` block.
2. All `Selection` field definitions across addons (8 sites) — add
   `('pl', 'Polish')`. Files: `language_words/models/language_lang.py`,
   `language_words/models/language_word_of_day.py`, `language_pvp/models/language_duel.py`,
   `language_portal/models/language_post.py`, `language_portal/models/language_idiom.py`,
   `language_portal/models/language_scenario.py`,
   `language_portal/models/language_scenario_session.py`.
3. All controller `LANG_NAMES` dicts and validation tuples (~25 sites across
   `language_words`, `language_translation`, `language_portal`,
   `language_pvp`, `language_chat`, `language_learning`) — add `'pl'`.
4. `language_portal/controllers/portal_translator.py`: add `LANG_FLAGS['pl'] = '🇵🇱'`.
5. QWeb template hardcoded language tuples — add `('pl', 'Polish')` (or
   `('pl', '🇵🇱 Polish')` for the idiom view).
6. `language_anki_jobs`: no changes (the import service is language-agnostic;
   user picks source/target language at upload time, and the dropdown is
   driven by `language.lang`).

**Step 2 — LLM prompts & AI services**
1. `services/translation/main.py`: extend `_MYMEMORY_LOCALES` with `"pl": "pl-PL"`.
   Google's `GoogleTranslator` already accepts bare `pl` — no change there.
2. `services/audio/main.py`: extend `_EDGE_VOICES` with
   `"pl": "pl-PL-ZofiaNeural"` and `_ESPEAK_LANGS` with `"pl": "pl"`.
3. `services/llm/main.py`: extend `LANG_NAMES` with `"pl": "Polish"`. The
   enrichment system prompt is language-agnostic ("Output in the SAME language
   as the input term"), so no prompt rewrite is needed — Polish input
   automatically yields Polish enrichment output.
4. `POST /explain-grammar`: same — system prompt says "Reply in the same
   language as the phrase." No code change.
5. `POST /roleplay`: scenario `target_language` Selection field gets `'pl'`
   (already covered by Step 1). No code change.

**Step 3 — Browser extension**
1. `extension/content.js` `_detectLang()`: add Polish-diacritic branch.
2. `extension/newtab.js`: extend `LANG_FLAGS` and `LANG_NAMES` with `pl`.
3. `extension/content.js` Quick Look overlay: extend the `data-trans-pl`
   attribute write + the `🇵🇱 PL` row render. Hide the row if `data-trans-pl`
   is empty.
4. `extension/overlay.js` YouTube subtitle overlay: same — render the Polish
   translation row when the API returns it.
5. `extension/content.js` highlight tooltip: same `data-trans-pl` + 🇵🇱 row.
6. `language_portal/controllers/portal_api.py` `get_learned_words`: extend the
   `translations` dict to include `pl` when present (already structured as
   `{lang: text}`, so this is automatic once the model has `pl` translations).

**Step 4 — Web UI (portal templates)**
1. Vocabulary entry detail page: existing template iterates
   `entry.translation_ids` — Polish appears automatically once the Selection
   field accepts `pl`.
2. PvP arena: `practice_language` and `native_language` dropdowns — covered
   by the duel model Selection update in Step 1.
3. Translator page (`/translator`): the `LANG_FLAGS` and `LANG_NAMES` updates
   in Step 1 + a one-line addition to the `<select>` tuples in
   `portal_translator.xml`.
4. Anki import upload form: language selector reads `language.lang` records,
   so Polish appears once the seed XML lands in Step 1.
5. Profile page (`/my/profile`): `learning_languages` is a Many2many to
   `language.lang`, so Polish auto-appears as a checkable option.

**Step 5 — Documentation & verification**
1. PLAN.md row → ✅ Complete; status header updated.
2. TASKS.md milestone block archived.
3. README.md: add Polish to "Supported Languages" (or equivalent) section;
   update implementation status table with M29 row.
4. ADR-029: record the `pl-PL-ZofiaNeural` and `pl-PL` MyMemory locale picks.

### Verification

```bash
# Schema migration
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_words,language_translation,language_pvp,\
language_portal,language_chat,language_learning --stop-after-init --no-http

# Confirm pl seeded
docker exec -i postgres psql -U odoo -d lexora -c \
  "SELECT code, name FROM language_lang WHERE code='pl';"
# → pl | Polish

# Translation service: pl in both directions
curl -X POST http://localhost:8001/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"apple","source":"en","target":"pl"}'
# → {"status":"ok","result":"jabłko"}

curl -X POST http://localhost:8001/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"jabłko","source":"pl","target":"en"}'
# → {"status":"ok","result":"apple"}

# Audio service: pl TTS via edge-tts
docker exec rabbitmq rabbitmqadmin --username=guest --password=guest \
  publish exchange=amq.default routing_key=audio.generation.requested \
  payload='{"job_id":"m29-pl-tts","event_type":"audio.generation.requested",\
"payload":{"source_text":"dzień dobry","language":"pl","entry_id":1}}' \
  properties='{"content_type":"application/json","delivery_mode":2}'
# audio service log: "edge-tts: voice=pl-PL-ZofiaNeural ... produced N bytes"

# Portal: add entry "jabłko" (pl) → translation auto-queues for the user's
# learning languages → stored translations include en/uk/el/pl as configured

# Extension: navigate to a Polish-language page → known Polish words highlighted
# (assumes the user has Polish vocabulary). Hover → 🇺🇦/🇬🇷/🇵🇱 rows in tooltip.
```

**Acceptance:** Polish entries flow through translation, enrichment, audio, and
PvP without errors. Browser extension shows Polish translations alongside
existing languages. Portal templates render Polish without "null" placeholders
where Polish content is absent (graceful hide).

---

## M30 — AI Speaking Coach & Oral Practice

**Goal:** A new `/my/speaking` portal where users record themselves speaking on a
topic, see their speech transcribed by Faster-Whisper, and receive AI feedback
(grammar corrections, synonym suggestions, and an "improved" version) generated
by the local Qwen2.5-1.5B model.

**Architecture:** Two new sync HTTP endpoints on the existing FastAPI services
(no new container, no new RabbitMQ queue). Recording → transcription → analysis
is all synchronous so the user sees results within ~10–30 seconds of clicking
Stop. Transcript and feedback persist in a new `language.speaking.session`
model so users can review their progress over time.

```
Browser (mic + MediaRecorder)
    │  audio Blob
    ▼
Odoo controller /my/speaking/transcribe
    │  HTTP POST audio bytes
    ▼
audio_service POST /transcribe-sync (NEW)
    │  faster-whisper.transcribe(language=ll)
    ▼
{transcript, language}
    │
    ▼  Odoo creates language.speaking.session row
    │
    ▼  Browser POST /my/speaking/analyze
    │
Odoo controller proxies to LLM
    │
    ▼
llm_service POST /analyze-speech (NEW)
    │  Qwen2.5-1.5B chat completion
    ▼
{corrections, synonyms, improved}
    │
    ▼  Odoo updates the session row, returns to browser
```

### New endpoints

**`POST /generate-topic`** (LLM service) — accepts `{language: "en|uk|el|pl"}`,
returns `{topic: "Tell me about your favorite season."}`. System prompt asks
for one short open-ended conversation starter in the requested language at
B1 difficulty.

**`POST /analyze-speech`** (LLM service) — accepts `{transcript: "...",
language: "en|uk|el|pl", topic: "..."}`, returns `{corrections: [...],
synonyms: [...], improved: "..."}`. Output is enforced JSON via the same
`response_format={"type":"json_object"}` pattern used by `/enrich`. Falls back
to a stub when the model is not loaded.

**`POST /transcribe-sync`** (audio service) — multipart audio upload, returns
`{transcript: "...", duration: 12.3, language: "en"}`. Uses the same
faster-whisper instance already loaded for the async RabbitMQ path; just
adds a sync FastAPI route that bypasses the queue. Cap at 90 s of audio
(soft limit configurable via env).

### New model

`language.speaking.session` (in `language_portal`):

| Field | Type | Notes |
|---|---|---|
| `user_id` | Many2one → res.users | Required, indexed |
| `target_language` | Selection (LANGUAGE_SELECTION) | `en/uk/el/pl` (canonical import) |
| `topic` | Char | The LLM-generated conversation starter |
| `transcript` | Text | Whisper output |
| `duration_seconds` | Float | Set from Whisper response |
| `feedback_corrections` | Text | JSON list of `{wrong, correct, note}` |
| `feedback_synonyms` | Text | JSON list of `{original, suggestion, reason}` |
| `feedback_improved` | Text | The AI's refined version of the user's speech |
| `audio_attachment_id` | Many2one → ir.attachment | Stored audio (private to owner) |
| `status` | Selection (`pending`/`transcribing`/`analyzing`/`completed`/`failed`) | State machine |
| `error_message` | Text | Surfaces failure reason |
| `created_date` / `write_date` | Datetime | Auto |

### Portal routes

| Route | Method | Purpose |
|---|---|---|
| `/my/speaking` | GET | Page: topic input + Record button + last 10 sessions |
| `/my/speaking/topic` | POST (JSON) | Calls LLM `/generate-topic`, returns `{topic}` |
| `/my/speaking/transcribe` | POST (multipart) | Uploads audio + topic, calls audio `/transcribe-sync`, creates `language.speaking.session` (status `analyzing`), returns `{session_id, transcript}` |
| `/my/speaking/analyze` | POST (JSON) | Calls LLM `/analyze-speech` for the given session, persists feedback, returns `{corrections, synonyms, improved}` |
| `/my/speaking/<id>` | GET | Detail page for one session (transcript + feedback) |

### Step-by-step work plan

**Step 1 — Foundation (this commit):**
- Branch `m30_speaking_coach`, PLAN.md + TASKS.md updated.
- `language.speaking.session` model in `language_portal` with all fields,
  state machine, security ACL row, owner-only record rule.
- `portal_speaking.py` controller stub: `/my/speaking` GET renders the page
  with a topic input, Record button, and the last 10 sessions for the user.
- Manifest entry for the new model + view + access CSV.
- `language_portal` updates cleanly.

**Step 2 — LLM endpoints:**
- `services/llm/main.py` adds `POST /generate-topic` and `POST /analyze-speech`
  (both sync, both language-agnostic in the same way `/roleplay` is). System
  prompts kept short to fit Qwen2.5-1.5B's 200-token sweet spot
  (lessons from M18-FIX-09).
- `make up-llm-no-cache`; `/health` still flips `llm_ready:true`.

**Step 3 — Audio sync transcription:**
- `services/audio/main.py` adds `POST /transcribe-sync`. Reuses the loaded
  `faster_whisper.WhisperModel`. Returns `{transcript, duration}`.
- 90 s soft cap (rejects audio longer than that with HTTP 413). Returns
  HTTP 503 if `_whisper_ready=False`.

**Step 4 — Portal POST endpoints + UI:**
- `/my/speaking/topic` (JSON-RPC sync proxy to LLM).
- `/my/speaking/transcribe` (multipart upload → audio service → DB row →
  JSON response).
- `/my/speaking/analyze` (JSON-RPC → LLM → updates DB row).
- Glassmorphism dark UI (consistent with M17 Roleplay): topic card,
  Record/Stop button using browser MediaRecorder, transcription preview,
  feedback panel with three sections (corrections / synonyms / improved).

**Step 5 — Verification + docs:**
- End-to-end smoke for all 4 languages: record "Hello, my name is X" in en,
  confirm transcript + feedback render. Same for uk/el/pl.
- ADR-030 documenting: the sync-over-async decision (no RabbitMQ for the
  speaking flow) and the JSON output contract for `/analyze-speech`.
- README.md row for M30; PLAN.md flips ✅ Complete; TASKS.md archives.

### Verification

```bash
# After Step 1: model + page foundation
docker exec odoo odoo --config /etc/odoo/odoo.conf -d lexora \
  --update language_portal --stop-after-init --no-http
curl -s -o /dev/null -w "/my/speaking %{http_code}\n" \
  http://localhost:5433/my/speaking  # expect 303 (redirect to login) or 200 with cookie

# After Step 2: LLM topic + analysis
curl -X POST http://localhost:8002/generate-topic \
  -H "Content-Type: application/json" \
  -d '{"language":"pl"}'
# → {"topic":"Opisz swoje ulubione miejsce w mieście."}

curl -X POST http://localhost:8002/analyze-speech \
  -H "Content-Type: application/json" \
  -d '{"transcript":"I goes to school yesterday","language":"en"}'
# → {"corrections":[{"wrong":"I goes","correct":"I went","note":"past tense"}], ...}

# After Step 3: audio sync transcription
curl -X POST http://localhost:8004/transcribe-sync \
  -F "audio=@sample.webm" -F "language=en"
# → {"transcript":"...","duration":7.2}

# After Step 4: full E2E from the portal
# Record 10 s of audio → Stop → see transcript appear → see corrections panel
```

**Acceptance:** A user can record speech in any of en/uk/el/pl, see an accurate
transcript within 30 s, and receive grammar/synonym/improved-version feedback
within a further 30 s. The session persists at `/my/speaking/<id>` for review.

---

## M31 — Browser Extension: Lexora Writer (Active Writing Assistant)

**Goal:** Turn the Companion Extension into a proactive writing assistant — like Grammarly, but for the four supported learning languages. While a user is typing in any text field on any website (Reddit comments, Gmail compose, a CMS, an exam practice platform, etc.), Lexora offers a one-click "fix my grammar and polish this" pass powered by Qwen2.5-1.5B and applied directly back into the input.

**Architecture:** Pure synchronous proxy chain (consistent with ADR-030 sync-over-async rule):

```
Browser focuses <textarea> or [contenteditable]
   content.js MutationObserver + focusin listener
   → injects floating "L" FAB anchored to the input
User types text, clicks the FAB
   → content.js reads field value (textarea.value / el.innerText)
   → background.js handler `lexora-writer-check`
   → POST /lexora_api/writer_check (Odoo proxy, auth='user')
       → POST llm_service /analyze-writing (sync, ~15-30 s)
       ← {corrections: [...], improved: "..."}
   ← Glassmorphism popup near the input
User clicks "Apply to text"
   → content.js writes improved_version back to the field
   → dispatches 'input' event so React/Vue/etc. listeners notice the change
```

### New endpoint — LLM service

**`POST /analyze-writing`** — sync FastAPI endpoint following the pattern of `/explain-grammar`, `/analyze-speech`, `/roleplay`:

- Pydantic request: `{ text: str, language: str, context?: str }`. The optional `context` field carries the field's `placeholder` or `aria-label` so the model knows whether the user is writing an email, a tweet, or a forum comment.
- System prompt enforces JSON output with **two top-level keys** (simpler than M30's three — written text is more deliberate, no need for synonym suggestions):
  ```json
  {
    "corrections": [{"wrong": "...", "correct": "...", "note": "..."}],
    "improved":    "..."
  }
  ```
- `response_format={"type":"json_object"}`, `max_tokens=512`, `temperature=0.4`, `repeat_penalty=1.1`.
- Reuses `_parse_enrichment_json` + `_coerce_list` from M30. `parse_error` graceful fallback.
- Stub fallback when `_llm_ready=False`: returns `{corrections: [], improved: <original text>}`.

### New endpoint — Odoo

**`POST /lexora_api/writer_check`** in `language_portal/controllers/portal_api.py`:

- Auth: `_require_session()` (browser-extension session token, same as M22-M28 endpoints).
- Body: `{ text: str, language: str, context?: str }`.
- Caps: `text` length capped at `_MAX_WRITER_TEXT = 4000` chars (matches LLM's effective context window for the 1.5B model).
- Forwards to `POST {LLM_SVC}/analyze-writing` with a 60 s timeout.
- Returns the LLM's payload verbatim plus `status: "ok"` / `"error"` / `"unavailable"`.
- CORS reflection identical to existing `_lexora_api_*` routes (Origin reflected; `Allow-Credentials: true`).

### Extension changes (`extension/`)

**`content.js` — new "writer FAB" subsystem:**

- New constant `_WRITER_FAB_ID = 'lx-writer-fab'`. Floating anchor button styled like the Quick Look "L" icon (Shadow DOM for CSS isolation).
- `_initWriter()` runs once at script load: attaches `focusin` listener on `document` capturing focused `<textarea>` and `[contenteditable="true"]` elements.
- `_isEligibleInput(el)` heuristic — accepts only:
  - `el.tagName === 'TEXTAREA'` (not `<input>` for now), or
  - `el.isContentEditable === true`
  - **Rejects** when any of the following hold (silent skip, no FAB):
    - `el.type === 'password'` / `el.type === 'hidden'`
    - `el.hasAttribute('readonly')` / `el.hasAttribute('disabled')`
    - `el.closest('[role="search"]')` (search bars)
    - `el.closest('.lx-ql-host')` / `el.closest('.lx-yt-card')` (our own overlays — no recursion)
    - `el.getAttribute('aria-label')` matches code-editor patterns (`/code|monaco|cm-editor/i`)
    - The element belongs to a `<form>` whose `name` matches `/login|sign[ -]?in|password/i`.
- `_positionFab(input)` uses `getBoundingClientRect` + `position: fixed` to place the FAB just outside the bottom-right corner of the input. Re-runs on `scroll` / `resize` (debounced 100 ms).
- FAB click handler:
  1. Reads the field value (`input.value` for textarea; `input.innerText` for contenteditable).
  2. Bails out if `text.trim().length < 20` with a tooltip "Write at least 20 chars".
  3. Detects language via the existing `_detectLang(text)` helper from M27 (Cyrillic→uk, Greek→el, Polish-diacritic→pl, else en).
  4. Sends `{action:"lexora-writer-check", text, language, context}` to background.
  5. Renders a glassmorphism popup using a **new template `_renderWriterOverlay`** anchored to the same input. Reuses the M28-12c flexbox-sandwich layout (header / scroll-body / footer with Apply button). Status pill cycles through "Analysing…" → "Done" / "Failed".
- `_applyWriterImproved(input, improved)` — writes the improved text back:
  - For `<textarea>`: `input.value = improved; input.dispatchEvent(new Event('input', {bubbles:true}))` so React-controlled fields update their state.
  - For `[contenteditable]`: `input.innerText = improved; input.dispatchEvent(new Event('input', {bubbles:true}))`.
  - For both: also dispatch `change` and `blur` so frameworks that batch reads still notice.

**`background.js` — new handler:**

- `lexora-writer-check` case wires to `handleWriterCheck({text, language, context})` → POST `/lexora_api/writer_check` (same `getSessionHeader` / `X-Lexora-Session-Id` pattern as the other handlers).
- 60 s timeout (consistent with M28's `lexora-explain-grammar`).

**`manifest.json`:**

- Add `https://*/*` and `http://*/*` to `host_permissions` (already present from M27 review-in-the-wild).
- No new permissions needed — `activeTab` + `scripting` already cover injection.
- Add a small toggle in the existing Options page: "Show writer assistant on text fields" (default ON; persisted in `chrome.storage.sync`). The FAB injection is gated on this flag.

### CSS (extension)

Embedded as `_WRITER_CSS` string in `content.js` (consistent with the M27 `_REVIEW_CSS` / M28 `_QL_CSS` / M24 `_OVERLAY_CSS` patterns — no separate `.css` file in the extension). Key tokens:

- `.lx-writer-fab` — 32 × 32 indigo gradient circle, `z-index: 2147483600` (one less than the Quick Look host so a visible Quick Look always wins).
- `.lx-writer-fab:hover` — scale 1.08, indigo glow.
- `.lx-writer-host` — Shadow DOM host for the popup card.
- `.lx-writer-card` — flexbox sandwich (header / scroll-body / footer with `!important` flex props per M28-12d, draggable per M28-17).
- `.lx-writer-correction` — wrong/correct row, same colour palette as M30 corrections (`text-warning` / `text-success`).

### Verification (from PLAN view — full checklist lives in TASKS.md)

```bash
# After M31 ships
make up-llm-no-cache  # picks up the new endpoint
docker exec odoo odoo -d lexora --update language_portal --stop-after-init --no-http

# 1. Sync endpoint smoke
curl -X POST http://localhost:8002/analyze-writing \
  -H 'Content-Type: application/json' \
  -d '{"text":"I goes to school every days.","language":"en"}'
# → {"status":"ok","corrections":[{"wrong":"I goes","correct":"I go",...}],
#    "improved":"I go to school every day."}

# 2. Odoo proxy smoke (with session cookie)
curl -X POST http://localhost:5433/lexora_api/writer_check \
  -H 'Content-Type: application/json' \
  -H "X-Lexora-Session-Id: <sid>" \
  -d '{"text":"I goes to school every days.","language":"en"}'
# → same payload

# 3. Browser smoke: load extension, open a Reddit comment box, type 30 chars,
# click the L FAB, see the popup, click "Apply to text" — comment box value
# is replaced and React's character counter updates (proves the input event
# fired).
```

### Acceptance

- Floating L FAB appears beside any eligible textarea / contenteditable on any site.
- Click → ~15-30 s later → popup with corrections + improved version.
- "Apply to text" replaces the field value AND triggers framework state updates (verified on a React-based site — Reddit, Gmail compose, or an Odoo backend long-text field).
- Privacy hint in the popup footer: "Text is sent to your Lexora server for analysis."
- 4-language support — the `_detectLang` regex from M27 already routes correctly.

---

## M32 — Browser Extension: Slang & Idiom Explainer

**Goal:** Extend the existing Quick Look (M24) and YouTube subtitle (M24) overlays so they can explain phrases that don't translate literally — idioms, slang, phrasal verbs. The current "Explain Grammar" button (M28) handles the syntactic side; this milestone adds the semantic side. A user who selects "kick the bucket" or "let bygones be bygones" sees a meaningful figurative explanation plus a usage example, not a confused word-for-word translation.

**Architecture:** Same chain as M28 grammar explanation, just a new endpoint and a parallel button. Sync proxy. No new RabbitMQ, no new container.

```
User selects phrase in Quick Look (or YouTube subtitle) overlay
   → clicks "Explain Slang/Idiom" button (NEW, sibling of "Explain Grammar")
   → background.js handler `lexora-explain-slang`
   → POST /lexora_api/explain_slang (Odoo proxy)
       → POST llm_service /explain-slang (sync, ~10-25 s)
       ← {kind, figurative_meaning, literal_meaning, example, confidence}
   ← Renders in a new scrollable block within the overlay sandwich
```

### New endpoint — LLM service

**`POST /explain-slang`** — sync FastAPI endpoint:

- Pydantic request: `{ phrase: str, source_language: str, native_language?: str }`.
- `source_language` is the language of the phrase itself (Cyrillic phrase → `uk`, Polish phrase → `pl`, etc., already inferred client-side via `_detectLang`).
- `native_language` is the language the user wants the *explanation* in. Defaults to `en`. The browser supplies this from `chrome.storage.sync` (added by M22 Options page) or falls back to the user's profile `native_language` field if the proxy can resolve it.
- System prompt instructs the model to:
  1. Decide what kind of phrase this is — `idiom`, `slang`, `phrasal_verb`, `literal`, or `unknown`.
  2. If non-literal: give the *figurative* meaning in `native_language`, plus the literal word-for-word translation (so the user sees both), plus one short natural-usage example.
  3. If literal: say "this phrase translates literally" and just give the translation.
- Output JSON contract (enforced via `response_format={"type":"json_object"}`):
  ```json
  {
    "kind":               "idiom",
    "figurative_meaning": "to die",
    "literal_meaning":    "to kick a bucket",
    "example":            "He kicked the bucket at the age of 90.",
    "confidence":         "high"
  }
  ```
- `confidence` ∈ `{"high","medium","low"}`. The 1.5B model is wobblier on Slavic idioms than English; the UI surfaces low-confidence answers with an italic hint.
- Stub fallback when `_llm_ready=False`: returns `{kind:"unknown", figurative_meaning:"", literal_meaning:phrase, example:"", confidence:"low"}` so the UI doesn't wedge.
- Reuses `_parse_enrichment_json` tolerant parser; defensive `_coerce_list` not needed (no array fields).

### New endpoint — Odoo

**`POST /lexora_api/explain_slang`** in `language_portal/controllers/portal_api.py`:

- Auth: `_require_session()`. CORS reflection identical to `/lexora_api/explain_grammar`.
- Body: `{ phrase: str, source_language: str, native_language?: str }`.
- Cap on `phrase`: reuse the existing `_MAX_WORD_LEN = 1000` constant from M28 (sentence-length selections supported).
- If `native_language` not supplied, look up the caller's `language.user.profile.native_language` and use that; fall back to `en` if the profile is absent or has no native set.
- Forwards to `{LLM_SVC}/explain-slang` with a 60 s timeout (matches the existing grammar-explainer proxy).

### Extension changes (`extension/`)

**`content.js` — Quick Look overlay:**

- In `_renderQlOverlay`, add a second button next to the existing `#lx-ql-explain` (Explain Grammar):
  ```html
  <button id="lx-ql-explain-slang" class="lx-ql-explain-btn">💡 Explain Slang/Idiom</button>
  ```
- Add `#lx-ql-slang-block` `<div>` directly below the existing `#lx-ql-grammar-block` (also `display:none → .lx-visible:display:block`). Same flexbox-sandwich + scroll behaviour as the grammar block (M28-12c).
- Click handler — same shape as `#lx-ql-explain`:
  - Disables the button, sets text to "Looking up…".
  - Sends `{action:"lexora-explain-slang", phrase, source_language, native_language}` to background.
  - Renders the response (`renderSlangBlock(result)`):
    - If `kind === 'literal'`: show "This phrase translates literally — no figurative meaning." plus the literal translation.
    - Otherwise: show figurative meaning (bold, larger), literal meaning (smaller, italic), and the example (quoted, indented).
    - If `confidence === 'low'`: append a small italic note "AI is uncertain — consider checking a dictionary."
- `_QL_CSS` gains `.lx-ql-slang-btn`, `.lx-ql-slang-block` (mirrors `.lx-ql-grammar-block`).

**`overlay.js` — YouTube subtitle overlay:**

- Identical changes — second button next to `#lx-yt-explain`, second block below `#lx-yt-grammar-block`. `_OVERLAY_CSS` gains `.lx-yt-slang-btn` and `.lx-yt-slang-block`. Same flex-sandwich layout (M28-12d `!important` flex props preserved).

**`background.js`:**

- `lexora-explain-slang` case → `handleExplainSlang({phrase, source_language, native_language})` → POST `/lexora_api/explain_slang` (same session-cookie + 60 s timeout pattern as `handleExplainGrammar`).

**Options page (`options.html` / `options.js`):**

- New select: "Explanation language" with options matching the four supported languages (en/uk/el/pl). Default value resolved from the user's profile (best-effort `GET /lexora_api/whoami`); if unavailable, defaults to `en`. Persisted in `chrome.storage.sync` as `lexora_native_language`.
- The slang button click reads this value and includes it in the message to background; background passes it through unchanged.

### Verification

```bash
# 1. LLM endpoint smoke (English idiom)
curl -X POST http://localhost:8002/explain-slang \
  -H 'Content-Type: application/json' \
  -d '{"phrase":"kick the bucket","source_language":"en","native_language":"uk"}'
# → {"status":"ok","kind":"idiom","figurative_meaning":"померти",
#    "literal_meaning":"вдарити по відру","example":"...","confidence":"high"}

# 2. LLM smoke — phrasal verb (English)
curl -X POST http://localhost:8002/explain-slang \
  -d '{"phrase":"give up","source_language":"en","native_language":"en"}'
# → {"kind":"phrasal_verb","figurative_meaning":"to stop trying","example":"..."}

# 3. LLM smoke — Polish idiom
curl -X POST http://localhost:8002/explain-slang \
  -d '{"phrase":"masz węża w kieszeni","source_language":"pl","native_language":"en"}'
# → {"kind":"idiom","figurative_meaning":"to be stingy",...,"confidence":"medium"}

# 4. Odoo proxy: same payloads, with session cookie
# 5. Browser smoke: select an English idiom on a Wikipedia page → Quick Look
#    overlay → click "Explain Slang/Idiom" → block expands with the explanation.
# 6. YouTube smoke: pick a slangy subtitle word → overlay → same button works.
```

### Acceptance

- A new "Explain Slang/Idiom" button appears in both Quick Look and YouTube overlays.
- Clicking on a clear idiom (e.g. "kick the bucket") returns figurative + literal + example in the user's chosen native language within ~25 s.
- For a literal phrase (e.g. "the cat is on the mat"), the response sets `kind: "literal"` and the UI shows a clear "this is literal" hint instead of inventing a figurative reading.
- Low-confidence Slavic idioms surface the "AI is uncertain" hint instead of silently giving a wrong answer.
- Both buttons coexist without breaking the M28 flexbox sandwich layout.

### M32 ↔ M19 relationship

M19 already shipped a curated `language.idiom` table (100+ entries with meanings, examples, level). M32 is **not** trying to replace that — the curated table is high-quality and used in `/idioms` for browsing. Instead M32 covers the long tail: the ad-hoc idiom encountered on a webpage that's not in the seed list. A future M-thirty-something could merge them: the LLM check could first look up the curated table and only fall back to the model when no entry exists.

---

## Combined Branch Plan

Both M31 and M32 ship on a single branch `m31_m32_extension_upgrades` because they touch overlapping files (`content.js`, `background.js`, `portal_api.py`, `services/llm/main.py`). M31 lands first (it's a bigger surface — new FAB subsystem, focusin listener, Apply-to-text logic) and M32 follows once the M31 button-and-overlay scaffolding has been validated in a real browser.

Final commit order:
1. Docs (PLAN + TASKS) — this commit.
2. M31 LLM endpoint + Odoo proxy + extension FAB & popup.
3. M31 user verification + bug-fix commits as needed.
4. M32 LLM endpoint + Odoo proxy + extension button additions.
5. M32 user verification + bug-fix commits as needed.
6. Final docs flip + ADR-031 + ADR-032 (combined or separate per content).

---

## M33 — Webpage Shadowing (Extension Pronunciation Practice)

**Goal:** Bring the M30 `/my/speaking` microphone-and-feedback flow into the browser extension. A user reading an English article on Wikipedia, a Polish news site, or a Greek blog can select a sentence, click "🎤 Practice Pronunciation", hear a perfect Edge TTS rendering, hold-to-record themselves saying the same sentence, and receive a Qwen-generated accuracy score plus per-word annotations (which words they missed, which they mispronounced).

This is the first browser-extension feature that **records audio**. MV3 imposes hard constraints on `getUserMedia` from content scripts — the milestone's primary architectural risk is the mic permission flow, not the AI pipeline.

**Architecture (synchronous, ADR-030/031 rule reapplied — the user is staring at the result so RabbitMQ adds nothing):**

```
User selects sentence on any webpage
   → clicks "🎤 Practice Pronunciation" in Quick Look / YouTube overlay
   → Shadowing block expands inside the overlay

[Stage 1 — Play Original]
   "Play Original" button click
     → POST /lexora_api/shadow_tts (Odoo proxy, auth=session-bridge)
         → POST audio_service /tts-sync (NEW, returns audio/mpeg bytes)
         ← MP3 blob
     ← Streams audio bytes back to the extension
     → <audio> element plays the perfect TTS rendering

[Stage 2 — Hold to Record]
   Hold-to-record button:
     mousedown → background.js spins up a chrome.offscreen document
                  (created lazily on first record; reused thereafter)
                  → offscreen requests getUserMedia ONCE per extension
                  → MediaRecorder starts in the offscreen page
     mouseup   → MediaRecorder.stop() → audio Blob → background → content
                  → POST /lexora_api/shadow_evaluate (multipart)
                       audio + reference_text + language
                       → POST audio_service /transcribe-sync (M30 path)
                            ← {transcript, duration, language}
                       → POST llm_service /evaluate-pronunciation (NEW)
                            ← {score, missed_words, mispronounced_words, feedback}
                  ← Combined JSON
     → Shadowing block renders the score badge + per-word annotation
       overlaid on the reference text (red strike-through for missed
       words, amber underline for mispronounced)
```

### Sub-decision 33a: MV3 microphone strategy — Offscreen Document API

**Problem:** content scripts run in the page's origin (`https://example.com`), so `getUserMedia()` from a content script triggers a permission prompt **per origin**. A user who practises shadowing on Wikipedia, Reddit, and YouTube would see the prompt three times. The recording would also stop the moment the page navigates away.

**Decision:** record audio in a `chrome.offscreen` document hosted at `chrome-extension://<id>/offscreen.html`. The offscreen page lives on the **extension's origin**, so the user grants mic permission **once per extension** (in the Options page workflow) and Chrome remembers it forever. The offscreen doc has no UI; the content script messages it via `chrome.runtime.sendMessage` through the background service worker.

**Lifecycle:**

```
content.js: hold-to-record mousedown
  → bg.js: ensure offscreen exists
      if (!await chrome.offscreen.hasDocument()) {
        await chrome.offscreen.createDocument({
          url: 'offscreen.html',
          reasons: ['USER_MEDIA'],
          justification: 'Record speech for pronunciation practice',
        });
      }
  → bg.js: chrome.runtime.sendMessage({action:'lx-mic-start'})
  → offscreen.js: getUserMedia + MediaRecorder.start()

content.js: hold-to-record mouseup
  → bg.js: chrome.runtime.sendMessage({action:'lx-mic-stop'})
  → offscreen.js: recorder.stop() → blob → base64 → message back
  → bg.js: forward base64 audio to the requesting tab's content.js
  → content.js: decodes base64 → File → FormData → POST shadow_evaluate
```

**Why not a hidden iframe (the older pattern):** iframe-based recording predates `chrome.offscreen` and works on Chrome/Edge but is brittle on Firefox MV3 and on enterprise-locked Chromebooks where iframe injection is blocked. `chrome.offscreen` is the official MV3 recommendation since Chrome 116 and it's the future-proof choice.

**Why not the popup:** popups close when they lose focus. Hold-to-record requires the popup to stay open while the user is speaking; the user's mouse is on the webpage, not the popup, so the popup loses focus immediately.

**Manifest changes:** add `"offscreen"` to `permissions`. No new `host_permissions` (the offscreen doc is on the extension's own origin).

**Permission UX:** the first time the user clicks Hold-to-Record on any tab, the offscreen doc loads and prompts for mic permission via Chrome's standard chrome:// permission UI. Subsequent clicks on any tab reuse the same grant — no re-prompt.

### Sub-decision 33b: Two Odoo proxy endpoints

The orchestration is two distinct flows so neither one waits unnecessarily on the other:

**`POST /lexora_api/shadow_tts`** — fetch reference TTS audio.
- Body: `{text, language}`. `text` capped at 500 chars (typical sentence length); `language` validated against `_ALLOWED_LANGUAGES`.
- Forwards to audio service `POST /tts-sync` (NEW, see 33d).
- Returns `audio/mpeg` bytes directly (Content-Type passed through). **Not** wrapped in JSON — the extension creates a `Blob` from the response and feeds it to an `<audio>` element.
- 30 s timeout (TTS is fast; 30 s is a safety bound).

**`POST /lexora_api/shadow_evaluate`** — orchestrates the two-stage analysis.
- Multipart body: `audio` blob + `reference_text` (str) + `language` (str).
- **Stage 1**: forward `audio` to audio service `POST /transcribe-sync` (M30 endpoint, already exists). 120 s timeout.
- **Stage 2**: send `{reference_text, transcript, language}` to llm service `POST /evaluate-pronunciation` (NEW, see 33c). 60 s timeout.
- Returns combined JSON:
  ```json
  {
    "status": "ok",
    "transcript": "what the user actually said",
    "duration": 4.2,
    "score": 85,
    "missed_words": ["ephemeral"],
    "mispronounced_words": ["pronunciation"],
    "feedback": "Great rhythm overall — focus on the stressed syllable in 'pronunciation'."
  }
  ```
- Total user-perceived latency: ~20-50 s (Whisper ~10-20 s + Qwen ~10-30 s). Same envelope as M30's record-then-analyze pattern.

### Sub-decision 33c: LLM `/evaluate-pronunciation` contract

**Pydantic:**

```python
class EvaluatePronunciationRequest(BaseModel):
    reference_text: str
    transcript: str
    language: str = "en"
```

**System prompt (under 100 words, M18-FIX-09 rule):** instructs the model to compare the two strings word-by-word, score 0-100 (100 = byte-identical, 0 = nothing matched), classify each reference word as `matched`/`missed`/`mispronounced`, and write a one-sentence learning-friendly feedback note in the user's language.

**JSON contract:**

```json
{
  "score":                85,
  "missed_words":         ["ephemeral"],
  "mispronounced_words":  ["pronunciation"],
  "feedback":             "Great rhythm — focus on the stressed syllable in 'pronunciation'."
}
```

- `score` (int, 0-100) — defensively clamped server-side.
- `missed_words` / `mispronounced_words` — `List[str]`, defensively coerced to flat strings (each word stripped, max 30 chars), capped at 20 entries each.
- `feedback` — free text in the requested `language`.

**Few-shot anchor per language** (`_PRONUNCIATION_EXAMPLES` dict keyed by `language`) — closes the M30 lesson reapplied. Each anchor shows a reference + transcript pair with the JSON output filled in the right script.

**Server-side safety net** (M31 lesson reapplied): if the model returns `score=100` AND `missed_words=[]` AND `mispronounced_words=[]` BUT `transcript ≠ reference_text` (whitespace-normalised, lowercase), run a deterministic Python word-diff:

- Tokenise both on whitespace + Unicode word boundaries.
- Reference words not in transcript (substring-tolerant) → `missed_words`.
- Words in transcript that are similar but not identical to a reference word (Levenshtein ≤ 2 or shared prefix length ≥ 3) → `mispronounced_words`.
- Recompute `score` as `100 * matched_count / reference_word_count`.

This guarantees the UX contract — the user always sees an honest score even when the 1.5B model glosses over differences. Log INFO line per safety-net firing.

### Sub-decision 33d: New audio service endpoint `POST /tts-sync`

The audio service already has `_generate_tts(text, language, engine)` (M6) used by the RabbitMQ consumer. M33 adds a sync FastAPI route that reuses this internal helper:

- Pydantic: `{text: str, language: str = "en"}`.
- Calls `_generate_tts` with the configured engine (default `edge-tts` per M29's `pl-PL-ZofiaNeural` and friends).
- Returns the MP3/OGG bytes with `Content-Type: audio/mpeg` (or whatever the engine produced).
- 200 OK on success; 415 if generation fails; 503 if Edge TTS network call hangs past 25 s.
- Caps `text` at 500 chars.

No new dependencies, no new model. ~25 lines of Python.

### Sub-decision 33e: Extension UI — Shadowing block

A new amber-themed "🎤 Practice Pronunciation" button in the QL footer (alongside Explain Grammar and Explain Slang/Idiom) and the YouTube overlay footer. Click expands a `#lx-ql-shadow` / `#lx-yt-shadow` block inside the scroll body containing:

1. **Reference text display** — read-only, shows the selected phrase prominently. Will be re-rendered with per-word annotation after evaluation.
2. **▶ Play Original** button — fetches TTS via `/lexora_api/shadow_tts`, sets the response as the `src` of an internal `<audio>` element, plays. Disabled while the request is in flight.
3. **🎙 Hold to Record** button — `mousedown` triggers offscreen-doc record start, `mouseup` triggers stop and POST. Visual feedback: button glows red while recording, shows "Recording…" label, then "Analysing…" while the proxy + LLM run.
4. **Score + feedback** — once the proxy returns:
   - Big score badge (`85/100`), colour-coded (green ≥80, amber 60-79, red <60)
   - Per-word annotation: missed words struck through in red, mispronounced words underlined in amber, matched words plain
   - Feedback line below in italic (in the user's `language`)

Each click on Practice Pronunciation expands the block fresh — the user can iterate (hear original, record, read feedback, re-record).

### Sub-decision 33f: No persistence in the browser path

M33 deliberately doesn't write anything to `language.speaking.session` or any new model. Each shadowing attempt is ephemeral. Rationale:

- The session model from M30 is portal-scoped; reusing it from the extension would require auth-bridging the M30 session creation flow through the extension's session-cookie mechanism. Out of scope.
- Users practising on the web don't expect every word they say to be logged. Privacy-respecting default.
- A future M-thirty-something could add an opt-in "Save to my pronunciation history" toggle that POSTs the result back to the portal. Documented as a revisit trigger, not a milestone scope item.

### Step-by-step work plan

**Step 1 — LLM endpoint** (`POST /evaluate-pronunciation`)
- Add `EvaluatePronunciationRequest` + `_EVALUATE_PRONUNCIATION_SYSTEM_PROMPT` + `_PRONUNCIATION_EXAMPLES` per-language anchors + `_evaluate_pronunciation()` helper + `/evaluate-pronunciation` route.
- Server-side safety net (Python word-diff fallback when LLM glosses over differences).
- Defensive coerce: clamp score to 0-100, drop empty / overlong words, cap arrays at 20.
- `make up-llm-no-cache`; smoke for byte-identical / one-word-missed / multi-word-mispronounced cases in en/uk/el/pl.

**Step 2 — Audio service endpoint** (`POST /tts-sync`)
- Add Pydantic + sync route reusing the existing `_generate_tts`.
- 500-char cap, 25 s timeout (safety bound; Edge TTS is fast).
- `make up-audio-no-cache`; curl smoke streams MP3 bytes and saves to `/tmp/sample.mp3` for ear-check.

**Step 3 — Odoo proxy endpoints**
- `POST /lexora_api/shadow_tts` — proxies to audio `/tts-sync`, streams `audio/mpeg` back. CORS reflection identical to existing `/lexora_api/*` routes.
- `POST /lexora_api/shadow_evaluate` — multipart orchestrator. Calls audio `/transcribe-sync` (M30) then llm `/evaluate-pronunciation`. Combined JSON response. Pre-creates `language.speaking.session` row? **No** (per 33f).
- `--update language_portal --stop-after-init`; curl smoke with a real WAV (espeak-ng output of the reference text → known-good audio).

**Step 4 — Extension offscreen mic infrastructure**
- New `extension/offscreen.html` + `offscreen.js`: minimal page running `getUserMedia` + `MediaRecorder`, message-driven.
- `extension/manifest.json`: add `"offscreen"` to `permissions`.
- `extension/background.js`: lifecycle helper `_ensureOffscreen()`, plus `lexora-mic-start` / `lexora-mic-stop` message routing between content scripts and the offscreen doc.
- Sanity: test record start/stop without any UI by triggering messages from the DevTools service-worker console.

**Step 5 — Extension UI (Quick Look + YouTube)**
- Add "🎤 Practice Pronunciation" button in QL `_renderQlOverlay` (alongside Explain Grammar + Explain Slang).
- Add `#lx-ql-shadow` block with reference text, ▶ Play Original, 🎙 Hold to Record, score + feedback panel.
- `_QL_CSS` extended: `.lx-ql-shadow-btn`, `.lx-ql-shadow-block`, `.lx-ql-shadow-score`, `.lx-ql-shadow-word-missed` (red strikethrough), `.lx-ql-shadow-word-mispron` (amber underline), `.lx-ql-shadow-feedback` (italic).
- Mirror in `extension/overlay.js` for YouTube subtitle overlay.
- `extension/background.js`: `lexora-shadow-tts` and `lexora-shadow-evaluate` message handlers.

**Step 6 — Verification**
- Browser smoke: select a 5-10 word sentence on Wikipedia → click 🎤 → ▶ Play Original (perfect TTS plays) → 🎙 Hold to Record (red glow during recording) → release → ~30 s wait → score badge + per-word annotation render.
- Mic permission flow: first time exercises Chrome's permission prompt; subsequent uses on any tab don't re-prompt.
- Negative tests: deny mic permission → friendly error. Long sentence (>500 chars) → reference truncated client-side with hint.
- Multi-language: same flow on a Polish article and a Greek blog.

**Step 7 — ADR-032 + final docs flip**
- ADR-032 in DECISIONS.md: offscreen-document mic strategy, two-endpoint orchestration vs. single-endpoint design tradeoff, server-side word-diff safety net, no-persistence-by-default rationale.
- PLAN.md → v2.4, M33 row → ✅ Complete.
- TASKS.md archive.
- README.md: M33 row in implementation status; new "Webpage Shadowing" subsection in §3.
- Branch push + PR.

### Verification commands (M33-S6)

```bash
# After Steps 1-3
make up-llm-no-cache && make up-audio-no-cache
docker exec odoo odoo -d lexora --update language_portal --stop-after-init --no-http
docker restart odoo

# /evaluate-pronunciation smoke
curl -X POST http://localhost:8002/evaluate-pronunciation \
  -H 'Content-Type: application/json' \
  -d '{"reference_text":"The quick brown fox jumps over the lazy dog.",
       "transcript":"the quick brown fox jumps over lazy dog",
       "language":"en"}'
# → {"score":~88,"missed_words":["the"],"mispronounced_words":[],
#    "feedback":"Almost there — you skipped the second 'the'."}

# /tts-sync smoke (saves mp3 to /tmp for ear-check)
curl -X POST http://localhost:8004/tts-sync \
  -H 'Content-Type: application/json' \
  -d '{"text":"The quick brown fox","language":"en"}' \
  -o /tmp/ref.mp3
file /tmp/ref.mp3   # → MPEG ADTS, layer III

# Odoo proxy: stream TTS through the proxy (with session cookie)
curl -X POST http://localhost:5433/lexora_api/shadow_tts \
  -H 'Content-Type: application/json' \
  -H "X-Lexora-Session-Id: <sid>" \
  -d '{"text":"hello world","language":"en"}' \
  -o /tmp/ref-via-proxy.mp3

# Odoo proxy: full evaluate flow with a recorded sample
curl -X POST http://localhost:5433/lexora_api/shadow_evaluate \
  -H "X-Lexora-Session-Id: <sid>" \
  -F "audio=@/tmp/sample.webm" \
  -F "reference_text=The quick brown fox" \
  -F "language=en"

# Extension browser smoke (Step 6) covers the rest end-to-end.
```

**Acceptance:** a user reading any webpage can select a sentence, click 🎤, hear the TTS, hold-to-record themselves, and within ~40 s see a 0-100 score, per-word red/amber annotation, and a one-sentence feedback note in their language. Mic permission is requested once per extension, not per webpage. No data is persisted server-side without explicit opt-in.

---

## M34 — YouTube Vocab Radar (Extension)

**Goal:** Bring spaced repetition to where the user already spends their time —
YouTube. The extension scans upcoming subtitles for words the user has saved.
When a known word is about to be spoken, the radar pauses the video and shows
a glassmorphism alert with the word, translations, and the surrounding cue.
One click on "⏪ Rewind 5 s & Play" replays the natural-context pronunciation.
A configurable cooldown (default 120 s between auto-pauses) prevents
interruption storms for users with hundreds of saved words.

This is the **first organic-context** extension feature — the user doesn't have
to click anything or select text; vocabulary surfaces naturally as they watch.
Architectural pattern is read-only: no recording (M33), no input (M31), no
selection (M28/M32). Pure passive look-ahead + targeted UI interruption.

**Architecture (synchronous fetch + look-ahead scanner; no RabbitMQ, no LLM,
no per-event server roundtrip):**

```
Background service worker (on startup + on add_word cache invalidation)
   → GET /lexora_api/my_vocab  (Odoo proxy, lightweight projection)
   → caches result in chrome.storage.local (lx_radar_vocab_cache, 15-min TTL)

On youtube.com tab navigation:
   manifest content_scripts loads extension/youtube_radar.js
   → reads vocab cache (cache miss → fires lexora-get-my-vocab via background)
   → injects extension/youtube_radar_inject.js into the page's main world
       (web_accessible_resources entry; bridge via window.postMessage)

In the page's main world (inject script):
   patches XMLHttpRequest.prototype.send / fetch
   sniffs for *.youtube.com/api/timedtext requests
   on response, posts the JSON3 / SRV3 cue array back to the content script
   via window.postMessage({type:'lx-radar-cues', cues:[...]})

In the content script (isolated world):
   receives the cue array, normalises into [{startMs, endMs, text}]
   builds a Map<normalised_word, vocab_entry> from the cached vocab
   tokenises every cue; pre-computes a sorted "hit timeline":
     [{atMs, word, entry, cue}]
   subscribes to <video>.timeupdate (throttled to ~250 ms)
   on each tick: peek the next hit within LOOK_AHEAD_MS (default 4000 ms)
       AND respect COOLDOWN_MS (default 120 000 ms) since the last firing
       AND check the per-tab skip set + master kill-switch
   if eligible: video.pause(); render the radar overlay
       overlay buttons:
         "⏪ Rewind 5 s & Play" → video.currentTime = max(0, t - 5); video.play()
         "▶ Continue"          → video.play()
         "🔕 Skip this word"    → addToTabSkipSet(word); video.play()
         "✖ Disable for this video" → tabKillSwitch = true; video.play()
```

### Sub-decision 34a: New Odoo proxy `GET /lexora_api/my_vocab`

A separate, leaner endpoint from M27's `/lexora_api/get_learned_words` because
the use-case is different:

- **M27 (review-in-the-wild)** — highlights every known word on every webpage.
  Needs SRS state + days-ago to colour the underline. Capped at 500.
- **M34 (radar)** — match against subtitle cues; renders a single alert on hit.
  Needs all-language translations cleanly. Capped at 1000 (some users have
  bigger active vocab than 500). No SRS state needed.

**Pydantic-equivalent response shape:**

```json
{
  "status": "ok",
  "words": [
    {
      "id": 1234,
      "word": "ephemeral",
      "normalized": "ephemeral",
      "lang": "en",
      "translations": {
        "uk": "короткочасний",
        "el": "εφήμερος",
        "pl": "efemeryczny"
      }
    }
  ],
  "generated_at": 1747094400
}
```

- Auth: `_require_session()` (browser-extension session bridge, same as
  every other `/lexora_api/*` route since M22).
- Query: joins `language.entry` with `language.translation` for every
  `status='completed'` translation. Filter: `status='active'` AND
  `pvp_eligible=True` (i.e. has at least one completed translation —
  otherwise the radar alert would have nothing useful to show).
- Order: `write_date desc` (most recently touched first; matches the
  user's mental "recent vocab" model).
- Cap: 1000 entries. Env-overridable via `LEXORA_RADAR_VOCAB_LIMIT`.
- CORS reflection identical to all other `/lexora_api/*` routes.

**Why not reuse `/lexora_api/get_learned_words` with a query param?** The two
endpoints will diverge over time (SRS state for M27; per-language filters for
M34) and bundling them risks one consumer breaking the other on every change.
The shapes are also subtly different (`translations` dict vs. SRS metadata).
Two endpoints, single responsibility each.

### Sub-decision 34b: Look-ahead via `/api/timedtext` XHR interception (with DOM fallback)

**The hard problem:** to look ~4 seconds ahead, we need to know what the next
cue will be **before YouTube renders it**. DOM observation of
`.ytp-caption-segment` (M24 pattern) only shows the **current** cue. There are
three viable paths:

| Option | Mechanism | Look-ahead | Pros | Cons |
|---|---|---|---|---|
| A | Intercept `/api/timedtext` XHR | Full track | Get the whole cue list at once; precise timing | Requires main-world injection; YouTube format (JSON3 / SRV3) can shift |
| B | Read `<track>` / `TextTrack` API | Full track | Standard Web API; clean | YouTube hides cues inside Shadow DOM and disables the native track on the `<video>` |
| C | DOM observation only (M24-style) | Zero | Already works; no main-world injection | Cannot look ahead; would have to pause AS the word is spoken — too late |

**Decision: Option A as primary, Option C as fallback.**

- **Primary path (A):** `extension/youtube_radar_inject.js` runs in the page's
  main world (loaded via `chrome.scripting.executeScript` with
  `world: 'MAIN'`, or via the classic `<script src=getURL(...)>` injection
  if `chrome.scripting` is unavailable from content scripts). It patches
  `XMLHttpRequest.prototype.open` + `send` and `window.fetch`. On any
  `*.youtube.com/api/timedtext` response, it parses the JSON3 body
  (YouTube's modern caption format, has `events[]` with `tStartMs`,
  `dDurationMs`, `segs[].utf8`) and posts the normalised cue array back to
  the content script via `window.postMessage`. Falls back gracefully on
  SRV3 / XML format if JSON3 is absent.
- **Fallback path (C):** if no `/api/timedtext` request fires within the
  first 10 seconds of playback (e.g. live stream, auto-translated tracks
  loaded differently, or YouTube switches formats), the content script
  starts a `MutationObserver` on `.ytp-caption-window-container` and matches
  against the **current** cue. The radar still works, just with zero
  look-ahead — pauses fire as the word is spoken. Documented as a known
  degraded mode.

**Manifest changes:**

- `youtube_radar.js` added to `content_scripts` matched on `*://*.youtube.com/*`.
- `youtube_radar_inject.js` added to `web_accessible_resources` matched on
  the same pattern so the page's main world can load it.
- No new permissions (no `tabs`, no `scripting` — the content-script-driven
  injection via `<script src=getURL>` works under existing `activeTab`).

**Why not intercept network traffic via `webRequest`?** MV3 disallows
synchronous response inspection in the service worker. Even with
`declarativeNetRequest`, we can't read response bodies. The main-world
injection is the only MV3-compatible way to read the cue payload.

### Sub-decision 34c: Cooldown + skip controls

The radar would be unusable for a user with 500 saved words and a chatty
YouTube channel — every other sentence would pause the video. Three control
layers, all configurable in the Options page:

| Control | Default | Storage | Persistence |
|---|---|---|---|
| Master toggle "Enable Radar" | ON | `chrome.storage.sync.lexora_radar_enabled` | Persistent |
| Cooldown between pauses | 120 s | `chrome.storage.sync.lexora_radar_cooldown_seconds` | Persistent |
| Look-ahead window | 4 s | `chrome.storage.sync.lexora_radar_lookahead_seconds` | Persistent |
| Per-tab skipped words | {} | `chrome.storage.session.lexora_radar_skip_<tabId>` | Tab-lifetime |
| Per-video kill switch | OFF | in-memory only | Page-lifetime |

The per-tab skip set is **session-scoped** (cleared on tab close) so the user's
"I already know this one for now" doesn't permanently exclude the word from
future practice. The master toggle and the per-video kill switch give the
user two escape hatches at different scopes.

**Cooldown rule:** the timer starts when the radar **closes** (not when it
fires) — so a user reading a long alert isn't punished with the next pause
firing immediately after they hit Continue.

### Sub-decision 34d: Radar UI — top-level overlay, not nested in the Quick Look card

The existing YouTube overlay (`extension/overlay.js`, M24 + M28 + M32 + M33)
is **click-on-subtitle-word** triggered. M34's radar is **auto-triggered**
on a different code path. Putting both in the same DOM container would
guarantee a layout/z-index/visibility-state collision the first time a user
clicked a subtitle word while a radar alert was already open.

**Decision:** new top-level overlay `#lx-radar-card` (Shadow DOM host on the
extension's content-script side, same pattern as the Quick Look overlay's
`#lx-ql-shadow-host`). Positioned bottom-centre, ~360 px wide. Glassmorphism
with a teal/amber accent (visually distinct from the indigo M28 grammar
block and the amber M32 slang block — so a user with both features active
on the same page sees three colour-coded surfaces, not a mush).

**Structure** (re-using M28-12d flex-sandwich + `!important` flex props):

```
.lx-radar-card
  .lx-radar-header   (📡 Lexora Radar — Word in your vocabulary)
  .lx-radar-scroll
    .lx-radar-word       (large, bold)
    .lx-radar-trans      (🇺🇦/🇬🇷/🇵🇱 rows where present)
    .lx-radar-cue        (italic; the full subtitle sentence the word came from)
  .lx-radar-footer
    [⏪ Rewind 5 s & Play]
    [▶ Continue]
    [🔕 Skip this word]
    [✖ Disable for this video]
```

The header is **draggable** (reuses the M28-17 `_makeDraggable(overlayEl)`
pattern with viewport clamping). The card auto-closes if `<video>.play()` is
called from outside the radar (e.g. user clicks the YouTube play button
directly).

### Sub-decision 34e: Match algorithm

The vocab Map is keyed by `normalize(word)` (lowercase + Unicode NFC +
diacritic-preserving — same `_normalize_word` helper as M27 uses). For each
cue:

1. Tokenise cue text on the same Unicode word-boundary regex M27 + M33 use
   (`/[\wÀ-ɏͰ-ϿЀ-ӿ'-]+/u`). Preserves Greek, Cyrillic, Polish diacritics.
2. For each token, strip leading/trailing punctuation, lowercase, NFC.
3. Look up in the vocab Map. **First hit wins** per cue (no multi-pause from
   one cue; a single cue can only consume one pause budget).
4. Multi-word phrases (e.g. "give up", "kick the bucket") are checked **first**
   as a sliding window over 2-3 token N-grams, before single-token lookup.
   This way `kick the bucket` doesn't get pre-empted by `kick` if both are in
   the vocab. The radar prefers the **longest-match** entry.
5. The hit is recorded with the cue's `startMs` (not the token's index within
   the cue — sub-cue timing isn't reliably exposed in the JSON3 format).

### Sub-decision 34f: No persistence

Radar events are ephemeral. No DB write, no `language.review` update, no
"the user encountered this word in a YouTube video" telemetry. Rationale:

- M27 already covers passive review-in-the-wild on web pages — its SRS
  integration is the right place for "user has seen this word recently".
  If M34 also wrote to SRS state, a single video binge would skew review
  scheduling.
- Privacy: the user's YouTube watch history doesn't leave the extension.
- Same default as M33 (no persistence by default; opt-in revisit trigger).

### Step-by-step work plan

**Step 1 — Odoo proxy `GET /lexora_api/my_vocab`**

- `language_portal/controllers/portal_api.py`:
  - New `_MAX_RADAR_VOCAB = int(os.environ.get('LEXORA_RADAR_VOCAB_LIMIT', '1000'))` constant.
  - `@http.route('/lexora_api/my_vocab', type='http', auth='none', methods=['GET'], csrf=False)`.
  - `_require_session()` first line.
  - Query active `language.entry` rows owned by the caller, `pvp_eligible=True`,
    ordered `write_date desc`, capped at `_MAX_RADAR_VOCAB`.
  - For each entry: build `translations = {t.target_language: t.translated_text
    for t in entry.translation_ids if t.status == 'completed' and t.translated_text}`.
  - Build the JSON envelope and return via `_json_response()` so CORS
    reflection lands consistently.
- `OPTIONS` preflight handled by the existing wildcard preflight controller in
  the same file (no new OPTIONS route needed).

**Step 2 — Extension background fetch + cache**

- `extension/background.js`:
  - New `handleGetMyVocab()` — GET `/lexora_api/my_vocab` via existing
    session-cookie bridge (`getSessionHeader` → `X-Lexora-Session-Id`).
    On 200, persists to `chrome.storage.local.lx_radar_vocab_cache` with
    `generated_at` timestamp. On 401, returns `{status:'unauthorized'}` so
    the content script can stay silent.
  - `lexora-get-my-vocab` message router case.
  - Cache invalidation hook: extend the existing `handleAddWordOverlay` /
    context-menu `add_word` post-success block to also wipe
    `lx_radar_vocab_cache`. (M27 already wipes `lx_word_cache` there; same
    pattern, second key.)
- Cache TTL = 15 min (same as M27's review-in-the-wild cache, same rationale).

**Step 3 — Main-world inject script for `/api/timedtext` interception**

- New file `extension/youtube_radar_inject.js`:
  - Runs in the page's main world via `<script src=getURL(...)>` element
    appended to `document.documentElement` by `youtube_radar.js`.
  - Patches `XMLHttpRequest.prototype.open` to record URLs; patches `send`
    so `addEventListener('load')` callbacks can read `responseText` once
    URL matches `/^https?:\/\/[^/]*\.youtube\.com\/api\/timedtext\b/`.
  - Patches `window.fetch` similarly (`Response.clone().text()` to read
    without consuming the page's own consumer).
  - Posts cues via `window.postMessage({source:'lx-radar', type:'cues',
    cues:[{startMs, endMs, text}]}, '*')`. Source field guards against
    cross-extension postMessage collisions.
  - JSON3 parser primary; SRV3/XML fallback; logs a one-time warning if
    the format is unknown.
- `extension/manifest.json`:
  - Add `"youtube_radar_inject.js"` to `web_accessible_resources` (resources
    list, with `matches: ["*://*.youtube.com/*"]`).
  - Add `extension/youtube_radar.js` to `content_scripts` for YouTube.

**Step 4 — Content script `youtube_radar.js` (scanner + UI)**

- New file `extension/youtube_radar.js`:
  - On `document_idle`, load the inject script (idempotent —
    `if (document.querySelector('script[data-lx-radar-inject])')` guard).
  - Bootstrap: read master toggle + cooldown + lookahead from
    `chrome.storage.sync`; default ON, 120 s, 4 s.
  - `_getVocab()` async — read `lx_radar_vocab_cache`; on miss or stale
    (>15 min) send `lexora-get-my-vocab` and re-cache. Returns
    `Map<normalized, entry>` plus a separate phrase-list for the
    longest-match sliding window.
  - `window.addEventListener('message', ...)` listens for the inject script's
    `lx-radar / cues` envelope. Rebuilds the hit timeline.
  - **Hit timeline construction:** for each cue, run the longest-match
    sliding window (3-gram → 2-gram → 1-gram); first hit per cue records
    `{atMs: cue.startMs, word, entry, cueText}`. Result is sorted by `atMs`
    and held in a closure variable `_radarHits`.
  - **Scan tick:** subscribes to `<video>.timeupdate` (throttled via a
    `_lastTickMs` guard, ~250 ms). On each tick:
    - `currentMs = video.currentTime * 1000`
    - Find the next hit with `atMs > currentMs && atMs <= currentMs +
      LOOKAHEAD_MS`.
    - If found AND `(performance.now() - _lastFiredAt) > COOLDOWN_MS` AND
      `!_tabSkip.has(hit.word)` AND `!_videoKillSwitch` AND
      `masterToggle === true`:
      - `video.pause()`
      - `_renderRadarOverlay(hit, video)`
      - (do NOT advance `_lastFiredAt` until the overlay closes — see
        sub-decision 34c rationale)
  - **Navigation reset:** YouTube is an SPA. Listen for
    `yt-navigate-finish` events (YouTube custom event fired on URL change)
    and reset `_radarHits`, `_videoKillSwitch`, and the per-tab skip set
    on every nav. Without this, an old video's hits keep firing on the new
    video.

**Step 5 — Radar overlay UI**

- Glassmorphism Shadow DOM host appended to `document.body`.
- `_RADAR_CSS` string constant injected once (`_ensureRadarStyles`).
  Teal/amber palette (`rgba(20,184,166,...)` + `rgba(245,158,11,...)`),
  consistent with M33's teal recorder + M32's amber slang block.
- Four footer buttons wired to:
  1. `_onRewindAndPlay()` — `video.currentTime = Math.max(0,
     video.currentTime - 5); _closeOverlay(); video.play();`
  2. `_onContinue()` — `_closeOverlay(); video.play();`
  3. `_onSkipWord(word)` — `_tabSkip.add(word); _closeOverlay();
     video.play();`
  4. `_onDisableForVideo()` — `_videoKillSwitch = true; _closeOverlay();
     video.play();`
- `_closeOverlay()` advances `_lastFiredAt = performance.now()` so the
  cooldown timer starts at close, not at fire.
- `_makeDraggable(card)` reuses the M28-17 pattern for header-drag with
  viewport clamping.

**Step 6 — Options page surface**

- `extension/options.html`:
  - New "YouTube Vocab Radar (M34)" section with:
    - Checkbox "Enable Radar" → `lexora_radar_enabled` (default ON).
    - Number input "Cooldown between pauses (seconds)" → `lexora_radar_cooldown_seconds`
      (default 120, min 10, max 3600).
    - Number input "Look-ahead window (seconds)" → `lexora_radar_lookahead_seconds`
      (default 4, min 1, max 15).
    - Hint paragraph explaining what the radar does and that no data is
      persisted server-side.
- `extension/options.js`:
  - Initial load reads + pre-fills all three values.
  - `change` autosave (no Save button — consistent with M31/M32 toggle
    pattern). Content script subscribes to `chrome.storage.onChanged` so
    a toggle change takes effect on the next `timeupdate` tick without a
    page reload.

**Step 7 — ADR-033 + final docs flip**

- ADR-033 in `docs/DECISIONS.md` covering six sub-decisions:
  33a · separate `/my/vocab` endpoint; 33b · XHR interception + DOM
  fallback strategy; 33c · cooldown rule + per-tab skip set + per-video
  kill switch; 33d · top-level overlay vs. nested-in-Quick-Look; 33e ·
  longest-match sliding window; 33f · no persistence.
- `PLAN.md` v2.5 → v2.6; M34 row flipped ✅ Complete; status header
  reflects M0-M34 done.
- `TASKS.md` archive.
- `README.md` — Browser Ecosystem subsection adds M34; LLM service
  endpoint list **unchanged** (M34 doesn't add a sync LLM endpoint).
- Commit + push.

### Verification commands

```bash
# Step 1 — Odoo proxy
docker exec odoo odoo -d lexora --update language_portal \
  --stop-after-init --no-http
docker restart odoo

curl -X GET http://localhost:5433/lexora_api/my_vocab \
  -H "X-Lexora-Session-Id: <sid>"
# → {"status":"ok","words":[...],"generated_at":...}

# Step 2 — Background cache (run from extension SW DevTools console)
await chrome.runtime.sendMessage({action:'lexora-get-my-vocab'});
// → {status:'ok', words:[...]}
const {lx_radar_vocab_cache: cache} = await chrome.storage.local.get('lx_radar_vocab_cache');
console.log('cache_size', cache.words.length, 'age_s',
  Math.round((Date.now() - cache.generated_at*1000)/1000));

# Step 3 — XHR interception smoke (run on any youtube.com video page console)
window.addEventListener('message', e => {
  if (e.data?.source === 'lx-radar' && e.data?.type === 'cues') {
    console.log('cues received:', e.data.cues.length, 'first:', e.data.cues[0]);
  }
});
// Then turn captions ON. Within a few seconds the listener should fire.

# Steps 4-5 — Browser smoke (user-side):
# Load extension, open any YouTube video with subtitles ON that contains
# a word from your vocabulary. Within a few seconds of the word appearing
# on screen, the video should pause and the Radar overlay should appear
# with translations and rewind button. Confirm:
#   - "⏪ Rewind 5 s & Play" sets currentTime correctly and resumes playback.
#   - "🔕 Skip this word" suppresses subsequent pauses for that word in the tab.
#   - 120 s cooldown enforced (try a video with the same word appearing twice
#     within 60 s — second pause should be suppressed).
#   - SPA navigation (clicking a video recommendation) resets state cleanly.

# Step 6 — Options
# Toggle "Enable Radar" OFF in Options → no pauses on the next subtitle hit.
# Drop cooldown to 10 s → pauses now allowed every 10 s.
```

**Acceptance:** a user with ≥50 saved vocabulary words can play any
subtitled YouTube video and within a minute see the radar pause the video
on a known word. The "⏪ Rewind 5 s & Play" button replays the word in
its native context. The 120 s cooldown prevents pause-storms. The user
can disable the radar per-video, per-word, or globally via Options.
Vocabulary cache refreshes when the user adds new words via the existing
"Add to List" flow.

---

## Dependency Graph (final, M0–M34)

```
M0 → M1 → M2 → M3
               ↓
               M4 → M4b → M4c
               ↓
          M5   M6
          ↓    ↓
          M7 ←→ M8
          ↓
          M9 → M10 → M11 → M12 → M13 → M14 → M15 → M16 → M17 → M18
                                                                    ↓
                                                              M18.5 (Header)
                                                                    ↓
                                                  M19 ←──────── parallel ──────→ M20
                                                                    ↓
                                                                   M21
                                                                    ↓
                                            M22 (Extension scaffold + Odoo API)
                                                 ↓              ↓           ↓
                                               M23          M24           M25
                                          (Contextual)   (Subtitles)  (New Tab)
                                                 ↓              ↓
                                               M27            M28
                                          (Highlighting)  (Grammar LLM)
                                                    (M26 — AI Helpdesk — postponed ⏸)
                                                 ↓              ↓
                                               M31            M32
                                            (Writer)       (Slang)
                                                                ↓
                                                              M33
                                                          (Shadowing)
                                                                ↓
                                                              M34
                                                       (YouTube Radar)
```

M34 depends on **M22** (extension scaffold + `_require_session()` proxy
pattern), **M24** (existing YouTube content-script bootstrap; M34 adds a
sibling content script, not an extension of it), and **M27** (vocab cache
pattern + cache-invalidation hook on `add_word` success). No new service
dependencies — M34 is the first extension milestone that touches neither
the LLM service nor the audio service.

---

## M35 — Multi-word YouTube Subtitle Selection (Extension)

> **🚨 STRATEGY PIVOT (2026-05-16):** Strategy A (native browser selection
> via `user-select: text !important` override) was implemented end-to-end
> in commit `ad92887` and **FAILED in browser smoke**. The user-reported
> verdict: "щось воно ніфіга не тягнеться" — the selection range never
> extends past the click anchor. YouTube's player aggressively re-applies
> `user-select: none` via JS on every cue render and intercepts the
> selection-extension machinery deep enough that no CSS / event-firewall
> combination we tried kept a drag-extended range alive. **Strategy B**
> (manual drag state machine on `mouseenter`) was considered too fragile
> against YT's `.ytp-caption-segment` recycling and a poor UX (no native
> selection feedback). M35 has pivoted to **Strategy C — Ctrl/⌘-Click
> multi-select**, documented below the original Strategy A/B history.
> The Strategy A/B writeup is preserved as an engineering record of what
> we tried and why it didn't work.

**Goal:** Let the user select multiple YouTube subtitle words to trigger
the existing Quick Look / Grammar / Slang / Shadowing overlays on the entire
phrase — "kick the bucket", "give up on yourself", "il est en train de" — not
just the single word their cursor happens to land on. This closes the obvious
ergonomic gap that's been visible since M24 wrapped each cue word in an
isolated `<span>`.

This is a pure UX milestone: zero new backend endpoints, zero new services, no
new permissions. The whole milestone lives inside `extension/overlay.js` and a
few CSS rules.

**The hard problem (architectural analysis):**

YouTube's HTML5 player runs an aggressive pointer-event interception scheme on
its viewport surface. Three concrete obstructions for drag-to-select:

1. **`user-select: none`** applied by YT to `.html5-video-container` and
   inherited by descendants. Our `.lx-sub-word` spans visually look selectable
   but `getSelection()` returns an empty string when the user releases the
   mouse — the browser was never allowed to extend a selection range.

2. **Click-to-toggle-play on the player surface.** A `mousedown` / `mouseup`
   on any descendant of `.html5-video-player` bubbles to YT's own listener and
   pauses (or resumes) the video. The M24 single-word `click` handler already
   `stopPropagation`s the `click` event — but `mousedown` and `mouseup` are
   still propagating, so a drag across subtitle words risks a stray pause +
   the controls bar appearing mid-drag.

3. **Cue-segment volatility.** YT replaces `.ytp-caption-segment` DOM nodes on
   every subtitle change (typically every 2-4 s). A user mid-drag whose cursor
   crosses a cue boundary at the moment YT swaps in fresh `<span>` elements
   loses the selection because the original anchor node is gone.

**Two viable strategies, primary + fallback:**

### Strategy A — Native browser selection with event firewall (primary)

The browser already knows how to draw a selection range across multiple inline
text nodes. We just need to (a) tell YT's stylesheet not to suppress it on the
subtitle subtree, and (b) keep the drag events from waking up YT's player
listeners.

**The exact CSS — three rules:**

```css
.ytp-caption-window-container,
.ytp-captions-container,
.ytp-caption-segment {
  user-select: text !important;
  -webkit-user-select: text !important;
}
.lx-sub-word {
  user-select: text !important;
  -webkit-user-select: text !important;
  cursor: text !important;  /* drag-affordance for multi-word; click still fires */
}
.lx-sub-word:hover {
  cursor: pointer !important;  /* on a brief hover, still affords click */
}
```

The cursor toggle is deliberate — `cursor: text` on the span body signals
"drag here to select"; `cursor: pointer` on hover doesn't actually fire (CSS
specificity, plus drag doesn't fire `:hover`). In practice users learn the
drag affordance from the I-beam cursor change without any extra UI.

**The exact event firewall — one persistent capture-phase listener trio
on `.ytp-caption-window-container`:**

```js
// Bound once on the container that survives cue-segment swaps —
// _attachCaptionObserver already locates this element, reuse the
// reference.
const ROOT = _getContainer();
['mousedown', 'mousemove', 'mouseup'].forEach((type) => {
  ROOT.addEventListener(type, (e) => {
    if (!e.target.closest('.lx-sub-word')) return;
    e.stopPropagation();  // CRITICAL: keeps YT player silent
    // DO NOT preventDefault — that would kill native selection
  }, { capture: true });
});
```

`stopPropagation` (not `stopImmediatePropagation`) on the capture phase: YT's
`mousedown` listener on `.html5-video-player` lives on the bubble phase, so
our capture-phase `stopPropagation` aborts the bubble entirely. YT never sees
the event. The browser's own selection-extension logic, which runs deeper than
event listeners, is untouched. Verified pattern from M24's
`_onWordClick({ capture: true })`.

**Mouseup → phrase extraction:**

The same `mouseup` capture-phase listener (we add a second-stage post-stop
handler) reads the selection AFTER the browser has finished extending the
range. Normalisation pipeline:

```js
ROOT.addEventListener('mouseup', (e) => {
  if (!e.target.closest('.lx-sub-word')) return;
  // wait one microtask so getSelection sees the final range
  queueMicrotask(() => {
    const raw = (window.getSelection() || '').toString();
    const phrase = _normalisePhrase(raw);
    if (!phrase) return;                          // no drag → click flow handles it
    if (!/\s/.test(phrase)) return;               // single token → click flow handles it
    _lxSwallowNextClick = true;                   // suppress the per-span click that would otherwise fire
    _triggerPhraseOverlay(phrase);
    window.getSelection().removeAllRanges();      // clear the highlight after we've used it
  });
}, { capture: true });
```

`_normalisePhrase(raw)` is:

```js
function _normalisePhrase(s) {
  return (s || '')
    .replace(/\s+/g, ' ')          // collapse internal whitespace
    .trim()
    .replace(/^[.,!?;:'"()\[\]{}\-–—]+|[.,!?;:'"()\[\]{}\-–—]+$/g, '')
    .trim();
}
```

Internal apostrophes (`don't`) and hyphens (`mother-in-law`) are
intentionally preserved. Outer punctuation is stripped same as M24's single-
word path so the lookup key matches the vocab normalisation rule already used
by M2 / M27 / M34.

**Click coexistence — the `_lxSwallowNextClick` flag:**

When the user releases the mouse after a drag, the browser fires `mouseup`,
then (on the same target where the last `mousedown` happened) a `click`. M24's
per-span `click` listener would interpret this as a single-word lookup on the
anchor word. To suppress it cleanly:

```js
// existing _onWordClick gains a one-line guard at the top:
function _onWordClick(e) {
  if (_lxSwallowNextClick) {
    _lxSwallowNextClick = false;
    e.stopPropagation();
    e.preventDefault();
    return;
  }
  // ... existing single-word flow unchanged ...
}
```

The flag is set in the `mouseup` post-microtask handler exactly when we've
captured a multi-word phrase. Single-word selections (e.g. double-click on a
word, which selects only that word) take the `!/\s/.test(phrase)` branch and
fall through to the click handler naturally — same outcome as a plain click.

### Strategy B — Manual drag state machine on spans (fallback)

Only used if Strategy A turns out to be unreliable on certain YT player builds
(documented post-smoke, never pre-emptively). Pros: deterministic whole-word
selection, no `user-select` battle. Cons: ~40 lines of code, custom highlight
CSS, no native browser feedback.

```js
let _drag = null;  // {anchorIdx, spans:[<span>, ...], active:bool}

span.addEventListener('mousedown', (e) => {
  _drag = { anchor: span, spans: [span], active: true };
  span.classList.add('lx-sub-selected');
  e.stopPropagation();
});
span.addEventListener('mouseenter', () => {
  if (_drag?.active && !_drag.spans.includes(span)) {
    _drag.spans.push(span);
    span.classList.add('lx-sub-selected');
  }
});
document.addEventListener('mouseup', () => {
  if (!_drag?.active) return;
  _drag.active = false;
  if (_drag.spans.length > 1) {
    const phrase = _drag.spans.map(s => s.textContent).join(' ');
    _lxSwallowNextClick = true;
    _triggerPhraseOverlay(_normalisePhrase(phrase));
  }
  _drag.spans.forEach(s => s.classList.remove('lx-sub-selected'));
  _drag = null;
}, true);
```

CSS for the manual highlight:
`.lx-sub-selected { background: rgba(129, 140, 248, 0.35) !important; }`.

Strategy B is documented but **not implemented** in M35-S1..S5. It can be
patched in within a single commit if browser smoke shows native selection
breaks on (for example) YouTube's "ambient mode" or the new TV-mode player
shell.

### Strategy C — Ctrl/⌘-Click multi-select (CHOSEN, 2026-05-16)

After Strategy A failed in browser smoke, the user proposed a radically
simpler UX that completely sidesteps YT's selection-suppression: don't
try to drag at all. Instead, **the user Ctrl-clicks each word they want
to include in the phrase**; the buffer is finalised when they release
the modifier key.

**Why this works where A failed:**

- **No selection range.** We never call `getSelection()`. YT's
  `user-select: none` is irrelevant because we don't need the browser to
  draw or extend a range.
- **No new event types.** Each Ctrl-click is just a `click` event on a
  `.lx-sub-word` span — exactly the event surface M24 already handles.
  The `_onWordClick` listener that's been stable since M24 just gets a
  modifier branch added at the top.
- **No event firewall.** YT's bubble-phase listeners on
  `.html5-video-player` never see anything different. M24's existing
  `e.stopPropagation()` on the span's `click` listener already prevents
  the play/pause toggle from firing.
- **Deterministic.** Always whole-word, never partial. The user has
  100 % control over which spans land in the buffer.
- **Forgiving.** Toggle semantics: Ctrl-click on an already-selected
  span removes it from the buffer, so a misclick is one Ctrl-click away
  from being undone. No need to start over.

**State machine (4 transitions):**

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

**Module state added:**

```js
let _multiWordSelection = [];               // ordered list of span elements
const _MULTI_SELECTED_CLASS = 'lx-multi-selected';
```

**`_onWordClick` modifier branch (added at the top):**

```js
if (e.ctrlKey || e.metaKey) {
  e.stopPropagation();
  e.preventDefault();
  const span = e.target;
  if (!span?.classList?.contains(_WORD_CLASS)) return;
  const existing = _multiWordSelection.indexOf(span);
  if (existing >= 0) {
    _multiWordSelection.splice(existing, 1);
    span.classList.remove(_MULTI_SELECTED_CLASS);
  } else {
    _multiWordSelection.push(span);
    span.classList.add(_MULTI_SELECTED_CLASS);
  }
  return;
}
// no modifier → fall through to existing single-word click flow
```

**Helpers (module-level):**

```js
function _clearMultiSelection() {
  for (const span of _multiWordSelection) {
    try { span.classList.remove(_MULTI_SELECTED_CLASS); } catch (_) {}
  }
  _multiWordSelection = [];
}

function _finaliseMultiSelection() {
  if (!_multiWordSelection.length) return;
  const words = _multiWordSelection.map((s) => (s.textContent || '').trim());
  const phrase = _normalisePhrase(words.join(' '));
  _clearMultiSelection();
  if (!phrase) return;
  _triggerPhraseOverlay(phrase, null);
}
```

**Document-level listeners (3 added; 2 extended):**

```js
// NEW: finalise on Ctrl/⌘ release. Multi-key handling: if the OTHER
// side of Ctrl/Meta is still held (e.ctrlKey / e.metaKey after the
// event), don't finalise — only the LAST release counts.
window.addEventListener('keyup', (e) => {
  if (e.key !== 'Control' && e.key !== 'Meta') return;
  if (e.ctrlKey || e.metaKey) return;
  if (!_multiWordSelection.length) return;
  _finaliseMultiSelection();
}, true);

// EXTENDED: plain click without modifier aborts an in-progress selection.
document.addEventListener('click', (e) => {
  if (_multiWordSelection.length && !(e.ctrlKey || e.metaKey)) {
    _clearMultiSelection();
  }
  /* ...existing overlay-close logic unchanged... */
}, true);

// EXTENDED: Escape clears the multi-select buffer (mirrors overlay close).
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    _removeOverlay();
    if (_multiWordSelection.length) _clearMultiSelection();
  }
}, true);

// EXTENDED: SPA nav clears stale span references before the caption
// container is recycled.
window.addEventListener('yt-navigate-finish', () => {
  /* ...existing observer reconnect... */
  _clearMultiSelection();
});
```

**Highlight CSS:**

```css
.lx-multi-selected,
.lx-multi-selected:hover {
  background: rgba(129, 140, 248, 0.5) !important;
  color: #ffffff !important;
  outline: 1px solid rgba(129, 140, 248, 1) !important;
  border-bottom-color: rgba(129, 140, 248, 1) !important;
}
```

Stronger alpha (0.5) than the regular `:hover` state (0.25), full-opacity
outline so the selected spans remain visually distinct from any
incidentally-hovered span. The paired `:hover` selector prevents the
highlight from washing out when the cursor sits over an already-selected
span.

**Sandbox verification:** 16 / 16 state-machine cases pass in a Node
sandbox (recorded in the S1-S3 commit). Covers the happy path, toggle-
in-toggle-out, out-of-order Ctrl-clicks (order is preserved!),
deselect-in-middle, abort via `_clearMultiSelection`, single-Ctrl-click +
release (degenerates cleanly to the single-word case), and Polish /
Greek / Ukrainian token preservation.

### Sub-decision sketch (formalised in ADR-034)

| # | Decision | Why |
|---|---|---|
| 35a | Native-first, manual fallback | Native selection draws the browser's familiar blue highlight + crosses cue segments for free. Manual is a 40-line fallback if smoke shows YT actively fights the `user-select` override. |
| 35b | Event firewall on the PERSISTENT container, not per-span | `.ytp-caption-segment` and inner `.lx-sub-word` are replaced on every cue change. Binding on `.ytp-caption-window-container` survives that. One listener trio for the whole lifetime of the page. |
| 35c | Capture-phase `stopPropagation` ONLY — no `preventDefault` | `preventDefault` on `mousedown` would kill the browser's native selection. `stopPropagation` is enough — YT's player listeners are on the bubble phase. |
| 35d | `_lxSwallowNextClick` flag for click disambiguation | `mouseup` → `click` is a hard browser contract. The single-word click handler still owns the simple case; the flag is set only when we've recognised a multi-word selection. |
| 35e | Phrase normalisation = trim + collapse spaces + strip outer punctuation | Matches the existing M2 / M27 / M34 vocab normalisation rule. Internal apostrophes and hyphens preserved so `don't` and `mother-in-law` survive. |
| 35f | Selection cleanup via `removeAllRanges()` after triggering | Otherwise the blue highlight lingers until the next click and looks broken once the Quick Look card is up. |

### Step-by-step work plan

**Step M35-S1 — CSS override and event-firewall listener trio**

- Add the `user-select: text !important` block to `_OVERLAY_CSS`. Apply both
  the standard property and the `-webkit-` prefix because YT serves an
  un-prefixed older build to non-Chromium engines and the prefixed one to
  Chromium.
- Toggle `.lx-sub-word { cursor: text !important; }` with a `:hover` rule
  that keeps `cursor: pointer` for brief stationary hovers.
- In `_init()` (overlay.js bootstrap), bind the three capture-phase
  listeners (`mousedown`, `mousemove`, `mouseup`) once on
  `_getContainer()`. Re-bind on every `yt-navigate-finish` because the
  container element is replaced on hard SPA navigations. Use a
  `WeakSet<HTMLElement>` guard so we don't double-bind on a single
  element across re-attaches.

**Step M35-S2 — `_normalisePhrase` helper + `_lxSwallowNextClick` flag**

- New module-level `let _lxSwallowNextClick = false;`.
- New helper `_normalisePhrase(s)` — collapse whitespace, trim, strip outer
  punctuation (same regex as `_onWordClick` for the single-word path).
- Add the one-line guard at the top of `_onWordClick` that drains the flag
  and `stopPropagation`s + `preventDefault`s if set.

**Step M35-S3 — `mouseup` → phrase capture → overlay trigger**

- Extend the `mouseup` capture-phase listener (the same one from S1) so
  that after the `stopPropagation`, a `queueMicrotask` callback reads
  `window.getSelection().toString()`, normalises, and decides:
  - empty → return.
  - no internal whitespace → return (click handler takes over).
  - `>= 1 internal space` → set the flag, call `_triggerPhraseOverlay`,
    call `window.getSelection().removeAllRanges()`.
- `_triggerPhraseOverlay(phrase)` is mostly a re-wrap of the existing
  `_onWordClick` body: pauses the video, looks up subtitle language, calls
  `_showOverlay(phrase, ...)` with the same Loading → response state
  machine. The only divergence is the lookup payload — pass the phrase
  unchanged to `lexora-define`; the existing M24 `/define` controller
  already handles multi-word lookups (it dedups against
  `language.entry.normalized_text` which can contain spaces).

**Step M35-S4 — Verify Grammar / Slang / Shadowing inheritance**

- The Quick Look card's three buttons ("Explain Grammar", "💡 Explain
  Slang/Idiom", "🎤 Practice Pronunciation") all read the word from the
  card's own data, not from re-reading the subtitle. So a phrase that's
  surfaced via `_showOverlay(phrase, ...)` automatically flows through
  every downstream feature unchanged. Verify by clicking each button on a
  multi-word phrase in the browser smoke and confirming:
  - `/explain_grammar` returns a coherent grammar explanation for the
    full phrase.
  - `/explain_slang` correctly classifies idioms (and reports `kind:
    'literal'` for literal phrases — the M32 honesty branch).
  - `/shadow_tts` produces TTS for the whole phrase; click-to-toggle
    recording compares against the full phrase.

**Step M35-S5 — Edge-case smoke matrix**

- Drag-select across two `.ytp-caption-segment` siblings on a video
  whose captions are split into two simultaneous lines. Expected: phrase
  contains the words from both segments (browser handles cross-text-node
  selection natively).
- Drag-select while a cue change happens. Expected: selection is lost
  (known limitation, documented in ADR-034 revisit triggers); user can
  re-drag.
- Double-click a word. Expected: native single-word selection
  triggers `mouseup` with no internal whitespace → click handler takes
  over → identical UX to plain click.
- Triple-click a cue line. Expected: entire line selected →
  `mouseup` recognises >1 space → phrase overlay opens with the whole
  sentence. (Useful for grammar explanations.)
- Plain single-word click. Expected: no behaviour change from M24.
- Drag-select WHILE the radar is paused on a word (M34 active).
  Expected: works — the radar overlay is in its own top-level Shadow
  DOM host and doesn't block the captions area.

**Step M35-S6 — ADR-034 + final docs flip**

- ADR-034 in `docs/DECISIONS.md` with sub-decisions 35a-f locked in.
- PLAN.md v2.7 → v2.8, M35 row flipped ✅, status header updated.
- TASKS.md M35 block archived under Completed Milestones.
- README.md — Browser Ecosystem section M22-M34 → M22-M35; new M35
  subsection; implementation status table row. No new endpoint /
  service entries.

### Verification commands

```bash
# Static checks
node --check extension/overlay.js

# Browser smoke (user-side)
# 1. Reload extension.
# 2. Open a YouTube video with captions ON.
# 3. Drag across "kick the bucket" — overlay opens with the phrase.
# 4. Click each footer button in turn; verify Grammar / Slang /
#    Shadowing all see the full phrase.
# 5. Single-click a word — unchanged M24 behaviour.
# 6. Drag across a cue boundary — phrase spans both segments.
# 7. Try to drag-select OUTSIDE the subtitle area — YouTube's video
#    play/pause toggle works normally (event firewall scoped correctly).
```

**Acceptance:** a user can drag-select any contiguous run of words within
the YouTube subtitle layer, the Quick Look opens for the phrase (not
the single anchor word), every downstream Quick Look feature (Add to
Vocabulary, Explain Grammar, Explain Slang/Idiom, Practice
Pronunciation) operates on the full phrase, and there is zero regression
to the M24 single-word click path or to YouTube's own click-to-pause
behaviour outside the subtitle area.

---

## Dependency Graph (after M35)

M35 has a hard dependency on **M24** (the word-wrap + click pipeline this
milestone retrofits) and a soft dependency on **M28 / M32 / M33** (the Quick
Look downstream buttons that automatically inherit phrase support once
`_showOverlay(phrase, ...)` is callable with multi-word input). No backend
dependency at all — M35 is the second extension milestone (after M34) to ship
without touching any FastAPI service or RabbitMQ queue.
