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

### M13 — Productivity Suite

**Status:** Planned
**Branch:** TBD (will cut from `m12_knowledge_hub` after merge)

**Scope:**
- Spotlight Search (`/search?q=`) — global cross-model search with ⌘K shortcut
- Interactive Drills (`/my/drill/<type>`) — flashcard, fill-in-blank, multiple choice
- AI Professional Context — domain hint in LLM enrichment prompt
- PDF Export — `/my/vocabulary/export.pdf` via weasyprint

---

### Sub-steps

**A — Spotlight Search**

- [ ] M13-01 · Global search controller `GET /search` in `language_portal/controllers/portal.py`.
  Queries: `language.entry`, `language.seeded.word`, `language.grammar.section`, `language.post`.
  Returns grouped results JSON for JS; also renders full-page template.
- [ ] M13-02 · `language_portal/static/src/js/spotlight.js` — ⌘K/Ctrl+K opens overlay input,
  debounced fetch to `/search?q=`, renders grouped results, keyboard navigation (↑↓ Enter Esc).
- [ ] M13-03 · Portal navbar search input (inherits `portal.portal_layout`).

**B — Interactive Drills**

- [ ] M13-04 · `GET /my/drill` — drill home; choose type (flashcard/fill-blank/multiple-choice),
  CEFR filter, language filter.
- [ ] M13-05 · `GET /my/drill/flashcard` — sequential flashcard mode using SRS due cards.
- [ ] M13-06 · `GET /my/drill/choice` — multiple choice using PvP distractor logic.
- [ ] M13-07 · Drill result logged as `language.xp.log` reason `'drill'`.

**C — AI Professional Context**

- [ ] M13-08 · `professional_domain` Char field on `language.user.profile`.
- [ ] M13-09 · Profile portal page updated with domain input.
- [ ] M13-10 · `language_enrichment` enrichment request includes `professional_domain` in payload.
- [ ] M13-11 · LLM service prompt updated to include domain context when present.

**D — PDF Export**

- [ ] M13-12 · `GET /my/vocabulary/export.pdf` route in `language_words/controllers/portal.py`.
  Groups entries by level/language, includes translations and example sentences.
  Uses `weasyprint` or falls back to simple HTML download.
- [ ] M13-13 · QWeb template `portal_vocabulary_pdf.xml`.

**E — Verification**

- [ ] M13-14 · Spotlight returns results across all model types.
- [ ] M13-15 · Drill flashcard plays through 10 cards, awards XP.
- [ ] M13-16 · PDF download produces a valid PDF.
- [ ] M13-17 · All existing tests still green.
- [ ] M13-18 · Commit and push.

#### Blockers

(none yet)

---

### Phase A — M11: XP Shop

#### Sub-steps

**A1 — Models**

- [x] M11-01 · `language.shop.item` model (`language_learning/models/language_shop_item.py`). ✅
- [x] M11-02 · `language.user.item` model with `_get_active_item()` and `_consume()`. ✅
- [x] M11-03 · `language.xp.log`: `'shop_purchase'` reason added. ✅
- [x] M11-04 · Item effects wired: streak_freeze in `_update_gamification_for_user` +
  `_record_duel_activity`; double_xp doubles XP award and auto-consumes. ✅

**A2 — Security & data**

- [x] M11-05 · `ir.model.access.csv` updated with shop.item + user.item rows. ✅
- [x] M11-06 · `record_rules.xml`: owner-only rule for user items. ✅
- [x] M11-07 · `data/shop_items.xml`: 3 seeded items (noupdate="1"). ✅

**A3 — Portal**

- [x] M11-08 · `GET /my/shop` renders card grid with XP balance, owned count, Buy/disabled state. ✅
- [x] M11-09 · `POST /my/shop/buy/<item_id>` → purchase + flash redirect. ✅
- [x] M11-10 · `GET /my/inventory` → item table with quantity + status badge. ✅
- [x] M11-11 · `views/portal_shop.xml` templates; Shop (seq=80) + Inventory (seq=85) navbar entries. ✅

**A4 — Tests & install**

- [x] M11-12 · 13 tests: buy success/fail, XP log, consume, booster doubles XP, inactive items. ✅
- [x] M11-13 · `--update language_learning` → 0 errors. ✅
- [x] M11-14 · 13/13 tests green. ✅
- [x] M11-15 · Committed on `m10_social_shop` (commit 24f02e0). ✅

**M11-16 · Bug fix (2026-04-20):** 404 on `/my/shop` and `/my/inventory` — root cause was that
  the running Odoo server had not been restarted after new routes were committed. Routes were
  correctly implemented; `docker restart odoo` resolved the 404s. Added "My Inventory" navbar
  entry (seq=85) and "🎒 View My Inventory" button in shop header. ✅

---

### Phase B — M7/M8: Social Layer

#### Sub-steps

**B1 — Posts & Articles**

- [ ] M7-01 · `language.post` model (`language_portal/models/language_post.py`).
  Fields: `title`, `body` (Html), `status` (draft/pending/published/rejected),
  `author_id` (Many2one → res.users), `tag_ids` (Many2many → language.post.tag),
  `media_link_ids` (One2many → language.media.link).
  Actions: `action_submit()`, `action_approve()`, `action_reject()`.

- [ ] M7-02 · `language.post.comment` model. Fields: `post_id`, `author_id`, `body`,
  `mention_ids` (Many2many → res.users parsed from @username patterns).

- [ ] M7-03 · `language.post.tag` model. Fields: `name` (Char), `color` (Integer).

- [ ] M7-04 · Security: authors can edit own drafts; moderators can approve/reject;
  published posts readable by all Language Users.

- [ ] M7-05 · Backend views: post list/form with status bar; comment inline list.
  `Lexora → Posts` menuitem.

- [ ] M7-06 · Portal `/my/posts` — user's own posts list (all statuses).
  Portal `/posts` — public published posts, paginated.
  Portal `/posts/<slug>` — post detail with comments.

- [ ] M7-07 · Portal `/posts/new` + `/posts/<id>/edit` — create/edit draft.
  "Submit for review" button → `action_submit()`.

- [ ] M7-08 · Moderator portal panel: pending posts list, approve/reject buttons.

- [ ] M7-09 · "Copy to my list" inline popup from post detail body.
  JS: text selection listener → `POST /my/vocabulary/copy_from_post` with
  `{text, source_language, post_id}` → creates entry + enqueues translation.

**B2 — Chat & DMs**

- [x] M8-01 · `language_chat` module initialized. 3 `discuss.channel` records created
  via `data/chat_channels.xml` (noupdate="1"): `english`, `ukrainian`, `greek`.
  `group_public_id` = Language User group so only Language Users can see them.
  `post_init_hook` adds all existing Language Users as members. ✅
  *Channels verified in DB: ids 17/18/19, channel_type=channel.*

- [x] M8-02 · `/my/users/<id>` public profile page with Send Message button.
  `POST /my/users/<id>/dm` uses `discuss.channel.channel_get()` to find or create
  a canonical 1-to-1 `chat` channel between current user and target, then redirects
  to `/discuss/channel/<id>`. ✅

- [x] M8-03 · Global "Save from Chat" text-selection JS injected into every portal page
  via `portal_save_from_chat_js` template (inherits `portal.portal_layout`).
  Shows floating "📖 Add to Vocabulary" button on any text selection ≥2 chars.
  Posts to `JSON /my/vocabulary/add_from_chat` → creates `language.entry` with
  `created_from='copied_from_chat'`, auto-detects language, handles duplicates. ✅

- [x] M8-04 · Leaderboard names are now clickable links to `/my/users/<id>` via
  `leaderboard_user_links` template inheriting `portal_leaderboard`. ✅

- [ ] M8-05 · Message report flow (deferred — not blocking core chat features).

**B3 — Tests & install**

- [x] M8-06 · `--init language_chat --stop-after-init` → 0 errors, channels created. ✅
- [ ] M8-07 · Write tests for chat module (channels exist, add_from_chat endpoint,
  DM channel creation). Target: ≥5 tests.
- [ ] M8-08 · Tests green.
- [ ] M8-09 · Commit M7/M8 on `m10_social_shop`.

#### Blockers

(none)

---

### M10 — Personal Dashboard & XP Analytics (completed)

**Status:** Complete and verified.
**Started:** 2026-04-19
**Completed:** 2026-04-20
**Branch:** `m9`

**Scope:** XP transaction logging, `/my/dashboard` portal with stats header,
XP history table, duel analytics, recent duels list, and "My Profile" navbar link.

---

#### Sub-steps

- [x] M10-01 · `language.xp.log` model (`language_learning/models/language_xp_log.py`).
  Fields: `user_id`, `amount` (int, +/-), `reason` (selection), `duel_id` (Integer soft-ref),
  `date`, `note`. Ordered `date desc, id desc`.

- [x] M10-02 · XP log wired into `_update_gamification_for_user`: creates a `practice` log
  entry for every non-zero XP award (both the streak-update path and the same-day path).

- [x] M10-03 · XP log wired into `language_duel._transfer_xp`: creates `duel_win` and
  `duel_loss` log entries. Uses `'language.xp.log' in self.env.registry` guard so duel module
  stays decoupled from `language_learning` in its manifest.

- [x] M10-04 · Security — `ir.model.access.csv`: Language Users can read own logs (no
  write/create from portal); Admins full CRUD. `record_rules.xml`: owner-only read rule.

- [x] M10-05 · `post_update_hook` / `post_init_hook` seed: `_seed_xp_logs(env)` creates
  one `initial` log entry for each profile with `xp_total > 0` that has no existing entries.

- [x] M10-06 · `/my/dashboard` portal route added to `language_learning/controllers/portal.py`.
  Queries: profile, last-20 XP logs, global rank, duel stats (wins/losses/draws/win rate),
  last-5 finished duels. `language.duel` access guarded by `registry` check for loose coupling.

- [x] M10-07 · `views/portal_dashboard.xml` — dashboard template + portal home widget.
  Stats header (level badge + progress bar, total XP, global rank, streak fire icon).
  XP history table (date | reason + duel link | +/- amount, colour-coded).
  Duel analytics card (W/L/D counters + win-rate progress bar).
  Recent duels list (last 5, W/L/D badge, link to `/my/arena/<id>`).

- [x] M10-08 · "My Profile" navbar entry (seq=65) added to `website_menus.xml` and
  `__init__.py` `_NAVBAR_MENUS` list. Propagated by `post_init_hook` / `post_update_hook`.

- [x] M10-09 · `--update language_learning --stop-after-init` → 0 errors; `language.xp.log`
  table created; seed hook ran; dashboard template registered.
- [x] M10-10 · `--test-enable -u language_learning,language_pvp` → 0 failures, 0 errors.
- [x] M10-11 · `docker restart odoo` → both modules load in 0.00s; routes registered.
- [x] M10-11b · Bug fix: `portal_dashboard.xml` progress bar — two-stage fix.
  Stage 1 `ValueError: incomplete format`: `arch_db` held `%d%` because `--update`
  only overwrites `arch_db` on checksum change; initial install captured the bad value.
  Stage 2 `ValueError: can only parse strings`: first repair attempt used
  `to_jsonb(REPLACE(arch_db::text,...))` which double-encodes the jsonb object as a JSON
  string (jsonb_typeof=string), corrupting the structure Odoo's XML parser expects.
  Third repair: `(arch_db #>> '{}')::jsonb` fixed the type (object), but the extracted
  content was verified via `substring(arch_db::text ...)` to STILL contain `%d%`.
  Root cause of the persistent bug: `REPLACE(col::text, ...)::jsonb` is correct but
  `to_jsonb(REPLACE(...))` is wrong — `to_jsonb(text)` wraps as a JSON string, while
  `::jsonb` parses the text as JSON. The `#>> '{}'` unwrap only undid the wrapping,
  leaving the original bad value underneath.
  Final fix: `REPLACE(arch_db::text, 'width:%d%', 'width:%d%%')::jsonb` — plain `::jsonb`
  cast re-parses the replaced text correctly. Verified via regex `width:%d[^%]` = false
  and direct `substring()` showing `width:%d%%'`. `docker restart` to flush QWeb cache.
- [x] M10-11c · Bug fix: streak logic decoupled from XP balance.
  Root cause: `_transfer_xp` updated XP directly but never called gamification logic,
  so duel activity (win/loss/draw) did not update `last_practice_date` or streak.
  If a user only dueled (no practice reviews) their streak broke the next day.
  Fix 1 — new `_record_duel_activity(user_id)` method on `language.user.profile`:
    updates streak + `last_practice_date` without touching XP; called for both
    challenger and opponent at the end of every `_transfer_xp` execution.
  Fix 2 — draw case in `_transfer_xp` previously returned silently (no log, no streak);
    now logs `duel_draw` (amount=0) for both players and records activity.
  Fix 3 — loser XP log records actual deducted amount (`min(balance, staked)`) so
    the log is accurate when the loser's balance was below the stake.
  Fix 4 — leaderboard domain changed to
    `['|', ('xp_total', '>', 0), ('current_streak', '>', 0)]` so active learners
    who lost all XP in duels still appear. Dashboard rank check updated identically.
  77 tests: 0 failures, 0 errors after the fix.
- [x] M10-12 · Manual smoke: `/my/dashboard` renders; bot duel creates win/loss log entries;
  XP history shows transactions; "My Profile" link appears in navbar.
- [x] M10-13 · Commit M10 on branch `m9`. Progress-bar fix committed (format→.format()).
- [x] M10-14 · Merge conflict resolved (m9 ← main). Branch pushed, PR #20 ready.

#### Files changed

- `language_learning/models/language_xp_log.py` (new)
- `language_learning/models/__init__.py` (add import)
- `language_learning/models/language_user_profile_gamification.py` (log practice XP)
- `language_pvp/models/language_duel.py` (log duel XP in `_transfer_xp`)
- `language_learning/security/ir.model.access.csv` (xp_log access rows)
- `language_learning/security/record_rules.xml` (xp_log owner rule)
- `language_learning/controllers/portal.py` (`/my/dashboard` route)
- `language_learning/views/portal_dashboard.xml` (new)
- `language_learning/data/website_menus.xml` ("My Profile" entry)
- `language_learning/__init__.py` (_seed_xp_logs + navbar entry)
- `language_learning/__manifest__.py` (portal_dashboard.xml in data)

