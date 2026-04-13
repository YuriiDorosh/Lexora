# Lexora — Architecture Document (MVP)

> Version: 0.1 (post-discovery)
> Last updated: 2026-04-13

---

## 1. High-Level Overview

```
                        ┌─────────────────────────────────────┐
                        │              Browser / Client        │
                        └────────────┬────────────────────────┘
                                     │ HTTP / WebSocket
                        ┌────────────▼────────────────────────┐
                        │            Nginx (reverse proxy)     │
                        └────────────┬────────────────────────┘
                                     │
                        ┌────────────▼────────────────────────┐
                        │         Odoo 18 (monolith)           │
                        │  website / portal / auth / models    │
                        │  Odoo bus (websocket / longpoll)     │
                        └─┬──────┬──────┬──────────┬──────────┘
                          │      │      │          │
               Publishes events  │   Reads/writes  │ WebSocket push
                          │      │      │          │
              ┌───────────▼──┐   │  ┌───▼────┐  ┌─▼────────┐
              │  RabbitMQ    │   │  │Postgres│  │  Redis   │
              │  (event bus) │   │  │  (DB)  │  │(ephemeral│
              └──┬──┬──┬──┬──┘   │  └────────┘  │ PvP state│
                 │  │  │  │      │              └──────────┘
       ┌─────────┘  │  │  └──────────────────────────┐
       │            │  │                              │
┌──────▼──────┐ ┌───▼───▼────┐ ┌──────────────┐ ┌───▼────────────┐
│ Translation │ │   Anki     │ │  LLM Service │ │  Audio/TTS     │
│  Service    │ │  Import    │ │  (FastAPI +  │ │  Service       │
│ (FastAPI +  │ │  Service   │ │  Qwen3 8B)   │ │  (FastAPI +    │
│  Argos)     │ │ (FastAPI)  │ │              │ │  piper/espeak) │
└─────────────┘ └────────────┘ └──────────────┘ └────────────────┘
```

---

## 2. Principle: Odoo as System of Record

Odoo is the **single system of record** for all business data:
- Users, roles, auth
- Learning entries, translations, enrichments
- Audio metadata (files stored in Odoo filestore)
- Media links
- Chat messages
- Posts, articles, comments
- Dashboard data
- PvP battle history, player stats, leaderboard data
- Import job logs

External services (Translation, LLM, Anki, TTS) are **stateless processors**. They receive a job via RabbitMQ, do work, and publish a result event. They do not own any business data.

---

## 3. Services

### 3.1 Odoo 18

- Odoo Community Edition, built as a custom Docker image.
- Custom addons mounted from `src/addons/`.
- Postgres as the database backend.
- Exposes HTTP and WebSocket via the built-in Odoo server.
- Nginx sits in front and handles SSL termination + reverse proxy.
- Redis is used by custom code for PvP ephemeral state (via the `redis` Python package already in `base-requirements.txt`). Odoo's own session store uses its default filesystem-backed mechanism; Redis is **not** configured as Odoo's session store in the current `odoo.conf`.

### 3.2 Translation Service

- **Runtime:** FastAPI (Python)
- **Library:** Argos Translate (offline, no external API calls)
- **Languages:** `uk`, `en`, `el`
- **Note:** No direct `uk↔el` model exists in Argos. Routing is `uk→en→el` (two-hop). Quality degradation is a known limitation documented in OD-2.
- **Consumes:** `translation.requested`
- **Publishes:** `translation.completed`, `translation.failed`

### 3.3 LLM Enrichment Service

- **Runtime:** FastAPI (Python)
- **Model:** Qwen3 8B (or equivalent ≤20 GB local model, CPU or GPU)
- **Outputs:** synonyms, antonyms, 3–7 example sentences, short explanation
- **Note:** Greek enrichment quality may be lower than English/Ukrainian (OD-3).
- **Consumes:** `enrichment.requested`
- **Publishes:** `enrichment.completed`, `enrichment.failed`
- **Hardware note:** CPU-only inference is possible but slow. A GPU or large RAM (≥16 GB) is recommended for acceptable latency.

