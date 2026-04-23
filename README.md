# Lexora Academy

**Powered by [Avantgarde Systems](https://avantgarde.systems)**

> An advanced AI-driven language learning ecosystem for mastering English, Ukrainian,
> and Greek — built on enterprise-grade infrastructure with spaced repetition science,
> real-time multiplayer duels, and LLM-powered vocabulary intelligence.

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
In-context grammar corrections displayed in brackets. Glassmorphism chat UI with
typing indicator and session reset. Language learners practice real-world English
at difficulty levels A1–B1.
Route: `/my/roleplay`

### Grammar Pro — Cloze Tests
110 fill-in-the-blank exercises across English and Greek covering: all 12 tenses,
conditionals, modal verbs, articles, passive voice, reported speech, irregular verbs,
prepositions, and collocations. CEFR A1–B2 filter, multiple-choice format with instant
green/red feedback, grammar tips on wrong answers, and score summary after each set.
Route: `/my/grammar-practice`

### Premium Visual Identity
Dark animated hero section, glassmorphism cards, Inter + Montserrat typography,
Avantgarde Systems branding throughout, premium login page, and a fully custom CSS
design system (`lx-*` tokens).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Application monolith | Odoo 18 Community |
| Database | PostgreSQL 16 |
| Async message bus | RabbitMQ 3 |
| Ephemeral PvP state | Redis 7 |
| Translation microservice | FastAPI + `deep_translator` (Google / MyMemory) |
| LLM enrichment microservice | FastAPI + `llama-cpp-python` + Qwen2.5-1.5B GGUF |
| Anki import microservice | FastAPI + `zstandard` + `beautifulsoup4` |
| Audio / TTS microservice | FastAPI + `edge-tts` + `faster-whisper` |
| Reverse proxy | Nginx |
| Container orchestration | Docker Compose |
| PDF generation | wkhtmltopdf 0.12.6 (via Odoo QWeb) |

---

## Custom Odoo Modules

Install order (each depends on the one above):

```
language_security → language_core → language_words → language_translation
  → language_enrichment → language_audio → language_anki_jobs
  → language_chat → language_dashboard → language_pvp
  → language_portal → language_learning
```

---

## Quick Start (Development)

```bash
# 1. Clone and configure
cp env.example .env          # set passwords and service URLs

# 2. Start the full stack
make up-dev                  # boots all services (Odoo, Postgres, RabbitMQ,
                             # Redis, Nginx, Translation, LLM, Anki, Audio)

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
curl http://localhost:5433/web/health     # Odoo
curl http://localhost:8001/health         # Translation service
curl http://localhost:8002/health         # LLM service
curl http://localhost:8003/health         # Anki service
curl http://localhost:8004/health         # Audio service
curl http://localhost:15672               # RabbitMQ management UI
```

---

## Documentation

| Document | Purpose |
|---|---|
| [docs/SPEC.md](docs/SPEC.md) | Full product specification: domain model, features, privacy, PvP rules |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design: services, event catalog, real-time PvP design |
| [docs/PLAN.md](docs/PLAN.md) | Milestone-by-milestone implementation plan (M0–M16) |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture decision records (ADR-001–ADR-028) |
| [CLAUDE.md](CLAUDE.md) | AI assistant context: build commands, key invariants, module order |

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

---

## License

Copyright (c) 2026 Avantgarde Systems. All rights reserved.

This software is proprietary. Unauthorized copying, modification, distribution,
or use is strictly prohibited. See [LICENSE](LICENSE) for full terms.