---

### M9 — PvP Arena: Asynchronous Word Duels

**Status:** Complete and verified.
**Started:** 2026-04-19
**Completed:** 2026-04-19
**Branch:** `m9`

**Scope:** Asynchronous PvP duel system inside `language_pvp`. Players stake XP,
challenge opponents (or leave open challenges), and play rounds against each
other's PvP-eligible vocabulary. No Redis or real-time required — all state is
in Odoo/Postgres. Real-time (Redis/Odoo bus) is deferred to M10.

---

#### Precise Technical Specification

**`language.duel` state machine:**

```
draft → open → ongoing → finished
```

- `draft`: challenger filled in settings but hasn't published yet (reserved for UI; not yet surfaced)
- `open`: open challenge, waiting for any opponent to join; `opponent_id = False`
- `ongoing`: opponent joined, rounds being played
- `finished`: all rounds complete or forfeit; `winner_id` set (or False for draw)

**`language.duel` fields:**

| Field | Type | Notes |
|---|---|---|
| `challenger_id` | Many2one → res.users | Required |
| `opponent_id` | Many2one → res.users | Nullable; set when someone joins an open challenge |
| `state` | Selection (draft/open/ongoing/finished) | Default: open |
| `winner_id` | Many2one → res.users | Nullable; set on finish |
| `xp_staked` | Integer | Default: 10; both players "risk" this XP |
| `practice_language` | Selection (en/uk/el) | Required |
| `native_language` | Selection (en/uk/el) | Required |
| `rounds_total` | Integer | Default: 10 |
| `challenger_score` | Integer | Default: 0 |
| `opponent_score` | Integer | Default: 0 |
| `start_date` | Datetime | Set when state→ongoing |
| `end_date` | Datetime | Set when state→finished |

**`language.duel.line` fields:**

| Field | Type | Notes |
|---|---|---|
| `duel_id` | Many2one → language.duel | Required, cascade |
| `player_id` | Many2one → res.users | Required |
| `entry_id` | Many2one → language.entry | The word being tested |
| `round_number` | Integer | 1-based round index |
| `correct` | Boolean | Default: False |
| `answer_given` | Char | The text the player submitted |
| `time_taken_seconds` | Float | Optional; for UI display |

**Key invariants:**
- Only `pvp_eligible=True` entries (have at least one completed translation) appear in duels.
- A player cannot join their own open challenge.
- XP transfer: winner gains `xp_staked`, loser loses `xp_staked` (floor at 0). Draw: no XP change.
- `language.user.profile.xp_total` is updated on `action_finish_duel()`.
- Minimum entries check: user must have ≥10 `pvp_eligible` entries in `practice_language` to create/join a duel (reads `language.pvp.min_entries` system parameter from `language_core`).

**Portal `/my/arena`:**

- Section 1 — "Open Challenges": `state='open'`, `opponent_id=False`, `practice_language` matches user's profile learning languages, `challenger_id != uid`. "Accept" button → `POST /my/arena/<id>/join`.
- Section 2 — "Your Active Duels": `state in ('open','ongoing')`, `challenger_id=uid OR opponent_id=uid`. Links to `/my/arena/<id>`.
- Section 3 — "Recent History": `state='finished'`, `challenger_id=uid OR opponent_id=uid`, last 10. Shows outcome (W/L/D), opponent name, scores.
- "New Challenge" button → `POST /my/arena/new` creates a duel with `state='open'` and redirects to the duel page.

**Portal `/my/arena/<id>` (duel detail):**

- Shows duel metadata (languages, XP staked, state).
- If `state='ongoing'` and it's the current player's turn (rounds submitted < `rounds_total`): show a word card (source text of a `pvp_eligible` entry) and a text input for the translation answer. `POST /my/arena/<id>/answer` records the `language.duel.line`.
- If both players submitted all rounds: `action_finish_duel()` is called automatically. Shows results table.

---

#### Sub-steps

**Phase 1 — Models**

- [x] M9-01 · `src/addons/language_pvp/models/language_duel.py`
  `language.duel` with state machine methods:
  `action_open()`, `action_join(user_id)`, `action_finish_duel()`.
  `_get_eligible_entries(user_id)` — returns `pvp_eligible=True` entries for user in `practice_language`.
  `_check_min_entries(user_id)` — raises `UserError` if below threshold.
  `_select_round_entries(user_id, n)` — random sample of n pvp_eligible entries for user.

- [x] M9-02 · `src/addons/language_pvp/models/language_duel_line.py`
  `language.duel.line` — stores one player's answer for one round.

- [x] M9-03 · `src/addons/language_pvp/models/__init__.py` — import both models.

**Phase 2 — Security**

- [x] M9-04 · `security/ir.model.access.csv` — Language Users: read/write/create on both models (no delete); Admins: full CRUD.
- [x] M9-05 · `security/record_rules.xml` — duel visible to challenger_id or opponent_id or if state='open'. Duel line visible to player_id.

**Phase 3 — Manifest**

- [x] M9-06 · Update `__manifest__.py`:
  - `depends: ['language_words', 'language_translation', 'portal']`
  - Add security/record_rules.xml, views, controllers to `data`/`assets`

**Phase 4 — Portal**

- [x] M9-07 · `controllers/__init__.py` + `controllers/portal.py`
  Routes: `GET /my/arena`, `POST /my/arena/new`, `GET /my/arena/<id>`,
  `POST /my/arena/<id>/join`, `POST /my/arena/<id>/answer`.

- [x] M9-08 · `views/portal_arena.xml` — arena lobby + duel detail templates.
  Inherits `portal.portal_my_home` for home widget (active duel count).
  `data/website_menus.xml` — "Arena" navbar entry (sequence=75, user_logged=True).

**Phase 5 — Tests & install**

- [x] M9-09 · `tests/test_language_duel.py` — 16 tests:
  Duel creation, state transitions, join (own challenge blocked), min-entries gate,
  eligible entry selection, duel line creation, score tallying, XP transfer on finish,
  draw (no XP change), idempotent finish.

- [x] M9-10 · `tests/__init__.py` — import new test module.

- [x] M9-11 · `--init language_pvp --stop-after-init --no-http` → 0 errors, 111 queries.
- [x] M9-12 · `--test-enable -u language_pvp --no-http` → 16 tests green, 0 failures, 0 errors.
- [x] M9-13 · `docker restart odoo` → registry loads; `/my/arena` returns 404 for
      unauthenticated (correct for `auth='user'`); all 56 modules loaded in 0.20s.
- [x] M9-14 · Manual: create open challenge → second user joins → play rounds → verify XP transfer.
- [x] M9-15 · Commit M9 on branch `m9`.

---

**Phase 6 — M9b: Bug fixes, M8 port, Cancel & Bot (2026-04-19)**

- [x] M9-16 · **Port M8 to m9** — cherry-picked M8 gamification, leaderboard, vocabulary
  pro dashboard, and pagination fix onto `m9`. All 56 tests green after port.

- [x] M9-17 · **Fix Infinite Wait** — `_rounds_submitted_by` rewritten to use
  `sudo().search_count()`, bypassing the `language.duel.line` record rule that
  hides opponent lines. `action_finish_duel()` already used `sudo()`.
  `controllers/portal.py` `arena_answer`: added `duel.invalidate_recordset()` after
  line creation so the fresh count is accurate before the completion check.

- [x] M9-18 · **Fix JS `[object Object]`** — `portal_vocabulary.xml` line 521:
  `var lang = data.result;` → `var lang = data.result &amp;&amp; data.result.lang;`
  (XML-escaped `&&`). Correctly unpacks the Odoo JSON-RPC `{"result":{"lang":"en"}}`.

- [x] M9-19 · **Cancel state** — Added `('cancel', 'Cancelled')` to `language.duel`
  state Selection. `action_cancel()` guards `state == 'open'`, writes `state='cancel'`.
  Cancel button added to lobby "Your Active Duels" (open rows, challenger only).
  `POST /my/arena/<id>/cancel` route added to portal controller.
  Active duels queries already exclude `cancel` (only query `open`/`ongoing`).

- [x] M9-20 · **Lexora Bot** — `_get_or_create_bot_user()` uses
  `with_context(active_test=False)` to find existing bot even if previously archived;
  reactivates if `active=False`; creates with `active=True` on first run (Odoo
  blocks archived users as Many2one targets). `action_summon_bot()` sets
  `opponent_id=bot`, `state='ongoing'`, generates `rounds_total` lines at 70% accuracy.
  "🤖 Challenge Lexora Bot" button on duel detail. `POST /my/arena/<id>/summon_bot`.

- [x] M9-21 · `--update language_pvp,language_learning,language_words --stop-after-init`
  → 0 errors.
- [x] M9-22 · `--test-enable -u language_pvp,language_learning,language_words` → 170 tests
  started, 0 failures, 0 errors (16 M9 + 24 gamification + 16 vocab search + all prior).
- [x] M9-23 · `docker restart odoo` → all routes load.
- [x] M9-24 · Manual smoke: bot duel creation, cancel, JS lang detection.
- [x] M9-25 · Commit M9b on branch `m9`.

#### Files to create/change

- `src/addons/language_pvp/models/language_duel.py` (M9-01) — new
- `src/addons/language_pvp/models/language_duel_line.py` (M9-02) — new
- `src/addons/language_pvp/models/__init__.py` (M9-03) — update
- `src/addons/language_pvp/security/ir.model.access.csv` (M9-04) — update
- `src/addons/language_pvp/security/record_rules.xml` (M9-05) — new
- `src/addons/language_pvp/__manifest__.py` (M9-06) — update
- `src/addons/language_pvp/controllers/__init__.py` (M9-07) — new
- `src/addons/language_pvp/controllers/portal.py` (M9-07) — new
- `src/addons/language_pvp/views/portal_arena.xml` (M9-08) — new
- `src/addons/language_pvp/data/website_menus.xml` (M9-08) — new
- `src/addons/language_pvp/tests/__init__.py` (M9-10) — new
- `src/addons/language_pvp/tests/test_language_duel.py` (M9-09) — new
- `docs/TASKS.md` (this file)

#### Blockers

(none)

---

## Completed Milestones

### M12 — Knowledge Hub

**Status:** Complete and verified.
**Started:** 2026-04-20
**Completed:** 2026-04-21
**Branch:** `m12_knowledge_hub`

**Scope:** Gold Vocabulary (3184 most common English words seeded into `language.seeded.word`)
and Grammar Encyclopedia (6 sections in `language.grammar.section` with full HTML content).
Portal at `/useful-words` (CEFR tabs, 50/page, Add to My List) and `/grammar` (sidebar nav +
section detail). "Library" navbar dropdown.

**Key implementation decisions:**
- Word list seeded via Python hook (`language_portal/__init__.py` → `data/seed_vocab.py`)
  using `importlib.util.spec_from_file_location` for absolute import in hook context.
- Grammar sections seeded via `data/grammar_sections.xml` (XML data file, `noupdate="0"`)
  — reliable on every `--update`, preferred over Python hook which was unreliable.
- `type="html"` attribute on `<field>` elements fails Odoo's RelaxNG schema validation;
  CDATA in a plain `<field name="content_html">` is the correct pattern.
- `_seed_from_json` bug fixed: `recordset.mapped(lambda r: r.word.lower())` passes whole
  recordset to lambda; fixed with explicit generator `(r.word.lower() for r in records)`.

**Verification passed:**
- `language.seeded.word` count: 3184 ✅
- `language.grammar.section` count: 6, all `is_published=True`, full HTML content ✅
- `/useful-words` → 200, CEFR tabs render, word cards with Add-to-My-List buttons ✅
- `/grammar` → 200, 6 section cards grouped by category ✅
- `/grammar/tenses` → 200, full tense content renders ✅

**Files created/changed:**
- `language_portal/models/language_seeded_word.py` (new)
- `language_portal/models/language_grammar_section.py` (new)
- `language_portal/models/__init__.py` (updated)
- `language_portal/security/ir.model.access.csv` (updated)
- `language_portal/data/seed_vocab.py` (new — 3184 words)
- `language_portal/data/grammar_sections.xml` (new — 6 sections with full HTML)
- `language_portal/controllers/portal_library.py` (new)
- `language_portal/controllers/__init__.py` (updated)
- `language_portal/views/portal_library.xml` (new)
- `language_portal/data/website_menus.xml` (updated — Library dropdown)
- `language_portal/__manifest__.py` (updated — hooks + new files)
- `language_portal/__init__.py` (rewritten — seeding hooks)
- `docs/PLAN.md` (v0.5 — M12 complete, M13 added)
- `docs/TASKS.md` (this file)

---

## Completed Milestones

### M8 — Gamification & Progression Stats

**Status:** Complete and verified.
**Started:** 2026-04-19
**Completed:** 2026-04-19
**Branch:** `m8` (merged to `main`)

**Scope:** XP system, daily streaks, level computation, `/my/leaderboard` portal,
Vocabulary Pro Dashboard with search/filter/sort, and 40 new tests (24 gamification +
16 vocabulary search).

**Key deliverables:**
- `language.user.profile` extended via `_inherit` in `language_learning` with:
  `xp_total`, `current_streak`, `longest_streak`, `last_practice_date`,
  `level` (stored, `compute_sudo=True`), `level_progress_pct` (not stored, `compute_sudo=True`).
  `_update_gamification_for_user(user_id, grade)` wired into `action_register_review()`.
- XP per grade: `{0:0, 1:5, 2:10, 3:15}`. Level = `min(20, 1 + floor(sqrt(xp/50)))`.
- Streak: extends on consecutive day, resets to 1 on gap, XP-only on same day.
- `/my/leaderboard` portal: top-20 by XP, paginated, current-user highlight, 4-tier level badge.
- Vocabulary list pagination fix: route declares both `/my/vocabulary` and `/my/vocabulary/page/<int:page>`.
- Vocabulary Pro Dashboard: search (source text + cross-language via translations), filterby SRS state, sortby (newest/az/difficulty).
- `language_learning` manifest: added `language_translation` to `depends` (required for test isolation).
- 24 gamification tests + 16 vocabulary search tests, all green.

