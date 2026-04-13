# Lexora

## Overview

Lexora is a language-learning platform for **English (en), Greek (el), and Ukrainian (uk)**.

The product uses:

- **Odoo 18** as the main application monolith (auth, users, vocabulary, chat, posts, PvP battles, dashboards)
- **FastAPI Translation Service** — offline translation via Argos Translate
- **FastAPI LLM Service** — synonyms, antonyms, example sentences, explanations (Qwen3 8B local model)
- **FastAPI Anki Import Service** — `.apkg` and `.txt` Anki deck imports
- **FastAPI Audio/TTS Service** — offline text-to-speech (piper / espeak-ng)
- **RabbitMQ** — async event bus between Odoo and the four worker services
- **PostgreSQL 15** — primary database
- **Redis** — ephemeral PvP battle state

## Documentation

| Document | Purpose |
|---|---|
| [docs/SPEC.md](docs/SPEC.md) | Full product specification: domain model, all features, privacy rules, PvP rules |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design: services, Odoo modules, event catalog, real-time design |
| [docs/PLAN.md](docs/PLAN.md) | Milestone-by-milestone implementation plan with verification commands |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architecture decision records (ADR-001–ADR-019) with rationale |
| [CLAUDE.md](CLAUDE.md) | Claude Code context: build commands, key invariants, module install order |

## Quick start (dev)

```bash
cp env.example .env          # fill in passwords
make up-dev                   # start full dev stack (once M0 is implemented)
```

See [docs/PLAN.md](docs/PLAN.md) for the milestone-by-milestone implementation guide.

## Status

Discovery and specification complete. Implementation not yet started. Begin at **M0** in [docs/PLAN.md](docs/PLAN.md).
