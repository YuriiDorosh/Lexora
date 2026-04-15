# Lexora — Product Specification (MVP)

> Version: 0.1 (post-discovery)
> Last updated: 2026-04-13
> Status: Approved for implementation planning

---

## 1. Product Overview

Lexora is a language-learning platform built on Odoo 18. Users build personal vocabulary lists (words, phrases, and sentences), enrich them with translations and LLM-generated context, practice via PvP word battles, and participate in a community layer of posts, articles, and chats.

**MVP languages:** Ukrainian (`uk`), English (`en`), Greek (`el`).

---

## 2. User Roles

| Role | How Assigned | Capabilities |
|---|---|---|
| Public Visitor | Unauthenticated | View public pages only |
| Language User | Auto-assigned on signup | All core learning, PvP, chat, post creation, copy-to-list |
| Moderator | Admin-assigned | Approve/reject posts, delete messages, mute/ban users |
| Administrator | Odoo admin group | Full backend access, system settings, job queues, analytics |

After signup, users are placed in the **Language User** security group automatically. They are **not** admins by default.

---

## 3. Domain Model

### 3.1 Learning Entry (`language.entry`)

A single model with a `type` field. No separate models per type.

| Field | Type | Notes |
|---|---|---|
| `id` | Integer | Auto |
| `type` | Selection | `word`, `phrase`, `sentence`, `collocation` (collocation behaves as phrase in MVP) |
| `source_text` | Char | Original text as entered/imported |
| `normalized_text` | Char | Computed at save; used for dedup lookup |
| `source_language` | Selection | `uk`, `en`, `el` |
| `owner_id` | Many2one → `res.users` | The user who owns this entry |
| `is_shared` | Boolean | `False` by default; opt-in public sharing |
| `status` | Selection | `active`, `archived` |
| `created_from` | Selection | `manual`, `anki_import`, `copied_from_post`, `copied_from_entry`, `copied_from_chat` |
| `copied_from_user_id` | Many2one → `res.users` | Optional provenance |
| `copied_from_entry_id` | Many2one → `language.entry` | Optional provenance |
| `copied_from_post_id` | Many2one → `language.post` | Optional provenance |
| `translations` | One2many → `language.translation` | Translation results |
| `enrichments` | One2many → `language.enrichment` | Enrichment results |
| `audio_ids` | One2many → `language.audio` | Audio recordings and generated TTS |
| `media_links` | One2many → `language.media.link` | External URLs |
| `pvp_eligible` | Boolean | Computed; `True` if entry has at least one valid translation |

**Type-specific rules (enforced by validation, not separate models):**

- `word`: short text; triggers a length warning if > 50 characters.
- `phrase` / `collocation`: medium length; warning > 150 characters.
- `sentence`: longer text allowed; trailing punctuation (`.`, `!`, `?`) is ignored during dedup normalization.

**All three types support:** audio button, translation, enrichment, PvP eligibility (configurable minimum entry count is the gate, not type).

### 3.2 Deduplication Rules

Dedup key: **`normalize(source_text)` + `source_language` + `owner_id`**

`normalize()` pipeline (applied at save time, stored in `normalized_text`):

1. Unicode normalization (NFC)
2. Lowercase
3. Strip leading/trailing whitespace
4. Collapse repeated internal whitespace to single space
5. Normalize smart quotes, apostrophes, dashes to ASCII equivalents
6. Strip trailing sentence-ending punctuation (`.`, `!`, `?`) — for dedup comparison only, not stored value
7. Do **not** strip internal meaningful punctuation (apostrophes in contractions, hyphens in compound words, etc.)

**`type` is not part of the dedup key.** If the same normalized text + source language + owner already exist, the entry is a duplicate regardless of type.

**On collision:**
- Skip the duplicate; do not overwrite existing data.
- Report to user: created count + skipped count.
- For Anki imports: persist a reviewable import log with the list of skipped items.
- For manual adds: show an inline "this entry already exists" message.

### 3.3 User Language Preferences (`language.user.profile`)

Each user has a profile record with:

| Field | Type |
|---|---|
| `user_id` | Many2one → `res.users` |
| `native_language` | Selection (`uk`, `en`, `el`) |
| `learning_languages` | Many2many → language codes |
| `default_source_language` | Selection (optional) |
| `pvp_total_battles` | Integer |
| `pvp_wins` | Integer |
| `pvp_losses` | Integer |
| `pvp_draws` | Integer |
| `pvp_win_rate` | Float (computed) |
| `is_shared_list` | Boolean | Whether the whole vocabulary list is shared |

### 3.4 Translation (`language.translation`)

| Field | Type |
|---|---|
| `entry_id` | Many2one → `language.entry` |
| `target_language` | Selection |
| `translated_text` | Text |
| `job_id` | Char (UUID) | Idempotency key |
| `status` | Selection (`pending`, `processing`, `completed`, `failed`) |
| `error_message` | Text |