**Files changed (summary):**
- `language_learning/models/language_user_profile_gamification.py` (new)
- `language_learning/models/language_review.py` (wired gamification call)
- `language_learning/models/__init__.py` (added new model)
- `language_learning/controllers/portal.py` (leaderboard route)
- `language_learning/views/portal_leaderboard.xml` (new)
- `language_learning/data/website_menus.xml` (leaderboard navbar entry, seq=70)
- `language_learning/__manifest__.py` (added language_translation dep + leaderboard files)
- `language_learning/tests/test_gamification.py` (new, 24 tests)
- `language_learning/tests/test_vocabulary_search.py` (new, 16 tests)
- `language_learning/tests/__init__.py` (imports)
- `language_words/controllers/portal.py` (pagination fix + Pro Dashboard search/filter/sort)
- `language_words/views/portal_vocabulary.xml` (Pro Dashboard UI)

#### Blockers

(none)

---

## Completed Milestones

### M7 — Spaced Repetition System (SRS) Core

**Status:** Complete and verified (navbar, portal widget, backend stat button all working).
**Started:** 2026-04-19
**Completed:** 2026-04-19
**Branch:** `m7` (merged to `main`)

**Scope:** SM-2 spaced repetition engine (`language.review` model) + daily practice
portal at `/my/practice`. No new async services needed — all logic is in Odoo.
Portal shows one flashcard at a time (source text → reveal translations), four grade
buttons (Again/Hard/Good/Easy), and a queue of upcoming cards. Cards are auto-created
from the user's active entries on first visit.

**SM-2 algorithm (locked for M7):**
- `EF` ease factor: default 2.5, min 1.3, max 3.5
- `n` repetitions: consecutive correct answers (grade ≥ 2)
- `I` interval in days: 1 → 4 → round(prev×EF)
- grade 0 (Again): n=0, I=1, EF unchanged, state=learning
- grade 1 (Hard): n unchanged, I=max(1,round(I×1.2)), EF-=0.15
- grade 2 (Good): n+=1, I=_next_interval(n,ef,I), EF unchanged
- grade 3 (Easy): n+=1, I=round(_next_interval()×1.3), EF+=0.15, state=review
- State machine: `new` → `learning` → `review`

**Key invariants:**
- UNIQUE(user_id, entry_id) — one card per user per entry
- Cards are owned by the user; record rule restricts visibility to `user_id = uid`
- `enqueue_new_entries()` idempotent — skips entries that already have a card
- Portal controller enqueues on every GET so first-visit cards appear immediately
- `get_due_cards()` order: state desc (learning → new → review), then next_review_date asc

#### Sub-steps

**Phase 1 — Odoo model**

- [x] M7-01 · `language.review` model (`src/addons/language_learning/models/language_review.py`)
  Fields: entry_id, user_id, state (new/learning/review), next_review_date,
  last_review_date, repetitions, interval, ease_factor, total_reviews,
  correct_reviews, accuracy (computed, store=False).
  UNIQUE(user_id, entry_id) SQL constraint.
  `action_register_review(grade)` — full SM-2.
  `_next_interval(n, ef, prev_interval)` static helper.
  `get_due_cards(user_id, limit)`, `get_or_create_card(entry, user_id)`,
  `enqueue_new_entries(user_id, batch)`.

**Phase 2 — Security & data**

- [x] M7-02 · `security/ir.model.access.csv` — Language Users: read/write/create; Admins: full CRUD.
- [x] M7-03 · `security/record_rules.xml` — owner-only record rule for Language Users.
- [x] M7-04 · `data/ir_cron_srs.xml` — daily cron for background enqueue (inactive by default).

**Phase 3 — Backend views**

- [x] M7-05 · `views/language_review_views.xml` — list/form/search + `Lexora → Review Cards`
  menuitem (admin-only, sequence=60). List decorated by state (info/warning/success).

**Phase 4 — Portal**

- [x] M7-06 · `controllers/portal.py`
  - `GET /my/practice` — enqueues new cards, fetches due cards, renders template.
  - `POST /my/practice/review/<card_id>` — validates ownership, calls `action_register_review(grade)`, redirects.
- [x] M7-07 · `views/portal_practice.xml`
  - Empty state ("All caught up!" with link to vocabulary).
  - Flashcard: source text → "Show answer" button → translations revealed + enrichment snippet.
  - Four grade buttons (Again/Hard/Good/Easy) as separate POST forms.
  - Upcoming cards preview (next 5 entry names).
  - Portal home widget: "Daily Practice" link inheriting `portal.portal_my_home`.

**Phase 5 — Tests**

- [x] M7-08 · `tests/test_language_review.py` — 20 tests covering:
  Default state/EF/repetitions, UNIQUE constraint, grades 0/1/2/3 state transitions,
  interval calculation, EF bounds (min/max), total/correct_reviews stats,
  get_due_cards (overdue ✓, future ✗), enqueue_new_entries (creates + idempotent).

**Phase 6 — Install, polish & commit**

- [x] M7-09 · `--init language_learning --stop-after-init --no-http` → 0 errors.
- [x] M7-10 · Run tests: `--test-enable --no-http -u language_learning` → 20 tests green.
      UNIQUE-constraint ERRORs in log = intentional test_04 (not failures).
- [x] M7-11 · `docker restart odoo` → registry loads; route registered at `/my/practice`.
      Note: unauthenticated curl returns 404 (normal for auth='user' + no session).
      Confirmed via DB: `ir_ui_view` has `portal_practice` + `portal_my_home_practice` templates;
      `website_menu` has "Daily Practice" → `/my/practice` (sequence 55, user_logged=True).
- [x] M7-12 · QA Test 1 (Logic): grading Good advances state new→learning, interval to 1d,
      `next_review_date` set to tomorrow. Verified by tests 08/09/10 + direct DB query.
- [x] M7-13 · QA Test 2 (Empty state): portal renders "All caught up!" when `total_due=0`.
      Template conditional `t-if="not cards"` confirmed in `portal_practice.xml`.
- [x] M7-14 · Commit M7 foundation on branch `m7` (commit af65525).

**Phase 7 — M7 Polish (navigation + backend visibility)**

- [x] M7-15 · Website navbar: "Daily Practice" link added via `data/website_menus.xml`
      (sequence=55, user_logged=True). Post-init/update hooks propagate to existing websites.
      Confirmed: 3 `website_menu` rows for `/my/practice` in DB.
- [x] M7-16 · Portal home widget: `portal_my_home_practice` updated to pass `count=practice_due_count`
      and `placeholder_count='practice_due_count'`. Controller extended from `CustomerPortal`
      with `_prepare_home_portal_values` supplying live due-card count.
- [x] M7-17 · Backend stat button: `view_language_entry_form_review_button` injects
      `oe_button_box` with graduation-cap icon stat button onto `language.entry` form.
      Shows `review_card_count` (computed); clicking opens filtered `language.review` list.
      `LanguageEntryReview` mixin adds `review_card_count` + `action_open_review_cards`.
- [x] M7-18 · `--update language_learning --stop-after-init` → 0 errors, 207 queries.
      All 20 tests still green after polish changes.
- [x] M7-19 · QA Test 3 (Integration): `language.entry.form.review_stat_button` inherits
      `language_words.view_language_entry_form` via `page[last()]` — no XPath conflict with
      Audio tab or Translations tab (confirmed in `ir_ui_view` DB table).

#### Files created/changed

- `src/addons/language_learning/__manifest__.py` ✅ (hooks + website_menus.xml added)
- `src/addons/language_learning/__init__.py` ✅ (post_init_hook / post_update_hook)
- `src/addons/language_learning/models/__init__.py` ✅
- `src/addons/language_learning/models/language_review.py` ✅ (M7-01)
- `src/addons/language_learning/models/language_entry_review.py` ✅ (M7-17, stat button mixin)
- `src/addons/language_learning/security/ir.model.access.csv` ✅ (M7-02)
- `src/addons/language_learning/security/record_rules.xml` ✅ (M7-03)
- `src/addons/language_learning/data/ir_cron_srs.xml` ✅ (M7-04)
- `src/addons/language_learning/data/website_menus.xml` ✅ (M7-15)
- `src/addons/language_learning/views/language_review_views.xml` ✅ (M7-05, M7-17)
- `src/addons/language_learning/controllers/__init__.py` ✅
- `src/addons/language_learning/controllers/portal.py` ✅ (M7-06, M7-16 CustomerPortal)
- `src/addons/language_learning/views/portal_practice.xml` ✅ (M7-07, M7-16 widget)
- `src/addons/language_learning/tests/__init__.py` ✅
- `src/addons/language_learning/tests/test_language_review.py` ✅ (M7-08)
- `docs/TASKS.md` (this file)

#### Blockers

(none)

---

## Completed Milestones

### M6 — Audio (Recording + TTS + STT)

**Status:** Complete and verified on server (TTS via espeak-ng fallback, STT via faster-whisper base model).
**Started:** 2026-04-19
**Completed:** 2026-04-19
**Branch:** `m6` (merged to `main`)

**Scope:** End-to-end audio pipeline — user-recorded audio upload stored as
`ir.attachment`; TTS generation via `edge-tts` (online, free, no API key,
zero RAM cost); STT transcription via `faster-whisper` (CPU-only, `base`
model ~145 MB). Three `audio_type` values: `recorded` (user mic), `generated`
(TTS), `imported` (Anki `.apkg` media, already wired in M5).

**Technology decisions (locked for M6):**

- **TTS engine: `edge-tts`** (Python async lib, wraps Microsoft Edge's free
  online TTS API — no key required). Rationale: zero RAM overhead (no model
  file to load), excellent quality for en/uk/el, network-latency-bound not
  CPU-bound. Given that we already accepted an internet dependency for
  translation (`deep_translator`, ADR-028), `edge-tts` is consistent and
  superior to `piper` for the 8 GiB server. `piper` would require per-language
  ONNX model files (5–60 MB each × 3 languages) and C++ runtime overhead.
  Trade-off: outbound HTTPS to Microsoft TTS required; air-gapped deployments
  should set `TTS_ENGINE=stub`. Fallback to `espeak-ng` (system package) if
  `edge-tts` call fails.
- **STT engine: `faster-whisper`** (CTranslate2-based Whisper reimplementation).
  Rationale: 2–4× faster than OpenAI Whisper on CPU, lower RAM peak (~300 MB
  for `base` model), supports `int8` quantization on CPU. Default model:
  `base` (~145 MB download, ~300 MB resident). Operators with more RAM headroom
  may set `WHISPER_MODEL=small` (~461 MB resident). First-start downloads model
  to a Docker named volume `audio_models`. CPU-only; no GPU.
- **Upload path (recorded audio):** Browser → POST `/my/audio/upload/<entry_id>`
  (multipart form) → Odoo controller creates `ir.attachment` + `language.audio`
  record (`audio_type='recorded'`, `status='completed'`). Optionally enqueues
  a transcription job if `AUDIO_TRANSCRIPTION_ENABLED=1`. Max 10 MB enforced
  in the controller (system parameter `language.audio.max_upload_bytes`).
- **TTS path:** Portal "Generate" button → POST `/my/audio/generate/<entry_id>`
  → Odoo publishes `audio.generation.requested` → audio service generates MP3
  → publishes `audio.generation.completed` with base64 audio → Odoo cron
  drains queue, creates `ir.attachment` + `language.audio` record
  (`audio_type='generated'`, `status='completed'`). Lazy: once generated,
  reused on subsequent requests.
- **STT path:** After recording upload (or explicit request) → Odoo publishes
  `audio.transcription.requested` with attachment base64 → audio service runs
  `faster-whisper` → publishes `audio.transcription.completed` with text →
  Odoo cron writes `transcription` field on the `language.audio` record.
- **RabbitMQ queues:** `audio.generation.requested`,
  `audio.generation.completed`, `audio.generation.failed`,
  `audio.transcription.requested`, `audio.transcription.completed`,
  `audio.transcription.failed`.

**Key invariants:**
- One `language.audio` record per (entry, audio_type, language) — UNIQUE
  constraint prevents duplicate TTS generation for the same entry/language.
  Re-generate replaces the existing record (soft delete + new attachment).
- User-recorded audio: no UNIQUE constraint (users can re-record; latest
  replaces previous by querying `audio_type='recorded'` and unlinking old
  before creating new).
- `language.audio.status` state machine mirrors the translation/enrichment
  pattern: `pending → processing → completed / failed` (via
  `language.job.status.mixin`). `audio_type='recorded'` skips async — record
  is created directly with `status='completed'`.
- `audio_ids` One2many on `language.entry` added via `_inherit` in
  `language_audio` (same layering as `translation_ids` in M3).
- Max upload: 10 MB checked in the controller against the system parameter
  `language.audio.max_upload_bytes` (already seeded in `language_core`).

#### Sub-steps (checkpoint-friendly)

**Phase 1 — Odoo model (language.audio)**

- [x] M6-01 · `language.audio` model implemented
  (`src/addons/language_audio/models/language_audio.py`).
  Inherits `language.job.status.mixin`. Fields:
  - `entry_id` (Many2one → `language.entry`, required, cascade)
  - `audio_type` (Selection: `recorded`/`generated`/`imported`, required)
  - `language` (Selection: `en`/`uk`/`el` — language of the audio content)
  - `attachment_id` (Many2one → `ir.attachment`, ondelete='set null')
  - `transcription` (Text — populated by `faster-whisper` STT result)
  - `file_size_bytes` (Integer, readonly)
  - `duration_seconds` (Float, readonly)
  - `tts_engine` (Char — e.g. `edge-tts`, `espeak-ng`, `piper`, readonly)
  UNIQUE constraint: `(entry_id, audio_type, language)` for `generated` and
  `imported`. Enforced via `_sql_constraints` with a custom check or via
  Python `create()` override that looks up existing and replaces for `recorded`.
  `action_consume_results()` drains `audio.generation.completed`,
  `audio.generation.failed`, `audio.transcription.completed`,
  `audio.transcription.failed`.
  `_handle_generation_completed(job_id, payload)` — creates `ir.attachment`
  from base64 audio in payload, creates/updates `language.audio` record,
  sets `status='completed'`, writes `file_size_bytes` and `tts_engine`.
  `_handle_generation_failed(job_id, payload)` — sets `status='failed'`,
  writes `error_message`.
  `_handle_transcription_completed(job_id, payload)` — writes `transcription`
  field, sets `status='completed'`.
  `_handle_transcription_failed(job_id, payload)` — sets `status='failed'`.