### 3.4 Anki Import Service

- **Runtime:** FastAPI (Python)
- **Parses:** `.apkg` (SQLite + zip), `.txt` (tab-separated)
- **Responsibilities:** parse, normalize, return new + skipped entry lists, extract audio from `.apkg`
- **Consumes:** `anki.import.requested`
- **Publishes:** `anki.import.completed`, `anki.import.failed`

### 3.5 Audio / TTS Service

- **Runtime:** FastAPI (Python)
- **Engines:** piper (primary), espeak-ng (fallback), Coqui TTS (optional)
- **Offline only:** no external API calls for MVP
- **Language quality:** English > Ukrainian > Greek (known MVP limitation)
- **Consumes:** `audio.generation.requested`
- **Publishes:** `audio.generation.completed`, `audio.generation.failed`
- **Output:** audio file (MP3/WAV) returned to Odoo for storage in filestore

### 3.6 RabbitMQ

- Async message bus between Odoo and all worker services.
- Durable queues; persistent messages.
- All messages carry a `job_id` (UUID) for idempotency.
- Dead-letter queues for failed messages.

### 3.7 Redis

**Role in Lexora:** PvP ephemeral battle state only. Odoo sessions use the default Odoo filesystem-backed session store; Redis is **not** configured as an Odoo session or cache backend.

The `redis==7.2.1` Python package is already present in `base-requirements.txt` (and therefore installed in the Odoo container image), making direct `redis-py` calls from custom Odoo code possible without further pip changes.

**A Redis Docker Compose service does not yet exist in the repo.** It must be created in M0 (a `docker_compose/redis/docker-compose.yml` file). The Makefile already has `up-redis` / `down-redis` / `logs-redis` targets that reference this path.

**PvP ephemeral battle state** — stores short-lived keys per active battle:
- Matchmaking queue state (sorted set per language pair)
- Current round number
- Round countdown timer
- Player answers for the current round
- Reconnect grace period state
- Battle TTL (expires automatically if battle stalls)

PvP Redis keys use a `pvp:battle:<battle_id>:*` namespace pattern with appropriate TTLs.

### 3.8 PostgreSQL

- Odoo database backend.
- All business data, including analytics computed by Odoo ORM.
- No Elasticsearch in MVP. SQL-backed dashboards and search.

### 3.9 Nginx

- Reverse proxy for Odoo.
- WebSocket pass-through for Odoo bus.
- SSL termination (production).
- Serving static files in production.

---

## 4. Odoo Custom Modules

All modules live in `src/addons/`. Install order matters; dependencies declared in `__manifest__.py`.

```
language_security
    └── language_core
            ├── language_words
            │       ├── language_translation
            │       ├── language_enrichment
            │       ├── language_audio
            │       └── language_anki_jobs
            ├── language_chat
            ├── language_dashboard
            ├── language_pvp
            └── language_portal
```

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `language_security` | Security groups, access rules, record-level visibility. Base dependency for all other modules. |
| `language_core` | System settings (configurable params like min PvP entries, audio max size), base utility methods, RabbitMQ publisher/consumer infrastructure, job status tracking. |
| `language_words` | `language.entry`, `language.user.profile`, `language.media.link`, dedup logic, normalization, language detection integration, entry visibility/sharing. |
| `language_translation` | `language.translation`, translation job lifecycle, Argos Translate event handling. |
| `language_enrichment` | `language.enrichment`, LLM enrichment job lifecycle, event handling. |
| `language_audio` | `language.audio`, user recording upload, TTS generation job lifecycle, audio event handling. |
| `language_anki_jobs` | `language.anki.job`, import job lifecycle, import log persistence, event handling. |
| `language_chat` | Public channels, private DMs, moderation hooks, "save to my list" from chat. |
| `language_dashboard` | Popular words, word of the day, personal dashboard, community dashboard, leaderboard data aggregation. |
| `language_pvp` | `language.pvp.battle`, `language.pvp.round`, matchmaking logic (Redis queue), bot logic, reconnect handling, player stats update, leaderboard computation. |
| `language_portal` | Website/portal views for all user-facing features. Articles/posts/comments with moderation flow. "Copy to my list" inline UI. |

