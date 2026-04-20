# Lexora — Implementation Plan (MVP)

> Version: 0.2 (post-M10)
> Last updated: 2026-04-20
> Status: M0–M10 complete (resequenced); M7/M8 Social features next

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
| M7 | Posts, Articles, Comments | ⏳ **Next** | Draft → review → publish flow; comments with @mentions |
| M8 | Chat & DMs | ⏳ **Next** | Public channels + private DMs; save-to-list from chat |
| M9 | SRS Core + Dashboards | ✅ Complete (resequenced) | SM-2 spaced repetition, `/my/practice`, leaderboard, vocabulary pro dashboard |
| M10 | PvP Arena + XP System | ✅ Complete (resequenced) | Async word duels, XP/streak/levels, personal dashboard, Lexora Bot |

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
          M9 → M10
```

M3, M4, M5, M6 can be worked in parallel after M2 is stable.
M7 and M8 can be worked in parallel after M3 (auto-translate after copy depends on M3).
M9 can begin in parallel with M7/M8 (dashboards only need entry data from M2+).
M10 requires M2 (entries), M3 (translations for distractors), M9 (leaderboard UI).