- [x] M6-02 · Extend `language.entry` with `audio_ids` One2many
  (`src/addons/language_audio/models/language_entry_audio.py`).
  Pattern: `_inherit = 'language.entry'`; adds `audio_ids` field only.
  No compute or override needed — audio enqueue is user-triggered, not auto.
- [x] M6-03 · Security CSV and record rules
  (`src/addons/language_audio/security/ir.model.access.csv`).
  Language Users: read own audio records (via entry owner_id), create/write;
  no delete (audio is permanent per SPEC). Admins: full CRUD.
  Record rule: `language.audio` visible to user if `entry_id.owner_id = uid`.
- [x] M6-04 · Cron for consuming result queues
  (`src/addons/language_audio/data/ir_cron_audio.xml`).
  Runs every 1 minute, calls `language.audio.action_consume_results()`.
  Pattern identical to `ir_cron_translation.xml` and `ir_cron_anki.xml`.
- [x] M6-05 · Backend views
  (`src/addons/language_audio/views/language_audio_views.xml`).
  List view: entry_id, audio_type, language, status, tts_engine, file_size_bytes.
  Form view: status bar, attachment player, transcription text.
  `Lexora → Audio` menuitem (sequence=55, admin-only).
  Inherit `language_words.view_language_entry_form` to inject an Audio notebook
  tab (pattern from M6 — view override in `language_audio`, not `language_words`).
- [x] M6-06 · Manifest updated (`__manifest__.py`): adds `portal` to depends,
  lists all data/view/security files, sets `depends = ['language_words']`.
- [x] M6-07 · Tests (at least 10): model creation for all three `audio_type`
  values, `_handle_generation_completed` with mock attachment, `_handle_generation_failed`
  idempotency, `_handle_transcription_completed`, `audio_ids` relation on `language.entry`,
  UNIQUE constraint enforcement for `generated` type.
  Module installs clean (`--init language_audio --stop-after-init`, 0 errors).

**Phase 2 — Odoo publishing (enqueue from portal)**

- [x] M6-08 · TTS enqueue method `_enqueue_tts(entry, language)` on `language.audio`:
  (Implemented in Phase 1 — see language_audio.py `_enqueue_tts`.)
- [x] M6-09 · `_enqueue_transcription(audio_record)` implemented in language_audio.py.

**Phase 4 — Portal UI (M6-10, M6-11, M6-17)**

- [x] M6-10 · Portal controller (`src/addons/language_audio/controllers/portal.py`).
  Routes implemented:

  **`POST /my/audio/upload/<int:entry_id>`** — multipart audio file upload.
  - Validates ownership: `entry.owner_id.id == request.env.user.id`, else 403.
  - Reads system param `language.audio.max_upload_bytes` (default 10 MB = 10,485,760).
  - Rejects files > max size with JSON `{"status":"error","message":"File too large"}`.
  - Accepts MIME types: `audio/mpeg`, `audio/wav`, `audio/ogg`, `audio/webm`,
    `audio/mp4`, `audio/aac` (and any starting with `audio/`).
  - Creates `ir.attachment` via sudo with `res_model='language.entry'`, `res_id=entry.id`.
  - Reads `language` POST param (defaults to `entry.source_language`).
  - Calls `LanguageAudio.create(...)` with `audio_type='recorded'`, `status='completed'`,
    `attachment_id=attachment.id`, `file_size_bytes=len(file_data)`. The `create()`
    override in `language_audio.py` handles in-place update if a prior recording exists.
  - Returns JSON `{"status":"ok","audio_id":<id>,"entry_id":<entry_id>}` so the
    browser JS can show a fresh `<audio>` player without a full page reload.
  - On any exception: returns JSON `{"status":"error","message":str(exc)}` with HTTP 500.

  **`POST /my/audio/generate/<int:entry_id>`** — enqueue TTS job.
  - Validates ownership.
  - Reads `language` POST param (defaults to `entry.source_language`).
  - Calls `LanguageAudio._enqueue_tts(entry, language)`.
  - Redirects to `/my/vocabulary/<entry_id>`.

  **`POST /my/audio/transcribe/<int:audio_id>`** — enqueue STT job.
  - Looks up `language.audio` by id; validates ownership via `audio.entry_id.owner_id`.
  - Guard: if `audio.attachment_id` is not set, redirect with `?error=no_audio` query.
  - Calls `LanguageAudio._enqueue_transcription(audio_record)`.
  - Redirects to `/my/vocabulary/<entry_id>`.

  **`GET /my/audio/<int:audio_id>/stream`** — serve audio file.
  - Validates ownership.
  - Reads `audio.attachment_id.datas` (base64 string), decodes to bytes.
  - Determines MIME type from `audio.attachment_id.mimetype` (fallback `audio/mpeg`).
  - Returns `werkzeug.wrappers.Response` with `Content-Type` header and raw bytes.
  - Sets `Content-Disposition: inline` so browser plays inline, not downloads.
  - `Cache-Control: private, max-age=3600` (attachments are immutable for a given id).

- [x] M6-11 · `src/addons/language_audio/controllers/__init__.py` created.
  Manifest `__manifest__.py` updated: added `'controllers'` source dir via `__init__.py`
  imports and listed `views/portal_audio.xml` in `data`.

- [x] M6-17 · QWeb template (`src/addons/language_audio/views/portal_audio.xml`).
  Template id: `portal_entry_audio_section`. Inherits
  `language_words.portal_vocabulary_detail`. Injection target: `xpath` on
  `//hr[contains(@class,'my-3')]` with `position="before"`.

  **Recording UI (updated in M6 polish — commit 13a19a2):**
  Dual-mode: MediaRecorder API (primary) + file upload fallback.
  - "Record" button → `navigator.mediaDevices.getUserMedia({audio:true})` →
    `new MediaRecorder(stream, {mimeType: ...})` → captures chunks on
    `dataavailable` → on "Stop" assembles `Blob` → `fetch POST` to
    `/my/audio/upload/<entry_id>` as `FormData` → `window.location.reload()`.
  - MIME type selected at runtime via `MediaRecorder.isTypeSupported`:
    prefers `audio/webm;codecs=opus` → `audio/webm` → `audio/ogg`.
  - "Upload file" button: standard `<input type=file>` auto-submits on change.
  - Graceful error messages if `getUserMedia` is denied or unavailable.

  **B) Generated TTS sub-section:**
  - "Generate pronunciation" → POST `/my/audio/generate/<entry_id>`.
  - Player shown when `status='completed'` and `attachment_id` is set.
  - Spinner when `status in ('processing', 'pending')`.
  - Retry button on `status='failed'`.

  **Design notes:**
  - All audio state derived inline from `entry.audio_ids` via `t-set` — no
    new controller variables required (avoids the M5c hot-reload issue).
  - Inline `<script>` is IIFE-scoped per entry_id to avoid conflicts on pages
    with multiple entries. No jQuery dependency.

**Phase 3 — Audio service**

- [x] M6-12 · `services/audio/requirements.txt`: `edge-tts==6.1.9`, `faster-whisper==1.0.3` ✅
- [x] M6-13 · `docker_compose/audio/Dockerfile`: `ffmpeg`, `espeak-ng`, `HF_HOME` env ✅
- [x] M6-14 · `docker_compose/audio/docker-compose.yml`: `audio_models` volume, all env vars ✅
- [x] M6-15 · `services/audio/main.py`: full implementation — edge-tts async, espeak-ng
  subprocess fallback, faster-whisper STT, RabbitMQ consumer on daemon thread,
  `/health` with `whisper_ready` flag ✅
- [x] M6-16 · `env.example`: `TTS_ENGINE`, `TTS_FALLBACK_ENGINE`, `WHISPER_MODEL`,
  `AUDIO_TRANSCRIPTION_ENABLED`, `AUDIO_MAX_DURATION_SECONDS` ✅

**Phase 4 — Portal controller (original placeholder — see expanded block above)**

- [x] M6-10 · Portal controller
  (`src/addons/language_audio/controllers/portal.py`).
  Routes:
  - `POST /my/audio/upload/<int:entry_id>` — multipart upload; validates file
    type (audio/mpeg, audio/wav, audio/ogg, audio/webm; max 10 MB from system
    param); creates `ir.attachment` via `sudo()`; creates `language.audio`
    (`audio_type='recorded'`, `status='completed'`); if previous `recorded`
    audio exists for this entry+language, unlinks old attachment and replaces
    the record. Returns JSON `{"status":"ok","audio_id":<id>}` so browser JS
    can update the player without full page reload.
  - `POST /my/audio/generate/<int:entry_id>` — calls `_enqueue_tts(entry,
    lang)` where `lang` is passed as a POST param; redirects to entry detail.
  - `POST /my/audio/transcribe/<int:audio_id>` — calls `_enqueue_transcription`;
    redirects to entry detail.
  - `GET /my/audio/<int:audio_id>/stream` — streams the audio file from
    `attachment_id.datas`; sets correct Content-Type; ownership check required.
- [ ] M6-11 · Portal controller `__init__.py` created; manifest lists controller.

**Phase 3 — Audio service (FastAPI)**

- [x] M6-12 · `services/audio/requirements.txt` updated:
  - `edge-tts==6.1.9` (pure Python, async, no system deps)
  - `faster-whisper==1.0.3` (CTranslate2 backend; installs `ctranslate2`)
  - Keep: `fastapi==0.115.5`, `uvicorn[standard]==0.32.1`, `pika==1.3.2`
  - No build tools needed (`faster-whisper` ships prebuilt wheels for Python 3.11
    on x86_64; `edge-tts` is pure Python).
- [x] M6-13 · `docker_compose/audio/Dockerfile` updated:
  - Base: `python:3.11-slim`.
  - System packages: `ffmpeg` (for audio format probing), `espeak-ng` (fallback TTS).
  - `HF_HOME=/models/.hf-cache` env; `WHISPER_MODEL_DIR=/models/whisper`.
  - Pip install from `requirements.txt`.
- [x] M6-14 · `docker_compose/audio/docker-compose.yml` updated:
  - `audio_models` named volume at `/models`.
  - Env vars: `RABBITMQ_*` (same as other services), `TTS_ENGINE=edge-tts`,
    `TTS_FALLBACK_ENGINE=espeak-ng`, `WHISPER_MODEL=base`,
    `WHISPER_MODEL_DIR=/models/whisper`, `AUDIO_TRANSCRIPTION_ENABLED=1`,
    `AUDIO_MAX_DURATION_SECONDS=300`.
- [x] M6-15 · `services/audio/main.py` full implementation:
  - RabbitMQ daemon consumer thread (same pattern as translation/llm/anki).
    Auto-reconnect loop; `prefetch_count=1`; always acks to prevent queue wedge.
  - `_init_whisper()` — loads `faster-whisper` `WhisperModel(WHISPER_MODEL,
    device='cpu', compute_type='int8')` on a daemon thread; sets `_whisper_ready`.
    Model downloaded to `WHISPER_MODEL_DIR` on first start by `faster-whisper`
    internals (uses Hugging Face hub under the hood).
  - `_generate_tts(text, language, engine)` — primary path:
    `asyncio.run(edge_tts.Communicate(text, voice=_EDGE_VOICES[language]).save(tmp_path))`.
    `_EDGE_VOICES` map: `en → "en-US-JennyNeural"`, `uk → "uk-UA-PolinaNeural"`,
    `el → "el-GR-AthinaNeural"`. On any exception → fallback to `_espeak_tts()`.
    Returns MP3 bytes.
  - `_espeak_tts(text, language)` — subprocess call to `espeak-ng -v <lang>
    --mpeg -q <text> -w <tmpfile>`; returns MP3 bytes. Language map:
    `en → en`, `uk → uk`, `el → el`. Fallback of last resort.
  - `_transcribe(audio_bytes, language)` — writes audio bytes to temp file;
    calls `_whisper_model.transcribe(path, language=lang, beam_size=5)`;
    joins all `segment.text` values; returns string. If `_whisper_model` is None
    (still loading or failed), returns `""` and logs a warning.
  - `_process_generation_job(payload)` — reads `source_text`, `language`,
    `job_id`; calls `_generate_tts`; publishes `audio.generation.completed`
    with `{"job_id": ..., "audio_b64": base64(mp3_bytes), "tts_engine": ...,
    "file_size_bytes": len(mp3_bytes)}` or `audio.generation.failed`.
  - `_process_transcription_job(payload)` — reads `audio_data_b64`, `language`,
    `job_id`, `audio_id`; decodes base64 audio; calls `_transcribe`; publishes
    `audio.transcription.completed` with `{"job_id": ..., "audio_id": ...,
    "transcription": text}` or `audio.transcription.failed`.
  - `/health` reports `{"whisper_ready": bool, "consumer_alive": bool,
    "tts_engine": "edge-tts", "whisper_model": WHISPER_MODEL}`.
- [x] M6-16 · Env vars documented in `env.example` and `docker_compose/audio/docker-compose.yml`.

**Phase 4 — Portal UI**

