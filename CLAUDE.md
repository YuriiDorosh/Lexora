# Lexora — Claude Code Context

Language-learning platform built on Odoo 18, with 4 async FastAPI worker services connected via RabbitMQ.

## Key docs (read these before coding)

- @docs/SPEC.md — product specification: domain model, features, privacy rules, PvP rules
- @docs/ARCHITECTURE.md — system design: services, Odoo modules, event catalog, PvP real-time design
- @docs/PLAN.md — milestone-by-milestone implementation plan with verification commands
- @docs/DECISIONS.md — all architecture decision records with rationale

## Repo structure

```
src/addons/          # Odoo custom addons (language_* modules go here)
src/configs/         # odoo.conf
docker_compose/      # per-service Docker Compose files
  odoo/              # Odoo service + nginx
  db/                # PostgreSQL
  redis/             # Redis
  pgadmin/ adminer/  # DB tooling
  elastic/ kibana/   # (not in MVP stack; kept for reference)
backups/             # pg_restore targets
logs/                # nginx + app logs
requirements/        # Python deps
```

## Custom Odoo modules (all in src/addons/, to be created)

Install order:
`language_security` → `language_core` → `language_words` → `language_translation` → `language_enrichment` → `language_audio` → `language_anki_jobs` → `language_chat` → `language_dashboard` → `language_pvp` → `language_portal`

## Build & run

```bash
# Start full dev stack
make up-dev

# Start individual services
make up-db          # PostgreSQL only
make up-odoo        # Odoo + nginx
make up-redis       # Redis
# (rabbitmq, worker services: see docker_compose/ subdirs)

# Odoo module install / update
docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --init language_security,language_core,... --stop-after-init

docker exec odoo odoo --config /etc/odoo/odoo.conf \
  -d lexora --update language_words --stop-after-init

# Logs
make logs-odoo
make logs-db

# DB restore from backup
make load-backup FILE=your_backup.dump
```

## Core tech choices

| Concern | Choice |
|---|---|
| Framework | Odoo 18 Community |
| DB | PostgreSQL 16 |
| Message bus | RabbitMQ 3 |
| PvP ephemeral state | Redis 7 (compose file to be created in M0; `redis` Python pkg already in base-requirements.txt) |
| Offline translation | Argos Translate |
| LLM enrichment | Qwen3 8B (local, ≤20 GB) |
| TTS | piper / espeak-ng (offline-first) |
| Reverse proxy | Nginx |
| Search | SQL + pg_trgm (base_search_fuzzy addon) |
| Analytics | PostgreSQL (no Elasticsearch in MVP) |

## Key invariants (do not break these)

- Every async job must carry a `job_id` UUID for idempotency (ADR-018)
- Dedup key = `normalize(source_text) + source_language + owner_id` — `type` is NOT in the key (ADR-003)
- Learning entries are private by default; sharing is opt-in (ADR-004)
- All four worker services are async via RabbitMQ; TTS is the 4th service (ADR-007)
- PvP uses Odoo bus + Redis for real-time; Odoo owns persistent results (ADR-009)
- No Elasticsearch in MVP stack (ADR-016)
- GDPR: private entries deletable; community content anonymizable (ADR-017)

## Current status

Discovery complete. Implementation not started. Begin at M0 in @docs/PLAN.md.