---

## 5. Async Event Bus Patterns

### 5.1 Event Catalog

| Event | Publisher | Consumer |
|---|---|---|
| `translation.requested` | Odoo | Translation Service |
| `translation.completed` | Translation Service | Odoo |
| `translation.failed` | Translation Service | Odoo |
| `enrichment.requested` | Odoo | LLM Service |
| `enrichment.completed` | LLM Service | Odoo |
| `enrichment.failed` | LLM Service | Odoo |
| `anki.import.requested` | Odoo | Anki Import Service |
| `anki.import.completed` | Anki Import Service | Odoo |
| `anki.import.failed` | Anki Import Service | Odoo |
| `audio.generation.requested` | Odoo | Audio/TTS Service |
| `audio.generation.completed` | Audio/TTS Service | Odoo |
| `audio.generation.failed` | Audio/TTS Service | Odoo |

PvP coordination (future, if PvP moves to a dedicated service):
- `pvp.matchmaking.requested`, `pvp.matchmaking.started`, `pvp.matchmaking.failed`
- `pvp.battle.started`, `pvp.round.completed`, `pvp.battle.completed`

### 5.2 Idempotency Contract

Every event payload includes:
```json
{
  "job_id": "<UUID>",
  "event_type": "translation.requested",
  "payload": { ... }
}
```

**Worker behavior:**
1. Receive message.
2. Check if `job_id` is already in a terminal state (`completed` or `failed`) in the worker's local tracking (Redis `SETNX` or DB unique check).
3. If already completed: log as duplicate delivery, ack the message, no further action.
4. If not: process, write result, publish result event, then ack.

**Odoo-side job state machine:**
```
pending → processing → completed
                    → failed
```

Re-delivery after `completed` or `failed` → no-op (log the duplicate).

### 5.3 Retry and Dead-Letter

- Workers ack only after durable write.
- On failure: message is nacked; RabbitMQ retries with exponential backoff.
- After N retries: message moves to dead-letter queue.
- Odoo polls for stuck `processing` jobs (e.g., jobs in `processing` for >10 minutes are eligible for a retry or admin alert).

---

## 6. PvP Real-Time Design

### State distribution

| State | Where |
|---|---|
| Matchmaking queue | Redis sorted set, keyed by `(practice_lang, native_lang)` |
| Live battle: current round, answers, countdown | Redis hash, `pvp:battle:<id>:*` |
| Reconnect grace timer | Redis key with TTL |
| Final battle result, stats | Odoo Postgres |
| UI event delivery | Odoo bus (WebSocket/long-poll) |

### Battle lifecycle

```
User requests battle
    → Odoo writes battle record (status: waiting)
    → Odoo adds user to Redis matchmaking set
    → 60s timer

Found opponent → Odoo creates battle in DB, initializes Redis state → starts round 1
No opponent    → Odoo starts bot battle (bot runs server-side in Odoo)

Each round:
    → Odoo selects entry from player's eligible entries
    → Odoo selects distractors (own dict → fallback pool)
    → Odoo pushes round data via Odoo bus
    → Redis countdown key set (30s TTL)
    → Players submit answers
    → Round expires or both answered
    → Odoo scores round, updates Redis and DB
    → Next round or battle end

Battle end:
    → Odoo calculates winner
    → Odoo writes final result, updates player stats, win_rate
    → Odoo pushes result via Odoo bus
    → Redis battle state expired/cleaned up

Disconnection:
    → Redis reconnect grace key set (15s TTL)
    → If reconnect: battle resumes
    → If timeout: forfeit, opponent wins, battle ends
```

---

## 7. Storage Model

