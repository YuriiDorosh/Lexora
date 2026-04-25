# Lexora Academy

<div align="center">

**Powered by [Avantgarde Systems](https://avantgarde.systems)**

> An advanced AI-driven language learning ecosystem for mastering **English**, **Ukrainian**, and **Greek** —  
> built on enterprise-grade infrastructure with spaced repetition science, real-time multiplayer duels,  
> LLM-powered vocabulary intelligence, and a premium glassmorphism UI.

[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](#license)
[![Odoo 18](https://img.shields.io/badge/Odoo-18%20Community-875A7B.svg)](https://odoo.com)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB.svg)](https://python.org)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://postgresql.org)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)

</div>

---

## Table of Contents

- [What is Lexora?](#what-is-lexora)
- [Architecture Overview](#architecture-overview)
- [Service Map](#service-map)
- [Feature Catalogue](#feature-catalogue)
- [Tech Stack](#tech-stack)
- [Custom Odoo Modules](#custom-odoo-modules)
- [Module Dependency Graph](#module-dependency-graph)
- [Async Event Bus](#async-event-bus)
- [Portal Routes](#portal-routes)
- [XP Economy](#xp-economy)
- [Quick Start](#quick-start-development)
- [Implementation Status](#implementation-status)
- [Documentation](#documentation)
- [License](#license)

---

## What is Lexora?

Lexora is a **self-hosted, full-stack language learning platform** that goes far beyond flashcard apps.
It combines a battle-tested SRS engine, real-time AI translation, PvP word duels with XP progression,
a curated Gold Vocabulary of 3000+ words, interactive grammar tools, AI roleplay scenarios, and
a Sentence Builder game — all running on your own infrastructure.

**Supported languages:** English (EN) · Ukrainian (UK) · Greek (EL)

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────────┐
                    │              Browser / Client                │
                    └───────────────────┬─────────────────────────┘
                                        │  HTTP / WebSocket
                    ┌───────────────────▼─────────────────────────┐
                    │              Nginx (Reverse Proxy)           │
                    │        SSL · Static files · WS pass-through  │
                    └───────────────────┬─────────────────────────┘
                                        │
                    ┌───────────────────▼─────────────────────────┐
                    │            Odoo 18 (System of Record)        │
                    │  Portal · Auth · Models · Odoo Bus (WS)      │
                    └──┬──────────┬──────────┬────────────┬───────┘
                       │          │          │            │
              Publishes │  Reads / │  WS push │  Redis     │
               events   │  Writes  │  via Bus │  PvP state │
                       │          │          │            │
        ┌──────────────▼──┐  ┌────▼──────┐  │  ┌─────────▼──────┐
        │   RabbitMQ       │  │ PostgreSQL │  │  │   Redis 7      │
        │  (Event Bus)     │  │    (DB)   │  │  │ (Ephemeral PvP)│
        └─┬───┬───┬───┬───┘  └───────────┘  │  └────────────────┘
          │   │   │   │                      │
    ┌─────┘ ┌─┘ ┌─┘ ┌─┘                     │
    │       │   │   │                        │
┌───▼───┐ ┌─▼──┐ ┌─▼────┐ ┌────────┐        │
│ Trans-│ │LLM │ │ Anki │ │ Audio  │        │
│lation │ │Enr.│ │Import│ │  TTS   │        │
│Service│ │Svc │ │ Svc  │ │  Svc   │        │
│FastAPI│ │Qwen│ │FastAP│ │edge-tts│        │
│deep_  │ │1.5B│ │zstd  │ │whisper │        │
│transl.│ │GGUF│ │ bs4  │ │FastAPI │        │
└───────┘ └────┘ └──────┘ └────────┘        │
                                             │
                    ┌────────────────────────┘
                    │  Odoo Bus / WebSocket
                    ▼
              Real-time PvP UI events
              Countdown timers
              Round results push
```

---

## Service Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  HOST MACHINE  (Docker Compose)                                     │
│                                                                     │
│  Port 5433  ──►  nginx ──►  odoo:8069                              │
│  Port 15672 ──►  rabbitmq (management UI)                          │
│  Port 8001  ──►  translation-service                               │
│  Port 8002  ──►  llm-service                                       │
│  Port 8003  ──►  anki-service                                      │
│  Port 8004  ──►  audio-service                                     │
│                                                                     │
│  Internal network: lexora_network                                   │
│  ┌─────────┐  ┌──────────┐  ┌───────┐  ┌───────────┐             │
│  │ postgres│  │ rabbitmq │  │ redis │  │  odoo     │             │
│  │ :5432   │  │ :5672    │  │ :6379 │  │  :8069    │             │
│  └─────────┘  └──────────┘  └───────┘  └───────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Feature Catalogue

### AI Translator (`/translator`)
Real-time synchronous translation between all six language pairs (EN ↔ UK ↔ EL) powered by
`deep_translator` (Google/MyMemory). Translate any text, swap languages with one click, copy
result to clipboard, and save directly to vocabulary. Available to public visitors (translation)
and logged-in users (save to list).

---

### Smart Spaced Repetition (`/my/practice`)

```
New Card ──► Learning ──► Review
   │             │
   │     Grade 0 (Again): interval = 1 day,  n reset
   │     Grade 1 (Hard):  interval × 1.2,   EF − 0.15
   │     Grade 2 (Good):  SM-2 formula,      EF unchanged
   └────► Grade 3 (Easy): interval × 1.3,   EF + 0.15
```

Full SM-2 algorithm. Cards scheduled at scientifically optimal intervals based on recall difficulty.
Four grade buttons, ease factor bounds (1.3 – 3.5), due-card counter in the portal home widget.

---

### PvP Arena (`/my/arena`)

```
User A requests duel           User B joins open challenge
        │                               │
        ▼                               ▼
   [state: open] ──────────────► [state: ongoing]
        │                               │
        │         10 rounds             │
        │  ┌──────────────────────┐     │
        │  │  Show source word    │     │
        │  │  User types answer   │     │
        │  │  Score: +1 if correct│     │
        │  └──────────────────────┘     │
        │                               │
        ▼                               ▼
   [state: finished]  ◄──────────────────
        │
        ▼
   XP transfer: winner +staked, loser −staked (floor 0)
   Stats updated: wins / losses / draws / win_rate
   Leaderboard refreshed
```

Asynchronous duels — no real-time requirement. Challenge any user or the **Lexora Bot** (70% accuracy).
Open challenges visible to all eligible users. Minimum 10 PvP-eligible entries required to participate.

---

### XP Shop (`/my/shop`)

| Item | Cost | Effect |
|---|---|---|
| Streak Freeze | 50 XP | Prevents streak reset for 1 missed day |
| Double XP Booster | 80 XP | Next 5 practice reviews award 2× XP |
| Profile Frame | 100 XP | Cosmetic border on leaderboard |

XP earned through: practice reviews · duel wins · grammar exercises · sentence builder · cloze tests.

---

### Knowledge Hub

**Gold Vocabulary** (`/useful-words`)
- 3184 most common English words
- CEFR levels A1 – C2, part of speech, UK + EL translations
- Tabbed by level, paginated 50/page, one-click "Add to My List"
- PDF export per level

**Grammar Encyclopedia** (`/grammar`)

| Section | Slug |
|---|---|
| All 12 English Tenses | `/grammar/tenses` |
| Irregular Verbs (~200) | `/grammar/irregular-verbs` |
| Articles (a/an/the/∅) | `/grammar/articles` |
| Conditionals 0 – 3 | `/grammar/conditionals` |
| Modal Verbs | `/grammar/modal-verbs` |
| Passive Voice & Reported Speech | `/grammar/passive-reported` |

---

### Grammar Pro — Cloze Tests (`/my/grammar-practice`)
110 fill-in-the-blank exercises across EN (A1–B2) and EL (A1–A2). Covers all 12 tenses,
conditionals, modal verbs, articles, passive voice, reported speech, irregular verbs,
prepositions, and collocations. Multiple-choice format, instant green/red feedback,
CEFR filter, category filter, 5 XP per correct answer.

---

### Sentence Builder (`/my/sentence-builder`)
Word-ordering game. A sentence is split into shuffled tiles — click tiles to reconstruct
the correct order. 5 sentences per session, language + CEFR filters, 10 XP per correct
sentence. Draws from the same exercise dataset as Grammar Pro.

```
Word bank:   [years.]  [lived]  [We]  [in]  [ten]  [this]  [city]  [have]  [for]

Answer tray: [ We ] [ have ] [ lived ] [ in ] [ this ] [ city ] [ for ] [ ten ] [ years. ]

             ✓ Correct!   →  Next sentence
```

---

### AI Situational Roleplay (`/my/roleplay`)
Six curated conversation scenarios powered by the local Qwen2.5-1.5B LLM:

| Scenario | Language focus |
|---|---|
| Café Ordering | Food vocabulary, requests |
| Job Interview | Professional English, tenses |
| Doctor's Visit | Health vocabulary, symptoms |
| Hotel Check-In | Travel vocabulary, formalities |
| Airport Check-In | Directions, numbers |
| Supermarket | Shopping, quantities |

In-context grammar corrections. Full conversation history persisted in Postgres.
Session reset available. Synchronous LLM call (90s timeout).

---

### Natural Speech Hub — Idioms (`/idioms`)
100+ phrasal verbs (EN), idioms (UK), and idioms (EL) with:
- Literal vs idiomatic meaning card flip animation
- CEFR level + category filter
- "Save to Vocabulary" one-click capture

---

### Survival Phrasebook (`/phrasebook`)
Six tourist scenario kits (Hotel · Taxi · Restaurant · Emergency · Shopping · Airport)
with EN / UK / EL side-by-side phrases, copy-to-clipboard, and "Practice in Roleplay" CTA.

---

### Vocabulary Management (`/my/vocabulary`)

```
User types word
      │
      ▼
Language auto-detected (langdetect, threshold 0.7)
      │
      ▼
Dedup check: normalize(source_text) + source_language + owner_id
      │
   ┌──┴──┐
Dupe │     │ New
      │     ▼
      │  Entry created (language.entry)
      │     │
      │     ├── Translation jobs queued (one per learning language)
      │     │        └── RabbitMQ → Translation Service → Google/MyMemory
      │     │
      │     └── User can trigger:
      │              LLM Enrichment (synonyms, antonyms, examples)
      │              TTS generation (edge-tts → espeak-ng fallback)
      │              Audio recording (MediaRecorder API)
      │
      ▼
  "Already exists" inline message
```

---

### PDF Export Suite

| Route | Output |
|---|---|
| `/my/vocabulary/print` | Personal vocabulary (word · translation · example) |
| `/useful-words/print?level=A1` | Gold Vocabulary for one CEFR level |
| `/grammar/<slug>/print` | Full grammar section with styled tables |

Generated server-side via wkhtmltopdf 0.12.6 (Odoo QWeb → PDF). A4 layout, 2-column word grid,
repeating table headers, page-break helpers.

---

### Community Layer

**Public channels** — `/en`, `/uk`, `/el` language channels seeded on install.
All Language Users are auto-joined. "Save from Chat" text-selection popup captures
any selected text directly into vocabulary with language auto-detection.

**Posts & Articles** — Draft → Submit → Moderator review → Publish workflow.
Comments with @mentions. Copy-to-list from post body.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Application monolith | Odoo 18 Community | Portal + ORM + Bus |
| Database | PostgreSQL 16 | All business data |
| Async message bus | RabbitMQ 3 | Durable queues, DLQ |
| Ephemeral state | Redis 7 | PvP battle state only |
| Translation microservice | FastAPI + `deep_translator` | Google → MyMemory fallback |
| LLM microservice | FastAPI + `llama-cpp-python` | Qwen2.5-1.5B Q4_K_M GGUF, CPU-only |
| Anki import microservice | FastAPI + `zstandard` + `beautifulsoup4` | `.apkg` + `.txt` |
| Audio / TTS microservice | FastAPI + `edge-tts` + `faster-whisper` | Online TTS + local STT |
| Reverse proxy | Nginx | SSL · static · WS pass-through |
| Container orchestration | Docker Compose | Dev + prod overlays |
| PDF generation | wkhtmltopdf 0.12.6 | Via Odoo QWeb reports |
| Language detection | `langdetect` 1.0.9 | Threshold 0.7 |
| Frontend framework | Bootstrap 5 + custom `lx-*` CSS | Glassmorphism design system |

---

## Custom Odoo Modules

| Module | Responsibility |
|---|---|
| `language_security` | Security groups, auto-assignment on signup |
| `language_core` | System params, RabbitMQ publisher/consumer, job mixin |
| `language_words` | `language.entry`, dedup, normalization, user profile, portal vocabulary |
| `language_translation` | `language.translation`, job lifecycle, RabbitMQ events |
| `language_enrichment` | `language.enrichment`, LLM job lifecycle |
| `language_audio` | `language.audio`, upload, TTS generation, STT transcription |
| `language_anki_jobs` | `language.anki.job`, import lifecycle, dedup, audio extraction |
| `language_chat` | Public channels, DMs, save-from-chat |
| `language_dashboard` | Leaderboard, popular words, word of the day |
| `language_pvp` | `language.duel`, matchmaking, bot, XP transfer |
| `language_portal` | All portal views: vocabulary, grammar, idioms, phrasebook, roleplay, sentence builder |
| `language_learning` | SRS (`language.review`), XP log, gamification, shop, inventory |

---

## Module Dependency Graph

```
language_security
        │
        ▼
language_core
        │
        ▼
language_words
        │
   ┌────┼────────────────┐
   │    │                │
   ▼    ▼                ▼
lang_  lang_          lang_
trans  enrich         audio
lation ment               │
   │    │             lang_
   │    │             anki_
   │    │             jobs
   └────┴──────┬──────────┘
               │
    ┌──────────┼──────────────────┐
    │          │                  │
    ▼          ▼                  ▼
lang_      lang_pvp          lang_
chat        │                portal
    │       │                    │
    │   lang_dash                │
    │   board                    │
    └───────┴────────────────────┘
                    │
                    ▼
            language_learning
```

---

## Async Event Bus

All four worker microservices communicate with Odoo exclusively via RabbitMQ.
Every message carries a `job_id` UUID for idempotency.

```
Odoo (publisher)                    RabbitMQ                   Worker (consumer)
      │                                 │                              │
      │── translation.requested ───────►│──────────────────────────►  │
      │                                 │                              │ _translate()
      │◄── translation.completed ───────│◄─────────────────────────── │
      │                                 │                              │
      │── enrichment.requested ─────────►│──────────────────────────► │
      │                                 │                              │ _enrich()
      │◄── enrichment.completed ────────│◄─────────────────────────── │
      │                                 │                              │
      │── anki.import.requested ────────►│──────────────────────────► │
      │                                 │                              │ _parse_apkg()
      │◄── anki.import.completed ───────│◄─────────────────────────── │
      │                                 │                              │
      │── audio.generation.requested ───►│──────────────────────────► │
      │                                 │                              │ edge-tts()
      │◄── audio.generation.completed ──│◄─────────────────────────── │
```

Odoo-side consumer: cron-based `basic_get` drainer (every 1 minute, up to 200 messages/queue).
Worker-side: `prefetch_count=1`, always acks to prevent queue wedge.

---

## Portal Routes

### Practice

| Route | Feature | Auth |
|---|---|---|
| `/my/practice` | Daily SRS flashcard queue | User |
| `/my/grammar-practice` | Cloze test exercises | User |
| `/my/sentence-builder` | Word-ordering game | User |
| `/my/roleplay` | AI scenario grid | User |
| `/my/roleplay/<id>` | AI chat session | User |
| `/my/arena` | PvP duel lobby | User |
| `/my/arena/<id>` | Active duel | User |

### Library

| Route | Feature | Auth |
|---|---|---|
| `/useful-words` | Gold Vocabulary (CEFR tabs) | Public |
| `/grammar` | Grammar Encyclopedia index | Public |
| `/grammar/<slug>` | Grammar section detail | Public |
| `/idioms` | Idioms & Phrasal Verbs | User |
| `/phrasebook` | Tourist Phrasebook index | Public |
| `/phrasebook/<scenario>` | Scenario phrases | Public |

### Tools & Account

| Route | Feature | Auth |
|---|---|---|
| `/translator` | AI Translator | Public |
| `/my/vocabulary` | Personal vocabulary list | User |
| `/my/vocabulary/<id>` | Entry detail | User |
| `/my/dashboard` | XP / streak / duel stats | User |
| `/my/shop` | XP Shop | User |
| `/my/inventory` | Owned items | User |
| `/my/leaderboard` | Global leaderboard | User |
| `/my/profile` | Language preferences | User |
| `/my/anki` | Anki import | User |
| `/my/vocabulary/print` | Vocabulary PDF | User |
| `/useful-words/print` | Gold Vocabulary PDF | User |
| `/grammar/<slug>/print` | Grammar PDF | User |

---

## XP Economy

```
XP Sources                         XP Sinks
──────────────────────────────     ──────────────────────────
Practice review (grade Good)  +10  Streak Freeze purchase   −50
Practice review (grade Easy)  +15  Double XP Booster        −80
Grammar Pro correct answer     +5  Profile Frame            −100
Sentence Builder correct      +10
Duel win                      +staked
Duel loss                     −staked (floor 0)
──────────────────────────────
Level = min(20, 1 + floor(√(xp / 50)))
```

Double XP Booster multiplies the XP award for the next 5 practice reviews by 2×.
Streak Freeze prevents the streak counter from resetting for one missed calendar day.

---

## Quick Start (Development)

```bash
# 1. Clone and configure
git clone https://github.com/YuriiDorosh/Lexora.git
cd Lexora
cp env.example .env          # edit passwords and service URLs

# 2. Start the full stack
make up-dev
# Boots: Odoo · Postgres · RabbitMQ · Redis · Nginx
#        Translation · LLM · Anki · Audio services

# 3. First-run database initialization
#    Open http://localhost:5433 → complete Odoo setup wizard, then:
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora \
  --init language_security,language_core,language_words,language_translation,\
language_enrichment,language_audio,language_anki_jobs,language_chat,\
language_dashboard,language_pvp,language_portal,language_learning \
  --stop-after-init

# 4. Open the platform
open http://localhost:5433
```

**Service health checks:**

```bash
curl http://localhost:5433/web/health    # Odoo
curl http://localhost:8001/health        # Translation service
curl http://localhost:8002/health        # LLM service (llm_ready: true after ~90s)
curl http://localhost:8003/health        # Anki service
curl http://localhost:8004/health        # Audio / TTS service
curl http://localhost:15672              # RabbitMQ management UI (guest/guest)
docker exec redis redis-cli ping         # Redis → PONG
```

**Update a module after code changes:**

```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_portal --stop-after-init --no-http
docker restart odoo
```

**Run tests:**

```bash
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --test-enable --no-http --stop-after-init \
  -u language_words,language_translation,language_enrichment,\
language_pvp,language_learning
```

---

## Implementation Status

| Milestone | Feature | Status |
|---|---|---|
| M0 | Infrastructure Foundation | ✅ Complete |
| M1 | Core Module Scaffold + Auth | ✅ Complete |
| M2 | Learning Entries + Dedup | ✅ Complete |
| M3 | Translation Service (RabbitMQ) | ✅ Complete |
| M4 | LLM Enrichment Service | ✅ Complete |
| M4b | Real CPU-only LLM (Qwen2.5-1.5B GGUF) | ✅ Complete |
| M4c | Translation / Enrichment split (`deep_translator`) | ✅ Complete |
| M5 | Anki Import (`.apkg` + `.txt` + Zstd) | ✅ Complete |
| M6 | Audio Recording + TTS (`edge-tts`) + STT (`faster-whisper`) | ✅ Complete |
| M7 | Posts, Articles, Comments | ✅ Complete |
| M8 | Chat, DMs, Save-from-Chat | ✅ Complete |
| M9 | SRS Core + Leaderboard + Vocabulary Pro Dashboard | ✅ Complete |
| M10 | PvP Arena + XP System + Lexora Bot | ✅ Complete |
| M11 | XP Shop (Streak Freeze, Double XP, Profile Frame) | ✅ Complete |
| M12 | Knowledge Hub (Gold Vocabulary + Grammar Encyclopedia) | ✅ Complete |
| M13 | PDF Export Suite | ✅ Complete |
| M14 | Premium Visual Identity (glassmorphism, Avantgarde branding) | ✅ Complete |
| M15 | AI Translator Tool | ✅ Complete |
| M16 | Legal Protection + Documentation | ✅ Complete |
| M17 | AI Situational Roleplay (6 scenarios, Qwen2.5) | ✅ Complete |
| M18 | Grammar Pro — Cloze Tests (110 exercises, EN + EL) | ✅ Complete |
| M18.5 | Header UI Redesign (Practice / Library / Tools dropdowns) | ✅ Complete |
| M19 | Natural Speech Hub — Idioms & Phrasal Verbs | ✅ Complete |
| M20 | Survival Phrasebook — Tourist Kits (6 scenarios, EN/UK/EL) | ✅ Complete |
| M21 | Sentence Builder — Syntax Master (word-ordering game) | ✅ Complete |

---

## Documentation

| Document | Purpose |
|---|---|
| [docs/SPEC.md](docs/SPEC.md) | Full product specification: domain model, features, privacy, PvP rules |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design: services, event catalog, real-time PvP design |
| [docs/PLAN.md](docs/PLAN.md) | Milestone-by-milestone implementation plan (M0–M21) |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture decision records (ADR-001–ADR-028) |
| [docs/TASKS.md](docs/TASKS.md) | Active task tracker and milestone resume point |
| [CLAUDE.md](CLAUDE.md) | AI assistant context: build commands, key invariants, module order |

---

## License

Copyright © 2026 Yurii Dorosh · Avantgarde Systems. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, modification,
distribution, sublicensing, or use — in whole or in part — is strictly prohibited
without express written permission from the copyright holder.

See [LICENSE](LICENSE) for full terms. For licensing inquiries: contact.yuriidorosh@gmail.com