### 3.5 Enrichment (`language.enrichment`)

| Field | Type |
|---|---|
| `entry_id` | Many2one → `language.entry` |
| `language` | Selection | Language context for the enrichment |
| `synonyms` | Text | JSON list |
| `antonyms` | Text | JSON list |
| `example_sentences` | Text | JSON list (3–7 sentences) |
| `explanation` | Text | Short explanation |
| `job_id` | Char (UUID) |
| `status` | Selection (`pending`, `processing`, `completed`, `failed`) |
| `error_message` | Text |

### 3.6 Audio (`language.audio`)

| Field | Type |
|---|---|
| `entry_id` | Many2one → `language.entry` |
| `audio_type` | Selection (`recorded`, `generated`, `imported`) |
| `language` | Selection |
| `attachment_id` | Many2one → `ir.attachment` | Stored in Odoo filestore |
| `job_id` | Char (UUID) | For generated audio; idempotency key |
| `status` | Selection (`pending`, `processing`, `completed`, `failed`) |
| `file_size_bytes` | Integer |
| `duration_seconds` | Float |
| `tts_engine` | Char | e.g., `piper`, `espeak-ng` |

Max upload size for user-recorded audio: **10 MB** (configurable system setting).

### 3.7 Media Links (`language.media.link`)

| Field | Type |
|---|---|
| `entry_id` | Many2one → `language.entry` (nullable) |
| `post_id` | Many2one → `language.post` (nullable) |
| `url` | Char | Format-validated |
| `title` | Char (optional) |
| `description` | Text (optional) |
| `user_note` | Text (optional) |

No server-side reachability checks. No automatic metadata scraping in MVP.

### 3.8 Import Job (`language.anki.job`)

| Field | Type |
|---|---|
| `user_id` | Many2one → `res.users` |
| `filename` | Char |
| `file_format` | Selection (`apkg`, `txt`) |
| `source_language` | Selection | Confirmed by user at import time |
| `target_language` | Selection (optional) |
| `field_mapping` | Text | JSON: which deck field → source_text, translation |
| `job_id` | Char (UUID) |
| `status` | Selection (`pending`, `processing`, `completed`, `failed`) |
| `entries_created` | Integer |
| `entries_skipped` | Integer |
| `entries_failed` | Integer |
| `skipped_details` | Text | JSON list of skipped items, for review |
| `error_message` | Text |
| `created_at` | Datetime |

Import logs are stored **persistently**; users can review them later.

---

## 4. Feature Specifications

### 4.1 Manual Entry

1. User navigates to their vocabulary page.
2. User types source text into the add-entry form.
3. System auto-detects source language; prefills the language dropdown.
4. If detection confidence is low, fall back to the user's `default_source_language`.
5. User reviews/corrects the language. Submission is blocked if language is unset.
6. On save: normalize text, run dedup check; if duplicate, show inline message.
7. If new: create the entry, **automatically enqueue a translation job** (to the user's learning languages).

### 4.2 Anki Import

**Supported formats:** `.apkg`, `.txt` (tab-separated).

**Flow:**
1. User uploads file via the import page.
2. For `.apkg`: system attempts to auto-detect field mapping (Front/Back convention). If ambiguous, presents field mapping UI.
3. For `.txt`: fixed two-column parse (column 1 = source, column 2 = translation).
4. User confirms or adjusts: source language, field mapping.
5. Odoo publishes `anki.import.requested` to RabbitMQ with the file + config.
6. Anki import service processes the file:
   - Parses entries.
   - For `.apkg`: attempts to extract embedded audio (MP3) and attach to entries.
   - Images are ignored in MVP.
   - Runs dedup check against user's existing entries.
   - Returns list of: new entries, skipped entries, errors.
7. Odoo receives `anki.import.completed`, creates entries, writes the import log.
8. Re-importing the same deck with overlapping data: duplicates are skipped, new entries created.

**Audio from `.apkg`:** if audio files are present in the Anki media bundle, extract and attach them as `language.audio` records with `audio_type = 'imported'` (distinct from `recorded`, which means the user captured it themselves). If extraction fails for a card, import the text anyway; log the failure in the import result.

### 4.3 Translation

- Triggered automatically after manual entry save (to all user learning languages).
- Triggered automatically after "copy to my list" save.
- Can be manually re-triggered from the entry detail page.
- Uses **Argos Translate** (offline). Note: no direct uk↔el model exists; routing is uk→en→el (two-hop). Quality limitation documented.
- Events: `translation.requested` → `translation.completed` / `translation.failed`.
- Each translation direction is a separate `language.translation` record with its own job.

### 4.4 LLM Enrichment

- User-triggered from the entry detail page (not automatic).
- Enriches in the context of the entry's source language.
- Produces: synonyms (JSON list), antonyms (JSON list), 3–7 example sentences (JSON list), short explanation (text).
- Model: CPU-first. Recommended: Qwen2.5 1.5B–3B (≤3 GB RAM, fast on CPU). Qwen3 8B INT4 via llama.cpp is supported on ≥16 GB RAM machines. No GPU required. Greek support may be weaker; documented as a known limitation.
- If model unavailable or generation fails: show retry button + error badge on the entry.
- Events: `enrichment.requested` → `enrichment.completed` / `enrichment.failed`.

### 4.5 Audio

**Three `audio_type` values:**
- `recorded` — user captured via microphone in the browser
- `generated` — auto-generated by the TTS service
- `imported` — extracted from an Anki `.apkg` media bundle

**Two user-facing modes (both in MVP):**

**A) User-recorded:**
- User presses record button → browser captures audio → uploads to Odoo.
- Stored as `ir.attachment` via `language.audio` record (`audio_type = 'recorded'`).
- Stored permanently. Max size: ~10 MB (configurable).
- One recording per entry per user (can be replaced by re-recording).