| Data | Storage | Notes |
|---|---|---|
| Business records | Postgres via Odoo ORM | Canonical |
| User-recorded audio | Odoo filestore (`ir.attachment`) | Permanent |
| Generated TTS audio | Odoo filestore (`ir.attachment`) | Lazy, permanent after first generation |
| Anki `.apkg` files (upload) | Temp during job processing | Not stored after import completes |
| Redis PvP state | Redis (in-memory) | Short TTL |
| Odoo sessions | Odoo filesystem session store (default) | Redis is NOT the session backend in current config |

**File size limits:**
- User audio recording upload: **10 MB max** (configurable via system parameter `language.audio.max_upload_bytes`).
- No video file uploads in MVP; external links only.

---

## 8. Search

| Context | Implementation |
|---|---|
| Vocabulary (source text + translations) | SQL ILIKE + `base_search_fuzzy` (pg_trgm) |
| Cross-language lookup | JOIN against `language.translation` table |
| Posts/articles | SQL ILIKE on title + body |
| Elasticsearch | Not in MVP stack |

Fuzzy search uses the `base_search_fuzzy` OCA addon. The addon files are present in `src/addons/` (mountable), but it must be explicitly installed in the Odoo database (e.g., via `--init base_search_fuzzy` or through the Apps menu). It also requires the `pg_trgm` PostgreSQL extension to be enabled.

---

## 9. Roles & Security

Implemented in `language_security`:

```
base.group_public          → Public Visitor
base.group_portal          → Portal / Registered User
language_security.group_language_user      → Language User (default on signup)
language_security.group_language_moderator → Moderator
language_security.group_language_admin     → Administrator
```

Record-level security:
- `language.entry` records: owner can read/write; shared entries readable by Language Users; no other user access to private entries.
- Moderators do not get a blanket read on all private entries.
- Admins can access all records in the backend.

Auto-assignment to `group_language_user` happens via a hook on `res.users` creation (or via the portal signup flow).

---

## 10. Docker Compose Stack (MVP)

| Service | Image / Build | Purpose |
|---|---|---|
| `odoo` | Custom build (`docker_compose/odoo/Dockerfile`) | Main application |
| `postgres` | `postgres:15` | Odoo database (version already in repo compose files; Odoo 18 supports pg 13–16) |
| `rabbitmq` | `rabbitmq:3-management` | Async message bus |
| `redis` | `redis:7-alpine` | PvP ephemeral state (compose file to be created in M0) |
| `nginx` | Custom build | Reverse proxy, WebSocket pass-through |
| `translation-service` | Custom build | Argos Translate FastAPI service |
| `llm-service` | Custom build | Qwen3 8B FastAPI service |
| `anki-service` | Custom build | Anki import FastAPI service |
| `audio-service` | Custom build | piper/espeak TTS FastAPI service |

**Not in MVP stack:** Elasticsearch, Kibana, APM, Celery workers (replaced by RabbitMQ workers).

Dev tooling (optional, separate compose files): pgAdmin, Adminer, monitoring.

---

## 11. Production Path

The MVP runs on Docker Compose locally. The same Docker Compose (with a prod overlay file) should be deployable to a Linux VPS/cloud VM.

**Production additions to plan:**
- Nginx with SSL termination (Let's Encrypt via Certbot, or pre-provisioned cert).
- `.env` secrets replaced by a secrets management approach (Docker secrets or a vault, TBD).
- Odoo `workers` setting tuned for the server's CPU count.
- PostgreSQL with `max_connections` tuned (already at 500 per current config).
- Backup/restore scripts already partially present in `Makefile`. Extend for scheduled dumps.
- Log shipping: existing promtail → Loki stack in `docker_compose/odoo/` can be reused.
- Redis persistence (AOF or RDB) for PvP state durability across restarts.
- RabbitMQ durable queues + management UI (already in `rabbitmq:3-management` image).

**Not in scope for MVP implementation but documented:**
- Kubernetes / container orchestration
- Multi-region
- CDN for static files / audio
- Elasticsearch as read model
