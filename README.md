# Lexora Academy

**Powered by [Avantgarde Systems](https://avantgarde.systems)**

> An advanced AI-driven language learning ecosystem for mastering English, Ukrainian,
> and Greek — built on enterprise-grade infrastructure with spaced repetition science,
> real-time multiplayer duels, and LLM-powered vocabulary intelligence.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Odoo](https://img.shields.io/badge/Odoo-18_Community-875A7B?logo=odoo&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3-FF6600?logo=rabbitmq&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red)

---

## Table of Contents

- [What is Lexora?](#what-is-lexora)
- [Core Features](#core-features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Custom Odoo Modules](#custom-odoo-modules)
- [Module File Structure](#module-file-structure)
- [Database Schema](#database-schema)
- [Async Event Bus](#async-event-bus)
- [Docker Compose Stack](#docker-compose-stack)
- [Repository Layout](#repository-layout)
- [Quick Start](#quick-start-development)
- [Developer Tooling](#developer-tooling)
- [Documentation](#documentation)
- [Implementation Status](#implementation-status)
- [License](#license)

---

## What is Lexora?

Lexora is a full-stack private language learning platform that goes far beyond
flashcard apps. It combines a battle-tested SRS engine, synchronous AI translation,
PvP word duels with XP progression, a curated Gold Vocabulary of 3000+ words, an
interactive Grammar Encyclopedia, and a premium glassmorphism UI — all self-hosted
and running entirely on your own infrastructure.

**Supported languages:** English · Ukrainian · Greek

---

## Core Features

### AI Translator
Real-time synchronous translation between all three language pairs (en ↔ uk ↔ el)
powered by `deep_translator` (Google/MyMemory backend). Translate any text and save
the result directly to your personal vocabulary in one click.
Route: `/translator`

### Smart Spaced Repetition (SRS)
Full SM-2 algorithm implementation. Cards are scheduled at scientifically optimal
intervals based on recall difficulty. Four grade buttons (Again / Hard / Good / Easy)
adjust ease factor and next-review date. Daily practice queue with due-card counter.
Route: `/my/practice`

### PvP Arena
Asynchronous word duel system. Challenge other learners or the Lexora Bot, stake XP,
play 10 rounds against each other's vocabulary, and climb the global leaderboard.
XP economy with Streak Freeze, Double XP Booster, and Profile Frame shop items.
Route: `/my/arena`

### Knowledge Hub
- **Gold Vocabulary** — 3184 most common English words tagged by CEFR level (A1–B2),
  part of speech, and Ukrainian/Greek translations. Paginated 50/page with
  one-click "Add to My List" buttons.
- **Grammar Encyclopedia** — 6 comprehensive sections: All 12 Tenses, Irregular Verbs,
  Articles, Conditionals, Modal Verbs, Passive Voice & Reported Speech.

Routes: `/useful-words` · `/grammar`

### PDF Export Suite
Printable cheat sheets generated server-side via wkhtmltopdf:
- Personal vocabulary (word + translation + example sentence)
- Gold Vocabulary filtered by CEFR level
- Any Grammar section

Routes: `/my/vocabulary/print` · `/useful-words/print?level=A1` · `/grammar/<slug>/print`

### Vocabulary Management
Manual entry with automatic language detection, normalization-based deduplication,
Anki `.apkg` / `.txt` import with audio extraction, inline translation editing,
LLM enrichment (synonyms, antonyms, example sentences, explanation), audio recording
and TTS generation.
Route: `/my/vocabulary`

### Community Layer
Public language channels and private DMs (built on Odoo Discuss), posts and articles
with moderator review workflow, comments with @mentions, and "Save from Chat /
Save from Post" inline vocabulary capture.
Routes: `/posts` · `/my/posts`

### AI Situational Roleplay
Six curated conversation scenarios (café ordering, job interview, airport check-in,
doctor's visit, hotel check-in, supermarket) powered by the local Qwen2.5 LLM.
In-context grammar corrections, glassmorphism chat UI, and session persistence.
Route: `/my/roleplay`

### Grammar Pro — Cloze Tests
110 fill-in-the-blank exercises covering all 12 tenses, conditionals, modal verbs,
articles, and more. CEFR A1–B2 filter, instant green/red feedback, XP rewards.
Route: `/my/grammar-practice`

### Premium Visual Identity
Dark animated hero section, glassmorphism cards, Inter + Montserrat typography,
Avantgarde Systems branding, and a fully custom CSS design system (`lx-*` tokens).

---

## System Architecture

```
                     ┌─────────────────────────────────────────────┐
                     │               Browser / Client               │
                     │  HTTP · WebSocket · JSON-RPC · PDF download  │
                     └────────────────────┬────────────────────────┘
                                          │ :443 / :80
                     ┌────────────────────▼────────────────────────┐
                     │              Nginx 1.27 (alpine)             │
                     │   SSL termination · static files · WS proxy  │
                     │   /websocket → odoo:8072                     │
                     └────────────────────┬────────────────────────┘
                                          │ :8069 / :8072
                     ┌────────────────────▼────────────────────────┐
                     │           Odoo 18 Community (4 workers)      │
                     │                                              │
                     │  ┌─────────────┐  ┌────────────────────┐   │
                     │  │  Portal /   │  │   Odoo Backend /   │   │
                     │  │  Website    │  │   Admin Interface  │   │
                     │  └─────────────┘  └────────────────────┘   │
                     │                                              │
                     │  ┌──────────────────────────────────────┐  │
                     │  │          Custom Modules (12)          │  │
                     │  │  security · core · words · trans ·   │  │
                     │  │  enrich · audio · anki · chat ·      │  │
                     │  │  dashboard · pvp · portal · learning  │  │
                     │  └──────────────────────────────────────┘  │
                     │                                              │
                     │  ┌──────────────┐  ┌──────────────────┐   │
                     │  │  RabbitMQ    │  │  Redis 7 client  │   │
                     │  │  Publisher   │  │  (PvP state)     │   │
                     │  └──────┬───────┘  └──────────────────┘   │
                     └─────────┼────────────────────────────────────┘
                               │ AMQP 0-9-1
          ┌────────────────────▼──────────────────────────┐
          │                RabbitMQ 3 (management UI)      │
          │          Durable queues · persistent messages   │
          └──┬────────────┬───────────────┬───────────────┘
             │            │               │               │
    ┌────────▼──┐  ┌──────▼──────┐  ┌────▼──────┐  ┌────▼──────────┐
    │Translation│  │LLM Enrichmt │  │   Anki    │  │  Audio / TTS  │
    │ FastAPI   │  │  FastAPI    │  │  FastAPI  │  │  FastAPI      │
    │           │  │             │  │           │  │               │
    │deep_trans │  │llama-cpp-py │  │zstandard  │  │edge-tts       │
    │Google/    │  │Qwen2.5-1.5B │  │bs4 / zip  │  │faster-whisper │
    │MyMemory   │  │GGUF Q4_K_M  │  │SQLite     │  │espeak-ng      │
    │:8001      │  │:8002        │  │:8003      │  │:8004          │
    └───────────┘  └─────────────┘  └───────────┘  └───────────────┘

    ┌───────────────────────┐     ┌───────────────────────────────┐
    │   PostgreSQL 16       │     │         Redis 7               │
    │                       │     │                               │
    │  Odoo ORM (business   │     │  PvP ephemeral state only:    │
    │  records, sessions,   │     │  matchmaking queues, round    │
    │  filestore metadata)  │     │  state, reconnect grace TTLs  │
    │  :5432                │     │  :6379                        │
    └───────────────────────┘     └───────────────────────────────┘
```

### Design Principles

| Principle | Implementation |
|---|---|
| **Single system of record** | All business data lives in Odoo / PostgreSQL |
| **Stateless processors** | Worker services (FastAPI) own no persistent state |
| **Async by default** | Translation, enrichment, Anki import, TTS all via RabbitMQ |
| **Sync exception** | Roleplay and Translator use direct HTTP (immediate response required) |
| **Idempotency** | Every async job carries a UUID `job_id`; workers check terminal state before reprocessing |
| **CPU-first** | No GPU assumed; LLM and Whisper tuned for AVX-only 8 GiB servers |

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Application monolith | Odoo 18 Community | 4 prefork workers |
| Database | PostgreSQL 16 | pg_trgm extension for fuzzy search |
| Async message bus | RabbitMQ 3 | Durable queues, persistent messages |
| Ephemeral PvP state | Redis 7 | TTL-keyed battle state; NOT session store |
| Translation service | FastAPI + `deep_translator` | Google primary / MyMemory fallback |
| LLM enrichment service | FastAPI + `llama-cpp-python` | Qwen2.5-1.5B GGUF Q4_K_M, CPU-only |
| Anki import service | FastAPI + `zstandard` + `beautifulsoup4` | `.apkg` (Zstd) + `.txt` (TSV) |
| Audio / TTS service | FastAPI + `edge-tts` + `faster-whisper` | Microsoft neural voices; Whisper `base` STT |
| Reverse proxy | Nginx 1.27 | WebSocket pass-through, SSL termination |
| Container orchestration | Docker Compose | Single-host; prod overlay planned |
| PDF generation | wkhtmltopdf 0.12.6 via Odoo QWeb | A4, 2-column print layout |
| Fuzzy search | `base_search_fuzzy` OCA addon + pg_trgm | Vocabulary and cross-language lookup |
| Language detection | `langdetect` 1.0.9 | Source language prefill; 0.7 confidence threshold |

---

## Custom Odoo Modules

All modules live under `src/addons/`. Install order matters — each module declares its
dependencies in `__manifest__.py`.

```
language_security
└── language_core
    ├── language_words
    │   ├── language_translation
    │   ├── language_enrichment
    │   ├── language_audio
    │   └── language_anki_jobs
    ├── language_chat
    ├── language_dashboard
    ├── language_pvp
    ├── language_portal
    └── language_learning
```

### Module Responsibilities

| Module | Key Models | Responsibility |
|---|---|---|
| `language_security` | — | Security groups, record rules, portal signup hook |
| `language_core` | `language.job.status.mixin` | System params, RabbitMQ publisher/consumer, job mixin |
| `language_words` | `language.entry` `language.user.profile` `language.lang` `language.media.link` | Vocabulary CRUD, dedup, normalization, language detection, sharing |
| `language_translation` | `language.translation` | Translation job lifecycle, `translation.*` event handling |
| `language_enrichment` | `language.enrichment` | LLM enrichment job lifecycle, `enrichment.*` event handling |
| `language_audio` | `language.audio` | User recording upload, TTS generation, `audio.*` event handling |
| `language_anki_jobs` | `language.anki.job` | Anki import job lifecycle, dedup on completion, audio extraction |
| `language_chat` | `discuss.channel` (extended) | Public language channels, DMs, save-from-chat |
| `language_dashboard` | — | Word of the day cron, popular words, community aggregations |
| `language_pvp` | `language.duel` `language.duel.line` | PvP duels, Lexora Bot, XP transfer, leaderboard |
| `language_portal` | `language.scenario` `language.scenario.session` `language.seeded.word` `language.grammar.section` `language.shop.item` `language.user.item` | All portal routes: vocabulary, translator, roleplay, grammar, shop, PDF export, library |
| `language_learning` | `language.review` `language.user.profile` (extended) `language.xp.log` | SM-2 SRS engine, XP/streak/level gamification, leaderboard, dashboard |

---

## Module File Structure

Every custom module follows the standard Odoo 18 layout:

```
src/addons/language_<name>/
├── __init__.py                    # post_init_hook / post_update_hook (if needed)
├── __manifest__.py                # module metadata, depends, data file list
│
├── models/
│   ├── __init__.py
│   ├── language_<entity>.py       # ORM model definition
│   └── ...
│
├── controllers/
│   ├── __init__.py
│   └── portal.py                  # HTTP routes (Odoo Controller)
│
├── views/
│   ├── <model>_views.xml          # backend list/form/search views
│   ├── portal_<feature>.xml       # QWeb portal templates
│   └── pdf_<feature>.xml          # QWeb PDF report templates (language_portal)
│
├── security/
│   ├── ir.model.access.csv        # CRUD rights per group
│   └── record_rules.xml           # row-level access rules
│
├── data/
│   ├── ir_cron_<name>.xml         # scheduled actions
│   ├── website_menus.xml          # navbar entries
│   ├── <seed_data>.xml            # XML fixture data (noupdate="1")
│   └── <seed_data>.py             # Python seed data (importlib-loaded in hook)
│
├── static/
│   └── src/css/
│       └── premium_ui.css         # custom CSS design system (language_portal)
│
└── tests/
    ├── __init__.py
    └── test_<feature>.py          # pytest-style Odoo test cases
```

### Key Non-Standard Patterns

| Pattern | Where | Why |
|---|---|---|
| `importlib.util.spec_from_file_location` for seed data | `language_portal/__init__.py` | Absolute import in hook context where relative imports fail |
| `_inherit = 'language.entry'` with new field only | `language_audio`, `language_enrichment`, `language_translation` | Adds `audio_ids`, `enrichment_ids`, `translation_ids` to entry without modifying `language_words` |
| `"language.xp.log" in request.env.registry` guard | `language_portal/controllers/` | Loose coupling — XP awards degrade gracefully if `language_learning` is not installed |
| QWeb inheritance via `xpath` with `position="after"` | `portal_audio.xml`, `portal_enrichment.xml` | Injects sections into the entry detail page without touching the parent template |
| `noupdate="0"` on scenario XML | `roleplay_scenarios.xml` | Allows prompt updates via `--update language_portal` without delete/re-insert |

---

## Database Schema

All tables are managed by Odoo ORM. Below are the key tables and relationships.

### Core Domain

```
┌─────────────────────────────────────────────────────────────────────┐
│                         language_entry                               │
├───────────────────────┬─────────────────────────────────────────────┤
│ id                    │ Integer PK                                   │
│ type                  │ Selection: word/phrase/sentence/collocation  │
│ source_text           │ Char (raw user input)                        │
│ normalized_text       │ Char (dedup key component, computed on save) │
│ source_language       │ Selection: en/uk/el                          │
│ owner_id              │ Many2one → res_users                         │
│ is_shared             │ Boolean (default False)                      │
│ status                │ Selection: active/archived                   │
│ created_from          │ Selection: manual/anki_import/copied_from_*  │
│ copied_from_user_id   │ Many2one → res_users (nullable)              │
│ copied_from_entry_id  │ Many2one → language_entry (nullable)         │
│ copied_from_post_id   │ Many2one → language_post (nullable)          │
│ pvp_eligible          │ Boolean (computed: has completed translation) │
└───────────────────────┴─────────────────────────────────────────────┘
         │ One2many                │ One2many              │ One2many
         ▼                        ▼                       ▼
┌─────────────────┐   ┌──────────────────┐   ┌───────────────────┐
│language_trans-  │   │language_enrich-  │   │  language_audio   │
│lation           │   │ment              │   │                   │
├─────────────────┤   ├──────────────────┤   ├───────────────────┤
│ entry_id        │   │ entry_id         │   │ entry_id          │
│ target_language │   │ language         │   │ audio_type        │
│ translated_text │   │ synonyms (JSON)  │   │ language          │
│ job_id (UUID)   │   │ antonyms (JSON)  │   │ attachment_id     │
│ status          │   │ example_sents    │   │ job_id (UUID)     │
│ error_message   │   │ explanation      │   │ status            │
│                 │   │ job_id (UUID)    │   │ tts_engine        │
│ UNIQUE(entry,   │   │ status           │   │ file_size_bytes   │
│   target_lang)  │   │ UNIQUE(entry,    │   │ transcription     │
│                 │   │   language)      │   │ UNIQUE(entry,     │
└─────────────────┘   └──────────────────┘   │   type, language) │
                                              └───────────────────┘
```

### User Profile & Gamification

```
┌──────────────────────────────────────────────────────────────────┐
│                    language_user_profile                          │
├──────────────────────┬───────────────────────────────────────────┤
│ user_id              │ Many2one → res_users (UNIQUE)             │
│ native_language      │ Selection: en/uk/el                       │
│ default_source_lang  │ Selection: en/uk/el                       │
│ is_shared_list       │ Boolean                                   │
│ pvp_total_battles    │ Integer                                    │
│ pvp_wins             │ Integer                                    │
│ pvp_losses           │ Integer                                    │
│ pvp_draws            │ Integer                                    │
│ pvp_win_rate         │ Float (computed)                           │
│ xp_total             │ Integer (gamification — from language_lrng)│
│ current_streak       │ Integer                                    │
│ longest_streak       │ Integer                                    │
│ last_practice_date   │ Date                                       │
│ level                │ Integer (computed: 1 + floor(sqrt(xp/50)))│
└──────────────────────┴───────────────────────────────────────────┘
         │ Many2many
         ▼
┌───────────────────┐          ┌──────────────────────────────┐
│   language_lang   │          │      language_xp_log         │
├───────────────────┤          ├──────────────────────────────┤
│ code  (en/uk/el)  │          │ user_id                      │
│ name  (English…)  │          │ amount (Integer, +/-)        │
└───────────────────┘          │ reason (practice/duel_win/…) │
                               │ duel_id (soft ref Integer)   │
                               │ date                         │
                               └──────────────────────────────┘
```

### SRS (Spaced Repetition)

```
┌──────────────────────────────────────────────────────────────────┐
│                      language_review                              │
├──────────────────────┬───────────────────────────────────────────┤
│ entry_id             │ Many2one → language_entry                 │
│ user_id              │ Many2one → res_users                      │
│ state                │ Selection: new/learning/review            │
│ next_review_date     │ Date                                       │
│ last_review_date     │ Date                                       │
│ repetitions          │ Integer (n in SM-2)                       │
│ interval             │ Integer (days until next review)          │
│ ease_factor          │ Float (default 2.5, min 1.3, max 3.5)    │
│ total_reviews        │ Integer                                    │
│ correct_reviews      │ Integer                                    │
│ UNIQUE(user_id, entry_id)                                        │
└──────────────────────┴───────────────────────────────────────────┘
```

**SM-2 algorithm grades:**

| Grade | Button | Effect |
|---|---|---|
| 0 | Again | n=0, interval=1d, EF unchanged, state→learning |
| 1 | Hard | n unchanged, interval×1.2, EF−=0.15 |
| 2 | Good | n+1, interval via SM-2, EF unchanged, state→review |
| 3 | Easy | n+1, interval×1.3, EF+=0.15, state→review |

### PvP Arena

```
┌──────────────────────────────────────────────────────────────────┐
│                       language_duel                               │
├──────────────────────┬───────────────────────────────────────────┤
│ challenger_id        │ Many2one → res_users                      │
│ opponent_id          │ Many2one → res_users (nullable)           │
│ state                │ Selection: open/ongoing/finished/cancel   │
│ winner_id            │ Many2one → res_users (nullable)           │
│ xp_staked            │ Integer (default 10)                      │
│ practice_language    │ Selection: en/uk/el                       │
│ native_language      │ Selection: en/uk/el                       │
│ rounds_total         │ Integer (default 10)                      │
│ challenger_score     │ Integer                                    │
│ opponent_score       │ Integer                                    │
│ start_date           │ Datetime                                   │
│ end_date             │ Datetime                                   │
└──────────────────────┴───────────────────────────────────────────┘
         │ One2many
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                     language_duel_line                            │
├──────────────────────┬───────────────────────────────────────────┤
│ duel_id              │ Many2one → language_duel (cascade)        │
│ player_id            │ Many2one → res_users                      │
│ entry_id             │ Many2one → language_entry                 │
│ round_number         │ Integer (1-based)                         │
│ correct              │ Boolean                                    │
│ answer_given         │ Char                                       │
│ time_taken_seconds   │ Float                                      │
└──────────────────────┴───────────────────────────────────────────┘
```

### XP Shop

```
┌─────────────────────────────────────┐    ┌───────────────────────────────────┐
│         language_shop_item          │    │       language_user_item           │
├──────────────────────┬──────────────┤    ├─────────────────┬─────────────────┤
│ name                 │ Char         │    │ user_id         │ Many2one→users  │
│ description          │ Text         │◄───│ item_id         │ Many2one→item   │
│ xp_cost              │ Integer      │    │ quantity        │ Integer         │
│ item_type            │ Selection:   │    │ activated_at    │ Datetime        │
│                      │  streak_freeze│   │ expires_at      │ Datetime        │
│                      │  double_xp   │    └─────────────────┴─────────────────┘
│                      │  profile_frame│
│ icon                 │ Char (emoji) │
│ is_active            │ Boolean      │
└──────────────────────┴──────────────┘
```

### Knowledge Hub & Roleplay

```
┌────────────────────────────┐    ┌──────────────────────────────────┐
│   language_seeded_word     │    │     language_grammar_section     │
├────────────────────────────┤    ├──────────────────────────────────┤
│ word        Char           │    │ title        Char                │
│ cefr_level  Selection(A1…) │    │ slug         Char (unique)       │
│ pos         Char           │    │ category     Selection           │
│ uk_trans    Char           │    │ content_html Html                │
│ el_trans    Char           │    │ sequence     Integer             │
│ sort_order  Integer        │    │ is_published Boolean             │
└────────────────────────────┘    └──────────────────────────────────┘

┌──────────────────────────────┐    ┌────────────────────────────────────┐
│     language_scenario        │    │    language_scenario_session       │
├──────────────────────────────┤    ├────────────────────────────────────┤
│ name           Char          │    │ scenario_id  Many2one→scenario     │
│ description    Char          │    │ user_id      Many2one→res_users    │
│ icon           Char (emoji)  │◄───│ chat_history Text (JSON array)     │
│ target_language Selection    │    │ UNIQUE(scenario_id, user_id)       │
│ initial_prompt Text          │    └────────────────────────────────────┘
│ is_active      Boolean       │
│ sequence       Integer       │
└──────────────────────────────┘
```

### Anki Import Jobs

```
┌──────────────────────────────────────────────────────────────────┐
│                      language_anki_job                            │
├──────────────────────┬───────────────────────────────────────────┤
│ user_id              │ Many2one → res_users                      │
│ filename             │ Char                                       │
│ file_format          │ Selection: apkg/txt                       │
│ source_language_id   │ Many2one → language_lang                  │
│ target_language_id   │ Many2one → language_lang (nullable)       │
│ field_mapping        │ Text (JSON: {source: int, translation: int})│
│ job_id               │ Char (UUID, auto-set on create)           │
│ status               │ Selection: pending/processing/completed/failed│
│ count_created        │ Integer                                    │
│ count_skipped        │ Integer                                    │
│ count_failed         │ Integer                                    │
│ details_log          │ Text (JSON: {skipped: [...], failed: [...]})│
│ error_message        │ Text                                       │
└──────────────────────┴───────────────────────────────────────────┘
```

### Deduplication Invariant

```
Dedup key = normalize(source_text) + source_language + owner_id

normalize():
  1. Unicode NFC
  2. Lowercase
  3. Strip leading/trailing whitespace
  4. Collapse internal whitespace to single space
  5. Normalize smart quotes/apostrophes/dashes to ASCII
  6. Strip trailing sentence-ending punctuation (.!?) — dedup only, not stored

type is NOT in the dedup key.
On collision: skip + report count; never overwrite existing data.
```

---

## Async Event Bus

All heavy processing flows through RabbitMQ. Odoo publishes a job and polls result
queues via a 1-minute cron (`basic_get` drain, ADR-023).

```
                    ┌─────────────────────┐
                    │        Odoo         │
                    │   (publishes job)   │
                    └──────────┬──────────┘
                               │ AMQP publish
                               ▼
                    ┌─────────────────────┐
                    │    RabbitMQ queue   │
                    │  (durable, persist) │
                    └──────────┬──────────┘
                               │ basic_consume (prefetch=1)
                               ▼
                    ┌─────────────────────┐
                    │   Worker service    │
                    │   (FastAPI thread)  │
                    └──────────┬──────────┘
                               │ AMQP publish result
                               ▼
                    ┌─────────────────────┐
                    │   Result queue      │
                    └──────────┬──────────┘
                               │ Odoo cron drains (every 1 min)
                               ▼
                    ┌─────────────────────┐
                    │   Odoo updates DB   │
                    │   status → completed│
                    └─────────────────────┘
```

### Event Catalog

| Queue (requested) | Publisher | Queue (result) | Consumer |
|---|---|---|---|
| `translation.requested` | Odoo | `translation.completed` / `.failed` | Odoo cron |
| `enrichment.requested` | Odoo | `enrichment.completed` / `.failed` | Odoo cron |
| `anki.import.requested` | Odoo | `anki.import.completed` / `.failed` | Odoo cron |
| `audio.generation.requested` | Odoo | `audio.generation.completed` / `.failed` | Odoo cron |
| `audio.transcription.requested` | Odoo | `audio.transcription.completed` / `.failed` | Odoo cron |

### Message Envelope

Every message (in both directions) uses this standard envelope:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "translation.requested",
  "payload": {
    "source_text": "apple",
    "source_language": "en",
    "target_language": "uk",
    "entry_id": 42
  }
}
```

Workers ack **only after** a durable write. On failure, the fail event is published
before the ack. `job_id` lookup prevents duplicate processing on redelivery.

### Sync Exceptions (Direct HTTP, No RabbitMQ)

Two features require an immediate response and bypass the queue:

| Feature | Endpoint | Caller |
|---|---|---|
| AI Translator | `POST /translate` on translation service | Odoo portal controller |
| AI Roleplay turn | `POST /roleplay` on LLM service | Odoo portal controller |

```python
# Pattern used in both sync features (portal controller side):
resp = requests.post(f"{LLM_SVC}/roleplay", json={...}, timeout=90)
resp.raise_for_status()
data = json.loads(resp.content.decode("utf-8", errors="replace"))
```

---

## Docker Compose Stack

```
docker_compose/
├── db/                       # PostgreSQL 16
│   └── docker-compose.yml    # :5432, lexora volume
│
├── odoo/                     # Odoo 18 + observability
│   ├── Dockerfile            # FROM odoo:18, pip base-requirements
│   ├── docker-compose.yml    # :8069/:8072, nginx, loki, promtail
│   └── nginx.conf            # WebSocket proxy, static files
│
├── nginx/                    # Standalone Nginx (prod overlay)
│   ├── Dockerfile            # FROM nginx:1.27-alpine
│   └── nginx.conf
│
├── rabbitmq/                 # RabbitMQ 3 management
│   └── docker-compose.yml    # :5672 (AMQP), :15672 (UI)
│
├── redis/                    # Redis 7 alpine
│   └── docker-compose.yml    # :6379, AOF persistence
│
├── translation/              # Translation FastAPI worker
│   ├── Dockerfile            # python:3.11-slim
│   └── docker-compose.yml    # :8001, TRANSLATE_* env vars
│
├── llm/                      # LLM Enrichment FastAPI worker
│   ├── Dockerfile            # python:3.11-slim + build-essential/cmake
│   └── docker-compose.yml    # :8002, llm_models volume, LLM_* env vars
│
├── anki/                     # Anki Import FastAPI worker
│   ├── Dockerfile            # python:3.11-slim
│   └── docker-compose.yml    # :8003
│
└── audio/                    # Audio/TTS FastAPI worker
    ├── Dockerfile            # python:3.11-slim + ffmpeg + espeak-ng
    └── docker-compose.yml    # :8004, audio_models volume, TTS_* env vars
```

### Port Map

| Service | Internal | Host (dev) |
|---|---|---|
| Odoo (via Nginx) | 80 | **5433** |
| Odoo direct | 8069 | — (internal only) |
| Odoo WebSocket | 8072 | — (internal only) |
| PostgreSQL | 5432 | 5432 |
| RabbitMQ AMQP | 5672 | 5672 |
| RabbitMQ Management UI | 15672 | **15672** |
| Redis | 6379 | 6379 |
| Translation service | 8000 | **8001** |
| LLM service | 8000 | **8002** |
| Anki service | 8000 | **8003** |
| Audio service | 8000 | **8004** |

---

## Repository Layout

```
Lexora/
├── src/
│   ├── addons/                       # All custom Odoo modules
│   │   ├── language_security/
│   │   ├── language_core/
│   │   ├── language_words/
│   │   ├── language_translation/
│   │   ├── language_enrichment/
│   │   ├── language_audio/
│   │   ├── language_anki_jobs/
│   │   ├── language_chat/
│   │   ├── language_dashboard/
│   │   ├── language_pvp/
│   │   ├── language_portal/
│   │   ├── language_learning/
│   │   ├── base_search_fuzzy/        # OCA addon (fuzzy vocab search)
│   │   ├── password_security/        # OCA addon (password policy)
│   │   ├── web_notify/               # OCA addon (toast notifications)
│   │   ├── website_require_login/    # OCA addon (auth gate)
│   │   └── website_menu_by_user_status/ # OCA addon (conditional nav)
│   └── configs/
│       └── odoo.conf                 # Odoo configuration (workers=4, etc.)
│
├── services/                         # FastAPI microservices
│   ├── translation/
│   │   ├── main.py                   # Consumer + /translate sync endpoint
│   │   └── requirements.txt
│   ├── llm/
│   │   ├── main.py                   # Consumer + /enrich + /roleplay endpoints
│   │   └── requirements.txt
│   ├── anki/
│   │   ├── main.py                   # Consumer + .apkg/.txt parsers
│   │   ├── requirements.txt
│   │   └── tests/
│   │       └── test_parsers.py       # 22 parser unit tests
│   └── audio/
│       ├── main.py                   # Consumer + edge-tts + faster-whisper
│       └── requirements.txt
│
├── docker_compose/                   # Per-service Docker Compose files
│   ├── db/ odoo/ nginx/ rabbitmq/
│   ├── redis/ translation/ llm/
│   ├── anki/ audio/
│   └── pgadmin/ adminer/             # Optional DB tooling
│
├── requirements/
│   ├── base-requirements.txt         # Odoo container pip deps (langdetect, redis, etc.)
│   └── dev-requirements.txt          # Developer tools (ruff, mypy, bandit, etc.)
│
├── docs/
│   ├── SPEC.md                       # Product specification
│   ├── ARCHITECTURE.md               # System design
│   ├── PLAN.md                       # Milestone implementation plan (M0–M21)
│   ├── DECISIONS.md                  # ADR-001 through ADR-028
│   └── TASKS.md                      # Active task tracker / resume point
│
├── .github/
│   ├── workflows/
│   │   ├── lint.yml                  # Ruff + Mypy + Bandit + Hadolint + XMLlint
│   │   ├── test.yml                  # FastAPI pytest matrix + Odoo module tests
│   │   ├── security.yml              # pip-audit + TruffleHog + Bandit SARIF
│   │   ├── docker-build.yml          # Build all 5 Docker images
│   │   └── pr-check.yml              # Conventional Commits + branch name check
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.yml
│       └── feature_request.yml
│
├── backups/                          # pg_restore targets
├── logs/                             # Nginx + app logs
├── pyproject.toml                    # Ruff / Mypy / pytest / Bandit config
├── .pre-commit-config.yaml           # pre-commit hooks
├── .editorconfig                     # Editor formatting rules
├── Makefile                          # Developer shortcuts
├── env.example                       # Environment variable template
├── CLAUDE.md                         # AI assistant context file
└── LICENSE                           # Proprietary — All rights reserved
```

---

## Quick Start (Development)

```bash
# 1. Clone and configure
git clone https://github.com/YuriiDorosh/Lexora.git
cd Lexora
cp env.example .env          # fill in RABBITMQ_PASS, etc.

# 2. Start the full stack
make up-dev                  # Odoo + Postgres + RabbitMQ + Redis + Nginx
                             # + Translation + LLM + Anki + Audio

# 3. Initialize the database (first run only)
#    Open http://localhost:5433 and complete the Odoo setup wizard, then:
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora \
  --init language_security,language_core,language_words,language_translation,\
language_enrichment,language_audio,language_anki_jobs,language_chat,\
language_dashboard,language_pvp,language_portal,language_learning \
  --stop-after-init

# 4. Access the platform
open http://localhost:5433
```

**Health checks:**

```bash
curl http://localhost:5433/web/health     # Odoo ({"status":"pass"})
curl http://localhost:8001/health         # Translation service
curl http://localhost:8002/health         # LLM service
curl http://localhost:8003/health         # Anki service
curl http://localhost:8004/health         # Audio service
curl http://localhost:15672               # RabbitMQ management UI (guest/guest)
```

**Common Makefile targets:**

```bash
make up-dev                  # start everything
make down-dev                # stop everything
make logs-odoo               # tail Odoo logs
make logs-translation        # tail translation service logs
make up-llm-no-cache         # rebuild LLM image (after model change)
make load-backup FILE=x.dump # restore PostgreSQL from backup
make ps-dev                  # list all running dev containers
```

**Update a single module:**

```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http
docker restart odoo          # reload routes into running workers
```

---

## Developer Tooling

```bash
# Install all dev tools
make install-dev             # pip install -r requirements/dev-requirements.txt

# Lint (ruff) — checks all service files and Odoo addons
make lint

# Format (ruff format)
make fmt                     # apply formatting
make fmt-check               # check only (used by CI)

# Type check (mypy — FastAPI services only)
make typecheck

# Security scan (bandit)
make security

# Dependency audit (pip-audit per service)
make audit

# Run all checks in sequence (matches CI)
make check

# pre-commit hooks
make pre-commit-install      # install hooks into .git/hooks/
make pre-commit-run          # run against all files
```

### CI/CD Pipelines (`.github/workflows/`)

| Workflow | Trigger | Jobs |
|---|---|---|
| `lint.yml` | Push to main/feature branches, PRs | Ruff lint + format, Mypy, Bandit, Hadolint, XMLlint |
| `test.yml` | PRs to main, `[test]` commits | FastAPI pytest matrix, Odoo module tests (postgres service) |
| `security.yml` | Push to main, PRs | pip-audit per service, TruffleHog secrets scan, Bandit SARIF |
| `docker-build.yml` | Changes to docker_compose/ or services/ | Build all 5 images with GHA cache |
| `pr-check.yml` | PR opened/edited/synchronized | Conventional Commits title, branch name convention |

**Commit convention:** `type(scope): description`

```
feat(M19): add idioms hub with phrasal verbs
fix(audio): handle edge-tts timeout on slow networks
docs(architecture): update database schema diagram
ci(lint): add DL3059 to hadolint ignore list
```

---

## Documentation

| Document | Purpose |
|---|---|
| [docs/SPEC.md](docs/SPEC.md) | Full product specification: domain model, features, privacy, PvP rules |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design: services, event catalog, real-time PvP design |
| [docs/PLAN.md](docs/PLAN.md) | Milestone-by-milestone implementation plan (M0–M21) |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture decision records (ADR-001–ADR-028) |
| [CLAUDE.md](CLAUDE.md) | AI assistant context: build commands, key invariants, module order |
| [docs/TASKS.md](docs/TASKS.md) | Active task tracker — resume point for interrupted sessions |

---

## Implementation Status

| Milestone | Feature | Status |
|---|---|---|
| M0 | Infrastructure Foundation | ✅ Complete |
| M1 | Core Module Scaffold + Auth | ✅ Complete |
| M2 | Learning Entries + Dedup | ✅ Complete |
| M3 | Translation Service (RabbitMQ) | ✅ Complete |
| M4 | LLM Enrichment Service | ✅ Complete |
| M4b | Real CPU-only LLM (Qwen2.5-1.5B) | ✅ Complete |
| M4c | Translation / Enrichment split | ✅ Complete |
| M5 | Anki Import (.apkg + .txt) | ✅ Complete |
| M6 | Audio Recording + TTS | ✅ Complete |
| M7 | Posts, Articles, Comments | ✅ Complete |
| M8 | Chat & DMs | ✅ Complete |
| M9 | SRS Core + Dashboards | ✅ Complete |
| M10 | PvP Arena + XP System | ✅ Complete |
| M11 | XP Shop | ✅ Complete |
| M12 | Knowledge Hub | ✅ Complete |
| M13 | PDF Export Suite | ✅ Complete |
| M14 | Premium Visual Identity | ✅ Complete |
| M15 | AI Translator Tool | ✅ Complete |
| M16 | Legal Protection + Documentation | ✅ Complete |
| M17 | AI Situational Roleplay | ✅ Complete |
| M18 | Grammar Pro — Cloze Tests | ✅ Complete |
| M18.5 | Header UI Redesign | 🗓 Planned |
| M19 | Natural Speech Hub (Idioms & Phrasal Verbs) | 🗓 Planned |
| M20 | Survival Phrasebook (Tourist Kits) | 🗓 Planned |
| M21 | Sentence Builder (Syntax Master) | 🗓 Planned |

---

## License

Copyright (c) 2026 Yurii Dorosh & Avantgarde Systems. All rights reserved.

This software is proprietary. Unauthorized copying, modification, distribution,
or use is strictly prohibited. See [LICENSE](LICENSE) for full terms.