**B) Auto-generated TTS:**
- User presses "generate pronunciation" button.
- Odoo publishes `audio.generation.requested`.
- Audio/TTS service processes offline (piper / espeak-ng / Coqui TTS).
- Language quality note: English TTS quality > Ukrainian > Greek (known MVP limitation).
- On completion: audio stored as `ir.attachment` (`audio_type = 'generated'`).
- Lazy generation: generated once, stored permanently, reused on subsequent plays.
- Events: `audio.generation.requested` → `audio.generation.completed` / `audio.generation.failed`.

**All three entry types** (word, phrase, sentence) support the audio button.

### 4.6 Posts and Articles

- Any **Language User** can create a draft post/article.
- Draft must be **submitted for moderator review** before publishing.
- Moderators and Admins can approve, reject, or publish directly.
- Posts have: title, body (rich text), tags, attached media links, comments.

**Comments:**
- Flat, chronological order.
- Support @mentions of other users.
- No nested/threaded replies in MVP.
- Moderators can delete comments; users can report comments.

### 4.7 "Copy to My List"

Available in: posts/articles, chat messages.

**UX flow:**
1. User selects text in a post/article or chat message.
2. An inline popup appears: "Save to my list".
3. Click opens a lightweight side panel / mini-form with:
   - Pre-filled selected text
   - Auto-detected source language (with dropdown to correct)
   - Optional note field
4. User confirms (or edits) and saves.
5. System runs dedup check; creates a new `language.entry` owned by the current user if not duplicate.
6. **Translation is automatically requested** after save (same as manual entry).
7. Provenance fields are set: `created_from`, `copied_from_user_id`, `copied_from_post_id`.

### 4.8 Chat

- **Public channels:** visible to all Language Users; anyone can post.
- **Private DMs:** 1-to-1 conversations; initiated from a user's profile page.
- "Save to my list" is available from chat message text (same inline popup UX).
- Built on Odoo's built-in discuss/messaging module.
- Moderators can see and moderate public channels; DMs are private unless a message is reported.
- Users can report messages; moderators review reported content.
- Moderator actions: delete message, mute user, ban/suspend user.

### 4.9 Vocabulary Search

Scope: source text + translations.

- Substring / prefix matching (SQL ILIKE).
- Fuzzy search via `base_search_fuzzy` OCA addon (files present in `src/addons/`; must be installed in the database and requires the `pg_trgm` PostgreSQL extension).
- Cross-language lookup: searching "apple" finds entries where source text or any translation is "apple".
- MVP: no semantic/AI search.

### 4.10 Post/Article Search

- Simple text search across title + body.
- No comment search in MVP.
- SQL ILIKE-based.

### 4.11 Dashboards

**Personal dashboard (per-user):**
- Total entries (by type breakdown)
- Recent activity (entries added, translations, enrichments)
- Learning language distribution
- Translation request count
- Enrichment request count
- PvP stats: total battles, wins, losses, draws, win rate

**Global/community dashboard:**
- Popular words (weighted score: list additions + copied-from-content count + translation requests)
- Word of the day (auto-selected from eligible pool, language-specific, not random from full DB)
- Most translated entries
- Most enriched entries
- Top language pairs by activity
- Most copied entries from posts/articles
- Leaderboard (top PvP players; filterable by language pair)

Implemented in SQL/Postgres. No Elasticsearch in MVP.

### 4.12 PvP Word Battle

**Entry point:**
1. User selects practice language and native language.
2. System checks minimum entry count (default: **10 entries** in the chosen practice language; configurable system setting).
3. If below minimum: block battle start with clear message.