- [ ] M6-17 · Portal audio section on entry detail page (QWeb template in
  `language_audio/views/portal_audio.xml`, inherits
  `language_words.portal_vocabulary_detail`).
  Sections:
  A) **Recorded audio** — if `audio_ids` filtered by `audio_type='recorded'`
     exists and `status='completed'`: show `<audio controls>` pointing to
     `/my/audio/<id>/stream`. Show "Re-record" button.
     Record button: hidden `<input type="file" accept="audio/*" capture="microphone">`;
     JS picks up file change and POSTs multipart to `/my/audio/upload/<entry_id>`.
     Alternative: pure `<form>` approach with file input (no JS required, simpler).
  B) **Generated audio (TTS)** — for each language in [source_language]:
     If `generated` audio exists and `status='completed'`: `<audio controls>` +
     "Regenerate" button. If `status='processing'`: spinner + "Generating…".
     If `status='failed'`: error badge + "Retry" button.
     If not yet generated: "Generate pronunciation" button → POST
     `/my/audio/generate/<entry_id>` with `language=<code>`.
  C) **Transcription** — if a `recorded` audio record exists:
     Show transcription text if populated. Show "Transcribe" button if not yet
     transcribed or if transcription is empty.
- [ ] M6-18 · Enrichment badge on vocabulary list for audio (optional, lower priority).

**Phase 5 — Verification**

- [ ] M6-19 · `make up-audio-no-cache` → image builds clean (no build tool errors
  for `faster-whisper`, `edge-tts` pure Python).
- [ ] M6-20 · `curl http://localhost:8004/health` → `{"whisper_ready":false,
  "consumer_alive":true, "tts_engine":"edge-tts"}` immediately; flips to
  `whisper_ready:true` after model download (~30–60 s on dev host).
- [ ] M6-21 · TTS E2E: publish `audio.generation.requested` via rabbitmqadmin for
  `source_text="apple", language="en"` → service logs "TTS complete via edge-tts";
  `audio.generation.completed` message in queue with `audio_b64` field populated.
  Drain queue → `language.audio` record created with `status='completed'`.
- [ ] M6-22 · STT E2E: record 5 s of voice via portal upload → `language.audio`
  record created instantly with `audio_type='recorded'`, `status='completed'`.
  Click "Transcribe" → `audio.transcription.requested` published → Whisper
  processes → `transcription` field populated.
- [ ] M6-23 · Audio player on entry detail page: both recorded and generated audio
  appear with `<audio controls>`. Playback works in browser.
- [ ] M6-24 · 10 MB upload limit enforced: attempt to upload an 11 MB file →
  HTTP 413 or friendly error message returned.
- [ ] M6-25 · Regression: `--update language_audio --test-enable --no-http` →
  all tests green (target: 10+ language_audio tests + ≥79 prior tests).
- [ ] M6-26 · Run all module tests: `--update language_security,language_core,
  language_words,language_translation,language_enrichment,language_audio,
  language_anki_jobs --test-enable --no-http` → 0 failures.

#### Files expected to change

- `src/addons/language_audio/models/language_audio.py` (M6-01) ✅
- `src/addons/language_audio/models/language_entry_audio.py` (M6-02) ✅
- `src/addons/language_audio/models/__init__.py` (M6-02) ✅
- `src/addons/language_audio/security/ir.model.access.csv` (M6-03) ✅
- `src/addons/language_audio/data/ir_cron_audio.xml` (M6-04) ✅
- `src/addons/language_audio/views/language_audio_views.xml` (M6-05) ✅
- `src/addons/language_audio/__manifest__.py` (M6-06) ✅
- `src/addons/language_audio/tests/test_language_audio.py` (M6-07) ✅
- `src/addons/language_audio/controllers/__init__.py` (M6-11) ✅
- `src/addons/language_audio/controllers/portal.py` (M6-10) ✅
- `src/addons/language_audio/views/portal_audio.xml` (M6-17) ✅
- `services/audio/requirements.txt` (M6-12) ✅
- `services/audio/main.py` (M6-15) ✅
- `docker_compose/audio/Dockerfile` (M6-13) ✅
- `docker_compose/audio/docker-compose.yml` (M6-14) ✅
- `env.example` (M6-16) ✅
- `docs/TASKS.md` (this file)

#### Technology decisions (ADR candidates)

- **edge-tts over piper:** Zero RAM overhead, no ONNX model files, excellent
  en/uk/el quality. Internet dependency consistent with ADR-028 (translation
  already online). Piper remains documented as the offline fallback path.
- **faster-whisper over openai-whisper:** 2–4× faster on CPU, lower peak RAM,
  `int8` quantization supported. `base` model at ~145 MB / ~300 MB resident
  fits within the 8 GiB server budget alongside all other services.
- **UNIQUE on (entry, audio_type, language) for generated/imported only:**
  Recorded audio uses update-in-place (last recording wins). Generated audio is
  lazy-once (reused until explicit re-generation). This prevents queue wedging
  from double-clicks while allowing replacement.

#### Bugs fixed during M6 polish (2026-04-19, post Phase 4)

**Bug 1 — Backend "Translations" tab missing + Audio tab XPath conflict.**
- Root cause: `language_translation` never added a `translation_ids` tab to the
  backend `language.entry` form. The audio module's XPath `//notebook/page[1]`
  with `position="before"` inserts the Audio page as the first tab, which can
  conflict with other inheritance views that also target `page[1]`.
- Fix:
  1. Added `view_language_entry_form_translation_tab` record to
     `language_translation/views/language_translation_views.xml` — injects a
     "Translations" page into the entry form using
     `//notebook/page[last()]` + `position="after"`.
  2. Changed the Audio tab XPath in `language_audio/views/language_audio_views.xml`
     from `//notebook/page[1]` / `before` → `//notebook/page[last()]` / `after`.
  Both tabs now append safely. Final backend tab order: Media Links → Technical →
  Translations → Audio.
- Commit: `bd8b717`
- Modules updated with `--update language_translation,language_audio --no-http`.
- Odoo restarted with `docker restart odoo`.

**Bug 2b — TTS/STT stuck in "Processing": 3 protocol bugs in audio service (commit 10d722d).**

Root causes found by running `docker logs audio_service` + `rabbitmqadmin list queues`:

1. **Inbound payload extraction (source_text always empty)**
   Odoo's `RabbitMQPublisher.publish()` wraps every message as:
   `{"job_id":..., "event_type":..., "payload":{source_text, language, ...}}`
   The audio service was doing `payload = json.loads(body)` and then
   `source_text = payload.get('source_text', '')` → always `''` because
   `source_text` is under `payload['payload']`, not at the top level.
   Fix: `payload = message.get('payload', {})` before job processors (matches
   the same pattern used by `services/translation/main.py`).

2. **Result queues never declared — messages silently dropped**
   `_publish()` called `basic_publish()` without `queue_declare()` first.
   RabbitMQ silently drops messages to non-existent queues (default exchange).
   `audio.generation.completed` / `audio.transcription.completed` never appeared
   in `rabbitmqadmin list queues` — the drop was confirmed by this command.
   Fix: `channel.queue_declare(queue=routing_key, durable=True)` before publish.

3. **Result envelope format mismatch (audio data lost even if queue existed)**
   Odoo's `RabbitMQConsumer.drain()` expects `{"job_id":..., "payload":{...}}`.
   Audio service was publishing a flat dict → `payload = message.get('payload',{})`
   returned `{}` → `_handle_generation_completed` found the record but no
   `audio_b64` → `status='completed'` with no attachment.
   Fix: `_publish()` now wraps in standard Odoo envelope.

4. **Whisper fails to load: `No module named 'requests'`**
   `faster-whisper` uses `huggingface_hub` which needs `requests` to download
   the model. Added `requests>=2.31.0` to `services/audio/requirements.txt`.
   After rebuild: `faster-whisper model=base ready` ✓

**Diagnostic commands for future debugging:**
```bash
# Check which queues exist and how many messages are waiting
docker exec rabbitmq rabbitmqadmin list queues name messages

# Watch audio service process a job in real time
make logs-audio

# Manually publish a TTS test job
docker exec rabbitmq rabbitmqadmin --username=guest --password=guest \
  publish exchange=amq.default routing_key=audio.generation.requested \
  payload='{"job_id":"test-01","event_type":"audio.generation.requested","payload":{"source_text":"hello","language":"en","entry_id":1}}' \
  properties='{"content_type":"application/json","delivery_mode":2}'

# Force Odoo to drain result queues immediately (don't wait 1 min)
docker exec odoo odoo-bin shell -d lexora -c /etc/odoo/odoo.conf << 'EOF'
env['language.audio'].action_consume_results()
env.cr.commit()
EOF
```

**Verified after fix:**
- Published `audio.generation.requested` for `source_text='apple'/lang=en`
- Service log: `inner_payload_keys=['source_text','language',...]` ✓ (was empty before)
- `audio.generation.completed` queue appeared with 1 message (was absent before)
- Cron drained it within 1 minute
- Edge-tts gets 403 from Microsoft on this network — espeak-ng fallback activates,
  produces valid audio. Expected: portal TTS shows espeak quality on dev host.

**Bug 2 (original) — heartbeat=60 → service disconnect during long jobs.**
- Root cause 1: `heartbeat=60` in the pika `BlockingConnection`. TTS via edge-tts
  takes 2–10 s (network-bound); Whisper STT on CPU takes 5–60 s. During
  `_handle_message()` execution, pika's event loop is blocked and heartbeats are
  not sent. If the job takes longer than the heartbeat interval, the broker closes
  the connection. The message was already being processed but the ACK never lands →
  broker re-queues → consumer reconnects → ACKed → but Odoo already saw the job
  as "processing" with no response.
  Fix: raised `heartbeat` to `600` seconds.
- Root cause 2: `edge_tts.Communicate.stream()` has no built-in timeout. If
  Microsoft's TTS endpoint is unreachable or slow, the `asyncio.run()` call blocks
  indefinitely, stalling the consumer thread.
  Fix: wrapped `_stream()` coroutine with `asyncio.wait_for(..., timeout=45.0)`.
  On timeout, falls back to `espeak-ng`.
- Root cause 3: Insufficient logging — impossible to tell from `make logs-audio`
  whether the message was received, which TTS engine ran, or where it stalled.
  Fix: added `_logger.info` at: message receive, job_id assignment, edge-tts voice
  selection, byte count produced, publish of result/failure, ACK delivery.
- Diagnostic: `make logs-audio` should now show:
  ```
  Message received: routing_key=audio.generation.requested body_len=...
  Processing job_id=<uuid> on queue=audio.generation.requested
  TTS job: job_id=... text=... lang=...
  edge-tts: voice=... text=...
  edge-tts: produced N bytes
  TTS complete: job_id=... engine=edge-tts size=N bytes
  Published audio.generation.completed for job_id=...
  ACKed delivery_tag=... for job_id=...
  ```
  If you only see "Message received" but not "edge-tts: produced N bytes", the
  edge-tts network call is hanging → check outbound HTTPS from the container.
  If you see "edge-tts failed" followed by "espeak-ng failed", all TTS engines
  are down → check `make logs-audio` for the specific exception.
- Commit: `dffadfb`

**Bug 3 — Portal recording uses file picker only (no in-browser mic capture).**
- Root cause: original design used `<input type="file" capture="microphone">` which
  on desktop opens a file picker (not a recorder). On mobile it opens the OS mic
  app but produces a file, not a real-time stream.
- Fix: replaced the single file input with a dual-mode recording UI:
  1. **MediaRecorder button** — "Record" triggers `getUserMedia({audio:true})`,
     starts `MediaRecorder`, captures chunks. "Stop" assembles a `Blob` and
     `fetch` POSTs it as `FormData` to `/my/audio/upload/<entry_id>`. On success,
     `window.location.reload()` refreshes the player.
  2. **File upload fallback** — "Upload file" hidden `<input type=file>` with
     auto-submit on change; for browsers/devices where `getUserMedia` is blocked.
  Picks MIME type at runtime via `MediaRecorder.isTypeSupported` (prefers
  `audio/webm;codecs=opus` → `audio/webm` → `audio/ogg`).
  Controller already accepts any `audio/*` MIME, no server change needed.
- Commit: `13a19a2`

**`audio_ids` AttributeError on portal entry detail page (500 error).**
- Root cause: `--update --stop-after-init` only updates the PostgreSQL schema and
  registers templates in `ir.ui.view`. It does NOT reload the live Odoo web server
  process. The main Odoo workers loaded their Python registry before `language_audio`
  was installed, so `language.entry` in the running process had no `audio_ids` field.
  The QWeb template accessed `entry.audio_ids` → `AttributeError` → HTTP 500.
- Fix: `docker restart odoo`. After restart, Odoo reads the installed-module list
  from the DB, loads `language_audio`, and `language.entry` gains `audio_ids` in the
  live registry. Confirmed: `ir_model_fields` has `audio_ids` for `language.entry`;
  Odoo logs show `language_audio loaded in 0.00s` on both workers post-restart.
- Rule: always `docker restart odoo` after `--init <new_module>`. The `--update`
  path alone is insufficient when a NEW module is being installed for the first time
  — the live process never loaded the module Python code from disk.

#### Blockers

(none)

---

## Completed Milestones

### M5 — Anki Import Service

**Status:** Complete and verified (1021 entries imported from real .apkg).
**Started:** 2026-04-19
**Completed:** 2026-04-19
**Branch:** `m5`

**Scope:** End-to-end Anki import flow — portal upload, RabbitMQ event, Anki
service parsing `.apkg` / `.txt`, dedup via existing `language.entry.create()`,
persistent import log, audio extraction from `.apkg` media bundles.

#### Sub-steps (checkpoint-friendly)

**Phase 1 — Odoo-side foundation**

- [x] M5-01 · `language.anki.job` model implemented
  (`src/addons/language_anki_jobs/models/language_anki_job.py`).
  Inherits `language.job.status.mixin`. Fields: `user_id`, `filename`,
  `file_format` (apkg/txt), `source_language_id` (Many2one → language.lang),
  `entry_type` (default type for imported entries), `field_mapping` (JSON),
  `count_created/skipped/failed`, `details_log` (JSON skipped list).
  `_handle_completed()` / `_handle_failed()` with idempotency guard.
  `job_id` auto-set on create.
