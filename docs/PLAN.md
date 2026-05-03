# Lexora — Implementation Plan (MVP)

> Version: 1.6 (M27–M28 Browser Extension — Review & Grammar — Complete)
> Last updated: 2026-05-03
> Status: M0–M25 complete; M26 postponed (resource constraints); M27–M28 complete

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
The next milestone (M29) will be planned separately.