**Matchmaking:**
- Match by `(practice_language, native_language)` pair only. No skill brackets in MVP.
- Wait up to **60 seconds** for a real opponent.
- If no match found: bot battle starts automatically.

**Battle flow:**
- 20 rounds total.
- Each round: show one `source_text` from the current player's eligible entries.
- Show 4 translation options: 1 correct + 3 distractors.
- Distractors: first from the player's own dictionary (same practice language); fall back to system-level shared fallback pool.
- Players have **30 seconds** per round.
- Both players answer independently; results revealed after both answer or time expires.

**Bot behavior:**
- Configurable difficulty: easy (~30% correct), **medium (~60% correct, default)**, hard (~90% correct).
- Bot battles count in history and win rate.

**Result:**
- More correct answers = win. Tie = draw.
- Result stored in `language.pvp.battle` with both player references, round details, outcome.
- Player stats updated: wins / losses / draws / win_rate.

**Disconnection handling:**
- **15-second reconnect grace period.**
- If player does not reconnect within 15s: forfeit. Opponent is awarded a win.
- Battle result saved; forfeited battles appear in history.

**Leaderboard:**
- Ranked by win count.
- Win rate also displayed.
- Filterable by language pair.
- Deleted/anonymized users are removed from visible leaderboard.

**Real-time transport:**
- Redis stores ephemeral live battle state: current round, countdown, submitted answers, matchmaking queue, reconnect grace state.
- Odoo bus/websocket pushes UI events to players.
- Odoo is the authoritative record for final results and stats.

---

## 5. Privacy & Visibility

| Object | Default Visibility | Sharing |
|---|---|---|
| Learning entries | Private to owner | Owner can mark whole list or individual entries as shared |
| Shared entries | Visible to all Language Users | Others can copy (new ownership) |
| Posts/articles | Public after moderator approval | N/A |
| Chat (public channels) | Visible to all Language Users | N/A |
| Chat (private DMs) | Only between participants | Not shareable |
| PvP profile / leaderboard | Public (battle stats only) | No vocabulary exposure |
| Import job logs | Private to owner | Not shared |
| Audio recordings | Private to owner | Not exposed separately |

When user B copies an entry from user A's shared list:
- A new `language.entry` is created owned by B.
- Provenance fields reference A's entry.
- B's entry is independent; B's progress, audio, translations are separate.

---

## 6. Data Retention & GDPR

When a user account is deleted:

| Data | Action |
|---|---|
| Private learning entries | Hard delete |
| Shared/public entries owned by user | Hard delete (copies owned by others are unaffected) |
| User-recorded audio files | Delete from filestore with the entry |
| Auto-generated audio tied to deleted entries | Delete with the entry |
| Chat messages (public channels) | Anonymize: author becomes "Deleted User"; content retained for thread integrity |
| Private DMs | Delete or anonymize; content handling configurable by admin |
| Posts/articles | Anonymize ownership; admin/moderator decides whether to keep published |
| Post comments | Anonymize author; content retained for thread integrity |
| PvP battle history | Anonymize player identity; match records retained for opponent's history |
| Leaderboard | User removed from public leaderboard visibility |
| Import logs | Delete with user account |

GDPR right-to-erasure is a **real requirement direction** for this product. The MVP implementation is pragmatic (not a full legal compliance platform), but the data model must support deletion and anonymization from the start.

---

## 7. Open Decisions (to resolve in later milestones)

| # | Decision | Notes |
|---|---|---|
| OD-1 | `type` in dedup key | Current: excluded. Revisit if user data shows frequent type-collision confusion. |
| OD-2 | Argos Translate uk↔el quality | Two-hop routing. If quality is unacceptable, consider alternative offline library. |
| OD-3 | Greek TTS quality | piper/espeak-ng Greek support is thin. May need a different engine or documented limitation. |
| OD-4 | Auto-enrichment on save | Currently manual. Could be a user-level toggle. |
| OD-5 | PvP skill-based matchmaking | Future enhancement after ELO/win-rate data accumulates. |
| OD-6 | ELO rating system | Future enhancement after win-count leaderboard is stable. |
| OD-7 | Link preview / OG tag scraping | Future enhancement for media links. |
| OD-8 | CSV / .colpkg Anki import | Future extensions after .apkg + .txt are stable. |
| OD-9 | Per-card language auto-detection in Anki | Future enhancement; not default MVP behavior. |
| OD-10 | Sentence length gate for PvP | Very long sentences may degrade gameplay. Consider a configurable max character count for PvP-eligible entries. |
| OD-11 | Trusted-user auto-publish | Future: users above a trust threshold can publish posts without review. |
| OD-12 | Adaptive bot difficulty | Future: bot mirrors user's historical accuracy. |