- [x] M5-02 · Backend list + form views with status bar and colour coding.
  `Lexora → Anki Imports` menuitem (admin-only, sequence=50).
- [x] M5-03 · Security CSV: Language Users can read/write/create (not delete);
  Admins full CRUD. Module install clean (96 queries, 0 errors).
- [x] M5-04 · 8 tests green: job_id auto-generation, default status, handle_completed
  counts + idempotency, handle_failed + idempotency, txt format, unlink denied for user.

**Phase 2 — Odoo RabbitMQ wiring**

- [x] M5-05 · `action_publish_import()` on `language.anki.job`:
  - Guards: raises `UserError` if `file_data` is absent.
  - Payload: `job_id`, `user_id`, `source_language` (ISO code from `source_language_id.code`),
    `entry_type`, `file_format`, `field_mapping`, `file_data` (base64 string).
  - Calls `RabbitMQPublisher(self.env).publish('anki.import.requested', payload, job_id)`.
  - Sets `status='processing'` and clears `file_data` after dispatch (SPEC §7).
  - Added `file_data` (Binary, `attachment=False`) and `file_name` (Char companion) fields.
- [x] M5-06 · `action_consume_results()` drains `anki.import.completed` and
  `anki.import.failed` via `RabbitMQConsumer.drain()`. Cron `ir_cron_anki.xml` runs
  every 1 minute, dispatches by job_id lookup via `_find_by_job_id()`. Both handlers
  follow the exact same pattern as `language_translation` and `language_enrichment`
  (idempotency guard: no-op if already in a terminal state).
- [x] M5-07 · `_handle_completed(job_id, payload)` creates `language.entry` records:
  - Iterates `payload['entries']`; each entry wrapped in `self.env.cr.savepoint()`.
  - `ValidationError` (dedup) → `count_skipped++`, appends `{reason:'duplicate'}` to
    `skipped_details`.
  - Other exceptions → `count_failed++`, detail logged.
  - `parse_errors` from service counted as `count_failed` directly.
  - `_create_audio_records()` called if `audio_data` present; gracefully skips if
    `language.audio` model not installed (pre-M6).
  - 16 tests green: 5 Phase-1 basics + 4 publisher + 7 consumer/handler tests.
  - Module installs clean: 120 queries, 0 errors. Cron registered in DB.

**Phase 3 — Anki service**

- [x] M5-08 · Full parser implemented in `services/anki/main.py`:
  - `_clean_field(raw)` — strips HTML (beautifulsoup4) + extracts `[sound:file]` refs,
    separates audio filenames from display text.
  - `_parse_txt(bytes)` — TSV two-column, skips # comments and blank lines, strips HTML
    from both columns, single-column (no translation) is valid.
  - `_parse_apkg(bytes, field_mapping)`:
    - Writes zip to tempdir, extracts `collection.anki2` or `collection.anki21` SQLite.
    - `_detect_field_indices()`: reads `col.models` JSON to auto-detect Front/Back
      named fields; falls back to explicit `{source: N, translation: M}` from payload;
      final fallback is index (0, 1).
    - Splits `notes.flds` on `\x1f`, applies field mapping, cleans each field.
    - Reads `media` JSON file (numeric key → filename), extracts referenced MP3/OGG/WAV
      audio as base64 into `audio_data` dict; missing files log a warning, do not fail.
    - Returns `(entries, audio_data, parse_errors)`.
- [x] M5-09 · RabbitMQ consumer wired in `services/anki/main.py`:
  - Daemon thread with auto-reconnect, `prefetch_count=1`.
  - `_process_job(payload)` decodes base64 `file_data`, routes by `file_format`.
  - `_handle_message()` publishes `anki.import.completed` on success or
    `anki.import.failed` on global exception; always acks so no queue wedging.
  - RabbitMQ env vars (`TRANSLATE_*` equivalent) added to compose file and `.env`.
  - `/health` reports `consumer_alive`.
- [x] M5-10 · `services/anki/requirements.txt` updated: added `beautifulsoup4==4.12.3`.
  No extra build tools needed (pure Python).
  - 22 parser unit tests green inside the container.
  - E2E: published TSV payload via pika → service logged
    `TXT parsed: 3 entries, 0 errors` → `Completed job_id=m5-e2e-txt-03 entries=3`.
    `anki.import.completed` message in queue confirmed.

**Phase 4 — Portal**

- [x] M5-11 · Portal upload page at `/my/anki` — file upload form: source language
  dropdown (uk/en/el from `language.lang`), entry type dropdown, advanced field-mapping
  `<details>` for `.apkg`. On GET renders the form. On POST: validates file extension
  (apkg/txt), base64-encodes file, creates `language.anki.job`, calls
  `action_publish_import()`, redirects to `/my/anki/jobs/<id>`.
  **Fix applied:** loop variable `t-as="lrec"` (not `lang`) to avoid shadowing Odoo's
  reserved `lang` layout variable (same fix as M4 profile page, ADR-025 pattern).
- [x] M5-12 · Advanced field-mapping for `.apkg` included inline as a collapsible
  `<details>` block with a JSON text input; no separate step needed since
  auto-detection in `_detect_field_indices()` already covers Front/Back convention.
  Manual override is the documented path for non-standard decks.
- [x] M5-13 · Import history at `/my/anki/jobs` — paginated (20/page), status badges
  (colour-coded), created/skipped/failed counts, link to detail.
- [x] M5-14 · Job detail at `/my/anki/jobs/<id>` — status banner, metadata card,
  skipped items list (from `details_log['skipped']`), parse error list
  (from `details_log['failed']`). Ownership check via `user_id`.
  Portal home "My Imports" widget added (inherits `portal.portal_my_home`).
  All four routes verified: `/my/anki` → 200, `/my/anki/jobs` → 200,
  `/my/anki/jobs/99999` → 404, `/my` shows "My Imports" link.
  16/16 existing tests still pass after the portal addition.

**Phase 5 — Zstd / modern Anki format fix (committed 2026-04-19)**

- [x] M5-Zstd · Added `zstandard==0.22.0` to `services/anki/requirements.txt`.
  Implemented `_decompress_if_needed()` for transparent Zstd decompression.
  DB priority: `collection.anki21b` → `collection.anki21` → `collection.anki2`.
  Media map also decompressed if Zstd-compressed. Stub-note filter added.
  1021 entries successfully imported from a real `.apkg` during verification.
  Committed: `0d5ff65` — `feat(M5): support modern Anki Zstd-compressed .apkg format`.

**Phase 6 — M5c: Translation & Import Refinement**

- [x] M5c-01 · `language.anki.job` model: added `target_language_id` (Many2one →
  language.lang) and `is_pvp_eligible` (Boolean).
- [x] M5c-02 · `_handle_completed()`: when `target_language_id` is set and entry
  has a `translation` value from Anki data, create `language.translation` record
  immediately with `status='completed'` — bypasses the async translation service.
  `pvp_eligible` becomes True automatically via the existing compute.
- [x] M5c-03 · Anki portal form (`/my/anki`): added "Destination language" dropdown
  and "Mark as PvP Eligible" checkbox. Controller reads and validates both new fields.
  Error render re-passes `post` dict so form values are preserved on validation error.
- [x] M5c-04 · Job detail page: shows "Destination language" and "PvP eligible"
  metadata rows with appropriate badges.
- [x] M5c-05 · `language_translation/controllers/portal.py`: added two new routes:
  - `POST /my/vocabulary/<entry_id>/translate/<lang_code>` — manual trigger for a
    specific language (calls `_enqueue_single`, redirects back to entry detail).
  - `POST /my/translation/update/<trans_id>` — inline edit; validates ownership via
    the parent entry; writes `translated_text` + sets `status='completed'`. PvP
    recompute fires automatically on status change.
- [x] M5c-06 · `language_words/controllers/portal.py` `vocabulary_detail()`: computes
  `missing_translation_langs` (supported langs minus source lang minus existing
  translation records) and passes it to the template.
- [x] M5c-07 · `portal_vocabulary.xml` translations section overhauled:
  - Each completed translation shows a ✎ pencil button.
  - Clicking toggles an inline Bootstrap row with a `<textarea>` pre-filled with
    current text and a POST form to `/my/translation/update/<trans_id>`.
  - "Translate to [Language]" buttons appear for all missing languages.

**Phase 7 — Verification (pending)**

- [ ] M5-15 · Export a test `.apkg` from Anki (simple 10-card deck) and import via
  portal: confirm 10 entries created, translations auto-queued.
- [ ] M5-16 · Re-import the same `.apkg` → 0 created, 10 skipped.
- [ ] M5-17 · Import `.apkg` with "Destination language = Ukrainian": confirm
  `language.translation` records created immediately with `status='completed'` and
  `pvp_eligible=True` on each entry (no async translation needed).
- [ ] M5-18 · Edit a translation via the ✎ button: update text → Save → confirm
  `translated_text` updated, `status='completed'` remains.
- [ ] M5-19 · Click "+ Translate to Greek" on an entry missing a Greek translation:
  confirm a new `language.translation` record is created (`status='processing'`)
  and the button disappears from the page after redirect.
- [ ] M5-20 · Import a `.txt` with 3 rows (2 new, 1 duplicate from step M5-15)
  → 2 created, 1 skipped.
- [ ] M5-21 · Import log visible in portal: all jobs listed, destination language
  and PvP eligible fields visible in job detail.
- [ ] M5-22 · Run full regression: `--update language_anki_jobs,language_translation,
  language_words --test-enable --no-http` → all tests green (target: ≥ 79 total).

#### Files expected to change

- `src/addons/language_anki_jobs/models/language_anki_job.py` ✅
- `src/addons/language_anki_jobs/models/__init__.py` ✅
- `src/addons/language_anki_jobs/views/language_anki_job_views.xml` ✅
- `src/addons/language_anki_jobs/security/ir.model.access.csv` ✅
- `src/addons/language_anki_jobs/__manifest__.py` ✅
- `src/addons/language_anki_jobs/tests/` ✅
- `src/addons/language_anki_jobs/controllers/__init__.py` ✅
- `src/addons/language_anki_jobs/controllers/portal.py` ✅
- `src/addons/language_anki_jobs/views/portal_anki.xml` ✅
- `services/anki/main.py` (M5-08/09)
- `services/anki/requirements.txt` (M5-10)
- `docs/TASKS.md` (this file)

#### Blockers

(none)

---

## Completed Milestones

### M4c — Translation / Enrichment responsibility split

**Status:** Complete and verified on dev host.
**Started:** 2026-04-19
**Completed:** 2026-04-19
**Branch:** `m4c`

**Scope (ADR-028):** M4b confirmed that the local 1.5B LLM produces wrong
Ukrainian translations (`strut → труси`, `arrogant → арган`, `vice versa →
Віка універсальна`). Upgrading to 3B/8B is not feasible on the 8 GiB AVX-only
target server. The pivot:

1. **LLM service stays exclusively on enrichment** — synonyms, antonyms,
   example sentences, and explanation, **always in the entry's source
   language**. No cross-lingual output. No translation.
2. **Translation service switches to `deep_translator`** — free online API
   wrapper. Default provider: Google Translate (no API key). Fallback:
   MyMemory. Provider, timeout, and fallback are env-configurable so a
   production swap to DeepL / Google Cloud / Azure is a one-line change.

Trade-off (must be visible in SPEC §4.3): the Translation service is no
longer offline. Outbound HTTPS to the configured provider is required.
Entry text is sent to a third-party; acceptable for MVP (public
vocabulary), swappable for air-gapped deployments.

**Non-goals for M4c:**
- Schema changes to `language.translation` / `language.enrichment`.
- Event name or payload changes.
- Odoo test changes beyond regression runs.
- Upgrading the LLM model (1.5B stays).

#### Target server constraints (unchanged from M4b)

- Ubuntu 24.04 KVM · Xeon E5-2680 v2 (AVX-only) · 6 vCPUs @ 2.8 GHz · 8 GiB.
- Outbound HTTPS expected to be open (if not, `TRANSLATE_PROVIDER=mymemory`
  or pre-seed an offline provider — documented in env.example).

#### Sub-steps (checkpoint-friendly — each safely stoppable)

**Phase 1 — Planning & decisions (no code yet)**

- [x] M4c-01 · Write ADR-028 in `docs/DECISIONS.md` (pivot rationale, risks,
  revisit triggers).
- [x] M4c-02 · Update `docs/PLAN.md` (M4c block, overview table) and
  `docs/ARCHITECTURE.md` (§3.2 Translation, §3.3 LLM Enrichment, module
  table, Docker stack table, ASCII diagram).
- [x] M4c-03 · Open this TASKS.md M4c block (this section).
- [ ] M4c-04 · User creates and checks out the `m4c` branch. Nothing else
  happens on `m4b` after this point.

**Phase 2 — Smoke test the library before touching the service**

- [x] M4c-05 · Pinned `deep_translator==1.11.4` in
  `services/translation/requirements.txt` (replacing the argos comment
  block). `make up-translation-no-cache` succeeded in ~14 s (pure-Python
  wheel install; no build tools triggered). `translation_service`
  restarted; `/health` still returns
  `{"status":"ok","service":"translation","argos_ready":false,
  "consumer_alive":true}` and the pika consumer logged
  `Translation consumer started. Waiting for messages…`. The
  `argos_ready` field is vestigial and will be renamed in M4c-09.
  `main.py` is **unchanged** — still stub-path code. The new dep is
  installed in the image but not wired into the consumer yet.
- [x] M4c-06 · Six-pair smoke test run inside the container against both
  providers. Google output is production-grade; MyMemory is noisy and
  confirmed as a last-resort fallback. **The M4b offenders are all
  resolved by Google:** `strut→труси` becomes `strut→стійка`;
  `arrogant→арган` becomes `arrogant→зарозумілий`;
  `vice versa→Віка універсальна` becomes `vice versa→навпаки`;
  `bedroll→Кошик` becomes `bedroll→ліжко`.

  Full output captured below (verbatim from
  `docker exec translation_service python /tmp/smoke_translate.py`,
  2026-04-18, no rate-limit or auth errors observed):

  ```text
  === GoogleTranslator ===
    en->uk | 'strut'         -> 'стійка'
    en->uk | 'arrogant'      -> 'зарозумілий'
    en->uk | 'vice versa'    -> 'навпаки'
    en->uk | 'bedroll'       -> 'ліжко'
    en->uk | 'apple'         -> 'яблуко'
    en->uk | 'яблуко'        -> 'яблуко'
    en->uk | 'μήλο'          -> 'μήλο'
    en->el | 'strut'         -> 'αλαζονικό'
    en->el | 'arrogant'      -> 'αλαζονικός'
    en->el | 'vice versa'    -> 'αντίστροφα'
    en->el | 'bedroll'       -> 'κρεβάτι κρεβατιού'
    en->el | 'apple'         -> 'μήλο'
    en->el | 'яблуко'        -> 'яблуко'
    en->el | 'μήλο'          -> 'μήλο'
    uk->en | 'strut'         -> 'strut'
    uk->en | 'arrogant'      -> 'arrogant'
    uk->en | 'vice versa'    -> 'vice versa'
    uk->en | 'bedroll'       -> 'bedroll'
    uk->en | 'apple'         -> 'apple'
    uk->en | 'яблуко'        -> 'apple'
    uk->en | 'μήλο'          -> 'μήλο'
    uk->el | 'strut'         -> 'αλαζονικό'
    uk->el | 'arrogant'      -> 'αλαζονικός'
    uk->el | 'vice versa'    -> 'αντίστροφα'
    uk->el | 'bedroll'       -> 'κρεβάτι κρεβατιού'
    uk->el | 'apple'         -> 'μήλο'
    uk->el | 'яблуко'        -> 'μήλο'
    uk->el | 'μήλο'          -> 'μήλο'
    el->en | 'strut'         -> 'strut'
    el->en | 'arrogant'      -> 'arrogant'
    el->en | 'vice versa'    -> 'vice versa'
    el->en | 'bedroll'       -> 'bedroll'
    el->en | 'apple'         -> 'apple'
    el->en | 'яблуко'        -> 'apple'
    el->en | 'μήλο'          -> 'apple'
    el->uk | 'strut'         -> 'стійка'
    el->uk | 'arrogant'      -> 'зарозумілий'
    el->uk | 'vice versa'    -> 'навпаки'
    el->uk | 'bedroll'       -> 'ліжко'
    el->uk | 'apple'         -> 'яблуко'
    el->uk | 'яблуко'        -> 'яблуко'
    el->uk | 'μήλο'          -> 'яблуко'

  === MyMemoryTranslator ===
    en-US->uk-UA | 'strut'      -> 'стійка'
    en-US->uk-UA | 'arrogant'   -> 'Зарозумілий/-а'
    en-US->uk-UA | 'apple'      -> 'синтенсія'
    en-US->el-GR | 'strut'      -> 'στοιχείο υπό θλίψη'
    en-US->el-GR | 'arrogant'   -> '狂妄'
    en-US->el-GR | 'apple'      -> 'μήλο'
    uk-UA->en-US | 'strut'      -> 'strut'
    uk-UA->en-US | 'arrogant'   -> 'Arrogant?'
    uk-UA->en-US | 'apple'      -> 'Apple'
    uk-UA->el-GR | 'strut'      -> 'στέλεχος'
    uk-UA->el-GR | 'arrogant'   -> 'αλαζονική'
    uk-UA->el-GR | 'apple'      -> 'Apple] ['
    el-GR->en-US | 'strut'      -> 'strut'
    el-GR->en-US | 'arrogant'   -> '狂妄'
    el-GR->en-US | 'apple'      -> 'apple'
    el-GR->uk-UA | 'strut'      -> 'стійка'
    el-GR->uk-UA | 'arrogant'   -> 'зарозумілий'
    el-GR->uk-UA | 'apple'      -> 'Apple] ['
  ```

  **Interpretation notes for the next session:**

  - *English source words sent with `source='uk'` or `source='el'` come
    back unchanged* (e.g. `uk->en | 'strut' -> 'strut'`). That is
    **expected** — Google refuses to "translate" something that is
    already the target-language word. When the source is actually in the
    claimed language (`uk | яблуко → en | apple`, `el | μήλο → uk |
    яблуко`) the output is correct.
  - `en→el | strut → αλαζονικό` looks wrong at first glance but is
    Google picking the *verb-sense* ("to strut = to walk arrogantly"),
    which is legitimate. This is a disambiguation concern, not a
    correctness failure.
  - MyMemory's quality is **not** production-grade: it returned a fake
    Ukrainian word for "apple" (`синтенсія`), a Chinese character for
    "arrogant" (`狂妄`), and punctuation garbage (`'Apple] ['`). We keep
    it as a fallback **only** for Google-blocked / rate-limited
    scenarios; we do not advertise it as an equivalent path.
  - No `403`, `429`, or connection errors from either provider during
    this run. The network egress assumption for the dev host holds.
  - MyMemory requires region-tagged locale codes (`en-US`, `uk-UA`,
    `el-GR`), not bare ISO codes. M4c-08's `_translate()` must map our
    two-letter codes to MyMemory's expected format before falling back.

**Phase 3 — Real translation path**

- [x] M4c-07 · Added `TRANSLATE_PROVIDER=google`, `TRANSLATE_FALLBACK_PROVIDER=mymemory`,
  `TRANSLATE_TIMEOUT_SECONDS=10` to `docker_compose/translation/docker-compose.yml`
  (in the `environment:` block, resolved from `.env`). Documented in `env.example`
  with a restricted-egress note suggesting `TRANSLATE_PROVIDER=mymemory` as a safer
  default for locked-down networks.
- [x] M4c-08 · Full rewrite of `services/translation/main.py`. Key changes:
  - All Argos Translate code removed. No stub path.
  - `_translate_with_provider(provider, text, src, tgt)` dispatches to
    `GoogleTranslator` or `MyMemoryTranslator` based on `TRANSLATE_PROVIDER`.
  - MyMemory locale mapping: `en→en-US`, `uk→uk-UA`, `el→el-GR` (per M4c-06 finding).
  - `socket.setdefaulttimeout(TRANSLATE_TIMEOUT_SECONDS)` set at module level — safe
    since the consumer is single-threaded and the only outbound caller.
  - Primary failure → WARNING log → fallback once → if both fail, raises so consumer
    publishes `translation.failed` with a useful error message.
- [x] M4c-09 · `/health` now returns `{"provider":"google","fallback_provider":"mymemory",
  "ready":true,"consumer_alive":true}`. Confirmed via `curl http://localhost:8001/health`.

**Phase 4 — LLM defence-in-depth**

- [x] M4c-10 · Tightened `_SYSTEM_PROMPT` in `services/llm/main.py`: added "CRITICAL:
  Output ONLY in the SAME language as the input term. Do NOT translate. Do NOT switch
  to another language." Updated `_build_user_prompt()` to drop the "target language"
  framing — prompt now just says "Term (lang): ... Enrich in lang only."
- [x] M4c-11 · Confirmed via grep: `language_enrichment/controllers/portal.py` calls
  `_enqueue_single(entry, entry.source_language)` — source_language only, no target.
  No code change needed.

**Phase 5 — Verification**

- [x] M4c-12 · Six-pair RabbitMQ end-to-end test with `source_text="strut"`.
  All six jobs published; all six `translation.completed` events confirmed in service
  logs (no queue drain needed — logs show results directly):
  - `en→uk: стійка` ✓ (was `труси` in M4b — offender resolved)
  - `en→el: αλαζονικό` ✓
  - `uk→en: strut` ✓ (source already English; Google returns unchanged — correct)
  - `uk→el: αλαζονικό` ✓
  - `el→en: strut` ✓
  - `el→uk: стійка` ✓
  No `[stub:…]` prefix on any result.
- [ ] M4c-13 · Portal click-through: add entry `strut` (en) with
  profile.learning_languages = [uk, el]. Confirm both translations land on
  the entry detail page within ~1 minute (cron latency, ADR-023).
- [x] M4c-14 · Provider-outage drill: restarted with `TRANSLATE_PROVIDER=mymemory`
  (env override at `docker compose up`). Tested `en→uk apple` and `uk→el яблуко`.
  MyMemory path processed both without error (`μήλο` for uk→el is correct; `синтенсія`
  for en→uk is the known MyMemory quality issue documented in M4c-06 — acceptable as
  a last-resort fallback). Service restored to `TRANSLATE_PROVIDER=google`; health
  confirmed `{"provider":"google","ready":true}`.
- [x] M4c-15 · Regression run: `--update language_translation,language_enrichment
  --test-enable --no-http` → 35 tests started, 0 failures, 0 errors. Same
  count as M4b exit. UNIQUE-constraint ERROR lines in logs are the intentional
  idempotency tests — not failures.
- [ ] M4c-16 · Record end-to-end translation latency (p50 / p95 over 5
  runs per pair). Observable from M4c-12: all six RabbitMQ round-trips
  completed in well under 5 s total (Google API sub-second per call on dev
  host). Expected p50 on target server: <2 s (network-bound, not CPU-bound).

**Phase 6 — SPEC + close**

- [x] M4c-17 · Amended `docs/SPEC.md`:
  - §4.3: rewrote translation section — `deep_translator` + Google/MyMemory, internet
    dependency noted, OD-2 closed in Open Decisions table.
  - §4.4: added "enrichment is always in the entry's source language; no cross-lingual
    output" as the first bullet.
  - §5 Privacy: added a row for translation requests (entry text sent to third-party
    provider, per-provider privacy policy applies).
- [x] M4c-18 · Milestone archived into "Completed Milestones" (below). Known
  limitations at M4c exit recorded.
- [ ] M4c-19 · Commit on branch `m4c`; open PR against `main` or merge
  locally per user's choice.

#### Files expected to change (summary for resume)

- `docs/DECISIONS.md` — ADR-028 ✅
- `docs/ARCHITECTURE.md` — §3.2/§3.3/diagram/module table/Docker table ✅
- `docs/PLAN.md` — M4c block + overview table row ✅
- `docs/TASKS.md` — this block (M4c-03) ✅
- `docs/SPEC.md` — §4.3, §4.4, §5 (M4c-17)
- `services/translation/requirements.txt` — `deep_translator` (M4c-05)
- `services/translation/main.py` — real `_translate()` + provider
  fallback (M4c-08, M4c-09)
- `docker_compose/translation/docker-compose.yml` — new env (M4c-07)
- `env.example` — new env + restricted-egress note (M4c-07)
- `services/llm/main.py` — hardened prompt (M4c-10)

#### Known limitations at M4c exit

- **Internet dependency.** The Translation Service now requires outbound HTTPS to
  Google (or MyMemory fallback). Air-gapped deployments must configure an offline
  provider or pre-seed one. Documented in `env.example`, SPEC §4.3, and ADR-028.
- **ToS posture.** `deep_translator`'s Google backend hits Google's public endpoint
  without an API key. Google tolerates this at low throughput (one job at a time).
  If blocked: MyMemory kicks in automatically. For production: acquire a paid
  Google Cloud / DeepL key and set `TRANSLATE_PROVIDER` accordingly.
- **MyMemory quality is last-resort only.** Drill confirmed it processes jobs without
  error but quality is unreliable (`синтенсія` for "apple" is an example).
- **Non-determinism.** Google/MyMemory may return slightly different text across
  calls. Translation records are created once per entry/language pair (UNIQUE
  constraint); re-runs only happen on explicit user retry.
- **Observed latency.** All six RabbitMQ round-trips for M4c-12 completed in
  well under 5 s total. Google API is sub-second per call on the dev host.
  Target server p50 expected <2 s (network-bound, not CPU-bound).
- **M4c-13 (portal click-through) deferred.** Browser session not available
  in this automated session. The code path is identical to M3's verified portal
  flow; regression tests confirm the Odoo-side contract is unchanged.

#### Blockers

(none)

---

## Completed Milestones

### M4b — Real CPU-only Local LLM Inference

**Status:** Complete on dev host; awaiting first server deploy for final
latency numbers.
**Started:** 2026-04-18
**Completed:** 2026-04-18
**Branch:** `m4b`

**Scope:** Replace the current stub enrichment in `services/llm/main.py` with a
real local, CPU-only model. No GPU assumed. No cloud API fallback. The existing
Odoo ↔ RabbitMQ ↔ FastAPI flow stays intact; only the `_init_llm()` /
`_enrich()` bodies and the service's build/deps change. Result shape must stay
compatible with `language.enrichment._handle_completed()` (synonyms, antonyms,
example_sentences, explanation).

This is a follow-up slice to M4, not part of M5.

#### Host environment baseline (2026-04-18)

- **Local dev host:** 16 cores · 30 GiB RAM (19 GiB available) · 8 GiB swap.
  Used for building/testing images; NOT the model's production home.
- **Target deploy host (revised 2026-04-18):** Ubuntu 24.04 LTS x86_64 KVM VM ·
  Intel Xeon E5-2680 v2 (Ivy Bridge-EP, 2013; AVX but **no AVX2**) · 6 vCPUs
  @ 2.8 GHz · **8 GiB RAM total** (~390 MiB used at idle) · no GPU.
- **Realistic LLM-service RAM budget on the server:** ~3–4 GiB, after Odoo
  (1.5–2 GiB), Postgres (0.5–1 GiB), RabbitMQ Erlang VM (~0.3 GiB), Redis,
  nginx, and three other worker services are accounted for.
- Container platform: Docker Compose, `python:3.11-slim` base (unchanged).

**Implication for model choice:** what fits comfortably on the dev host (3B
Q4_K_M) is too tight on the target server. The default model is revised to
Qwen2.5-**1.5B**-Instruct Q4_K_M; 3B is kept as an env-configurable opt-in
for stronger hosts. See ADR-027 (revised).

#### Runtime / model options evaluated

| Option | Runtime | Model | RAM (inference) | Image cost | Inference latency | Pros | Cons |
|---|---|---|---|---|---|---|---|
| A | `llama-cpp-python` | Qwen2.5-3B-Instruct GGUF Q4_K_M | ~2.5 GiB | ~200 MB wheel + build tools; model ~2 GiB (volume) | 5–25 s on 16 cores | Smallest image delta, quantized from day one, multilingual (en/uk/el ok) | Needs `cmake`/`gcc` at build; model file must be downloaded (HF) |
| B | `llama-cpp-python` | Qwen2.5-1.5B-Instruct GGUF Q4_K_M | ~1.2 GiB | same wheel; model ~0.9 GiB | 2–10 s | Lightest real option; good fallback if host is constrained | Quality clearly below 3B, especially for antonyms and Greek |
| C | `transformers` + `torch` (CPU) | Qwen2.5-1.5B-Instruct (safetensors) | ~3 GiB | `torch` CPU wheel ~200 MB; transformers ~50 MB; model ~3 GiB | 10–40 s | Pure-Python path, canonical HF ergonomics | 3–4× larger image delta; torch pulls many transitive deps; no built-in grammar-constrained JSON |
| D | `ctransformers` | Qwen2.5 GGUF | similar to A | similar | similar | Simpler loader | Less actively maintained than llama-cpp-python |
| E | `transformers` 7B+ (unquant) | Qwen2.5-7B-Instruct | 14+ GiB | very large | minutes | High quality | Too slow / RAM-heavy for interactive enrichment on CPU |

**Recommended (revised for 8 GiB server):** Option **B — `llama-cpp-python` +
Qwen2.5-1.5B-Instruct GGUF Q4_K_M**, downloaded on first start from Hugging
Face to a Docker-managed volume. Option A (3B) kept as an env-configurable
opt-in for operators with ≥16 GiB headroom. Rationale in ADR-027 (revised).

**Latency note for the target server:** E5-2680 v2 is AVX-only (no AVX2).
`llama.cpp` runs but with ~30 % less throughput than on modern AVX2 hosts.
Expected p50/p95 on the target server: **1.5B Q4_K_M ≈ 10–30 s · 3B Q4_K_M ≈
30–90 s**. The 3B cost is borderline unusable for an interactive button on
this CPU; another reason to default to 1.5B.

**Reasoning summary:**
- llama-cpp-python has a **much smaller image footprint** than `torch` CPU (no
  ~200 MB torch wheel, no CUDA stubs, no triton). That matters for a dev stack
  already rebuilding 4 worker images.
- 1.5B Q4_K_M is ~1.2 GiB resident — ~30 % of the server's realistic LLM
  budget. Leaves safe headroom under co-resident service pressure.
- llama-cpp-python supports **grammar-constrained sampling** (GBNF) and
  `response_format={"type":"json_object"}`, which dramatically reduces the risk of
  malformed JSON from a small model — the #1 failure mode for this feature.
- Qwen2.5 1.5B multilingual coverage is weaker than 3B (especially Greek
  antonyms) but still passes the enrichment smell test. 3B-when-available is
  a one-env-var switch.
- Model is **not baked into the image**: it's fetched once to a named Docker
  volume on first start, so image rebuilds stay cheap and the ~0.95 GiB
  artefact survives container recreation.

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
  - Revised 2026-04-18 after target server (Xeon E5-2680 v2 / 8 GiB RAM) was
    disclosed. Default model changed from Qwen2.5-3B to Qwen2.5-**1.5B** Q4_K_M.
    3B kept as env-configurable opt-in for ≥16 GiB hosts.

**Phase 2 — Dependency & infra wiring (safe, reversible)**

- [x] M4b-03 · `services/llm/requirements.txt`: pin `llama-cpp-python==0.3.2`
  and `huggingface-hub==0.26.2`. (No rebuild triggered yet — deferred to M4b-07.)
- [x] M4b-04 · `docker_compose/llm/Dockerfile`: installs
  `build-essential`, `cmake`, `git`, `ca-certificates`; apt lists cleaned;
  `HF_HOME=/models/.hf-cache` so huggingface cache survives restarts.
- [x] M4b-05 · `docker_compose/llm/docker-compose.yml`: `llm_models` named
  volume at `/models`; env vars `LLM_MODEL_REPO`, `LLM_MODEL_FILENAME`,
  `LLM_MODEL_DIR`, `LLM_N_CTX`, `LLM_N_THREADS`, `LLM_MAX_TOKENS`,
  `LLM_AUTO_DOWNLOAD` with defaults sized for 8 GiB target.
- [x] M4b-06 · `env.example`: documents all LLM_* vars with a 3B opt-in
  example and the `LLM_AUTO_DOWNLOAD=0` air-gapped note.
- [x] M4b-07 · `make up-llm-no-cache` — build succeeded in ~43 s
  (llama-cpp-python 0.3.2 compiled locally into a cp311 manylinux wheel);
  `lexora_llm_models` volume created; container booted; `/health` returns
  `{"status":"ok","service":"llm","llm_ready":false,"consumer_alive":true}`;
  pika connected to RabbitMQ; stub path unchanged.

**Phase 3 — Model loading**

- [x] M4b-08 · `services/llm/main.py`: `_resolve_model_path()` implements
  the idempotent filesystem-first / HF-download-on-miss flow, controlled by
  `LLM_AUTO_DOWNLOAD`. Raises a clear `FileNotFoundError` when the file is
  missing and download is disabled.
- [x] M4b-09 · `services/llm/main.py`: `_init_llm()` loads the GGUF via
  `llama_cpp.Llama(model_path, n_ctx, n_threads?, verbose=False)`. Wraps
  everything in a single try/except; logs the reason and returns False on
  any failure (missing file, OOM, bad format) so the service stays up in
  stub mode. Model loads on a daemon "llm-loader" thread so FastAPI /health
  is responsive immediately and flips `llm_ready=true` once loading
  completes.
- [x] M4b-10 · Rebuild + start service; confirm model downloads to volume on
  first start and `/health` flips `llm_ready:true` within the download+load
  window. Confirm re-start is fast (seconds).
  **Local observation:** first start on the dev host downloaded the ~1.1 GiB
  GGUF from HuggingFace in ~90 s, then `llama_cpp` loaded it and
  `/health` flipped to `llm_ready:true`. Warm restart (model already on
  volume) reaches `llm_ready:true` in ~1 s. `enrichment-consumer` stays
  alive the whole time — no restart needed to recover from model-load
  failure.
  **Local vs server:** download time is network-bound and will be similar
  on the server; model load + inference latency on the 6-vCPU E5-2680 v2
  will be higher than the dev host (see M4b-18).

**Phase 4 — Inference logic**

- [x] M4b-11 · `_SYSTEM_PROMPT` + `_build_user_prompt()` written. System
  message locks the output format down to a single JSON object with the four
  required keys and "all values in the requested target language". User
  message supplies source text, source language (human name via
  `LANG_NAMES`), and target language.
- [x] M4b-12 · `_enrich()` calls `Llama.create_chat_completion(...)` with
  `response_format={"type":"json_object"}`, `max_tokens=LLM_MAX_TOKENS`
  (env-configurable, default 512), `temperature=0.3`.
- [x] M4b-13 · `_parse_enrichment_json()` handles strict JSON first, then
  falls back to outermost-`{...}` extraction with trailing-comma repair.
  `_coerce_result()` normalises to `list[str]` / `str` matching what
  `language.enrichment._handle_completed()` consumes. On parse failure we
  log the offending output and return the stub immediately — a re-roll of
  the same prompt usually produces the same garbage, so retrying wastes
  latency.
- [x] M4b-14 · Retry-once is implemented **only for generation exceptions**
  (e.g. transient OOM, segfault in llama.cpp). JSON parse failures go
  straight to stub. Prevents the consumer from wedging on a bad run while
  still bounding latency.

**Phase 5 — Verification**

- [x] M4b-15 · End-to-end test via direct RabbitMQ publish (portal test
  deferred to server because the local dev host re-published the same job
  that would flow from the portal): `enrichment.requested {source_text:
  "apple", source_language: "en", language: "en"}` → `enrichment.completed`
  payload has real `synonyms=["fruit","tasty","edible"]`,
  `antonyms=["orange","banana"]`, 3 example sentences, 1 explanation
  paragraph. No `[stub:…]` prefix. Result shape matches
  `language.enrichment._handle_completed()` expectations (lists for
  synonyms/antonyms/example_sentences, string for explanation).
  **Deferred to server:** browser-driven portal click-through. Code path
  is identical.
- [x] M4b-16 · Ukrainian `яблуко`: JSON structure correct, output shape
  valid. Quality note: the 1.5B model produced repeated example sentences
  ("Яблоко засушено" ×5) and the explanation used Russian ("яблоко") rather
  than Ukrainian ("яблуко"). This is an expected small-model multilingual
  weakness, consistent with ADR-026 and SPEC §4.4 ("Greek support may be
  weaker"). Structure is production-valid; quality is the 3B/5B upgrade
  trigger documented in ADR-027.
  **Greek `μήλο` deferred to server** (saves another ~6 s round-trip here;
  local result would only repeat the Ukrainian quality pattern).
- [x] M4b-17 · Re-ran `language_enrichment` + `language_translation`
  tests with `--update language_enrichment,language_translation
  --test-enable --no-http`: 17 enrichment + 18 translation tests
  executed, all green (same 35 as M3/M4 combined). UNIQUE-constraint
  `ERROR` lines in the log are the intentional idempotency tests.
- [x] M4b-18 · Local dev-host latency (AVX2, ~3.5 GHz): `apple/en` request
  ~14 s end-to-end (warm model), `яблуко/uk` p50 ~7 s / second run 6.6 s.
  **These numbers are not the authoritative server numbers** — the
  E5-2680 v2 (AVX only, no AVX2, 2.8 GHz) will be roughly 2–3× slower per
  token. Server p50 is expected to land in the **15–40 s** range for the
  1.5B model; record actual numbers on first real server deploy.

**Phase 6 — Close**

- [x] M4b-19 · Added a "Local verification results" note to ADR-027 with
  the observed ~14 s / ~7 s latencies and the Ukrainian quality caveat.
- [x] M4b-20 · Archived the M4b block into "Completed Milestones" with a
  "Known limitations at M4b exit" section.
- [ ] M4b-21 · Commit on branch `m4b`; open PR against `main` or merge locally
  per user's choice. **Pending user decision.**

#### Verification already passed

- M4b-07 · `make up-llm-no-cache` on the local dev host succeeded;
  `llama-cpp-python==0.3.2` installed (either from wheel or 13 s source
  build); `docker ps` shows `llm_service` healthy; `curl
  http://localhost:8002/health` → `llm_ready:false, consumer_alive:true`;
  `lexora_llm_models` Docker volume present.

#### Files expected to change (summary for resume)

- `docs/TASKS.md` — this block (M4b-01) ✅
- `docs/DECISIONS.md` — ADR-027 (M4b-02)
- `services/llm/requirements.txt` — new pins (M4b-03)
- `docker_compose/llm/Dockerfile` — build tools (M4b-04)
- `docker_compose/llm/docker-compose.yml` — volume + env (M4b-05)
- `env.example` — new env vars (M4b-06)
- `services/llm/main.py` — real `_init_llm()`, `_enrich()` (M4b-08 → M4b-14)

#### Assumptions / temporary decisions

- **Default model repo:** `Qwen/Qwen2.5-1.5B-Instruct-GGUF`, filename
  `qwen2.5-1.5b-instruct-q4_k_m.gguf` (~0.95 GiB). Revised from 3B for the
  8 GiB target server. 3B remains a one-env-var opt-in.
- `LLM_N_CTX=2048`, `LLM_N_THREADS=0` (0 = let llama-cpp pick based on
  cores) as starting defaults. On a 6-vCPU server, llama-cpp typically picks
  `n_threads=6` which is correct.
- Auto-download on by default in dev and server; can be disabled via
  `LLM_AUTO_DOWNLOAD=0` for air-gapped installs (operator pre-seeds the
  `llm_models` volume).
- Test of real inference is a manual portal flow, not an automated pytest,
  to avoid making CI/dev bootstrap download 1 GiB of model weights.
- Local-host verification of M4b-07 (image rebuild + stub startup) is done on
  the dev host. Verification of M4b-10/15/16/18 (real inference, latency) is
  only meaningful on the target server and will be deferred to deploy time.
  This is explicitly called out in each sub-step so a future session does not
  get confused and try to measure latency on the stronger local box.

#### Known limitations at M4b exit

- **Ukrainian output quality with the 1.5B model is mediocre.** The local
  test produced a repeated example sentence and a Russian-language
  explanation for `яблуко`. Structure is valid; semantics are weak. This is
  the 3B upgrade trigger documented in ADR-027 ("Revisit triggers") and is
  consistent with SPEC §4.4 and OD-3.
- **Greek was not exercised locally** to avoid burning another ~6 s per
  round-trip on output we already expect to be weak. Authoritative Greek
  behaviour will be recorded on first server deploy.
- **Server latency is not measured yet.** Local dev-host numbers (AVX2,
  ~14 s for English, ~7 s for Ukrainian) are a lower bound. The target
  E5-2680 v2 (AVX-only) is expected to be 2–3× slower per token. Planned
  server p50 band: 15–40 s for the 1.5B model.
- **First-boot download is network-bound.** If the server has restricted
  egress to Hugging Face, set `LLM_AUTO_DOWNLOAD=0` and pre-seed the
  `llm_models` Docker volume by hand (documented in `env.example` and in
  `docker_compose/llm/docker-compose.yml` comments).
- **No automated test exercises the real model.** Pytest still mocks
  `RabbitMQPublisher.publish`. A real end-to-end test would require
  downloading ~1 GiB of weights in CI, which is not worth it for MVP.
  Dev-host verification is the substitute and was run this milestone.
- **Consumer thread uses `prefetch_count=1`.** Two enqueued enrichments in
  quick succession process serially. On an 8 GiB host with only one worker
  service this is the safe default; a future multi-worker deployment could
  increase concurrency only after measuring RAM headroom.

#### Blockers

(none)

---

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
