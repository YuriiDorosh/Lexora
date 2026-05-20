# Lexora — Production Deployment Guide

> **Target:** Ubuntu 22.04 LTS or 24.04 LTS server (Linux VPS).
> **Domain:** `lexora.avantgarde.systems`
> **Architecture:** Single-VPS Docker Compose stack (see `docs/DECISIONS.md` ADR-037).
> **Deploy model:** Manual via Git pull + SSH. **No GitHub Actions / no CI/CD.**

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Server preparation](#2-server-preparation)
3. [Install Docker](#3-install-docker)
4. [Issue the Let's Encrypt certificate](#4-issue-the-lets-encrypt-certificate)
5. [Clone the repository](#5-clone-the-repository)
6. [Configure `.env.prod`](#6-configure-envprod)
7. [Build and start the stack](#7-build-and-start-the-stack)
8. [Initialize the Odoo database](#8-initialize-the-odoo-database)
9. [Install the custom modules](#9-install-the-custom-modules)
10. [Health checks](#10-health-checks)
11. [Certificate auto-renewal](#11-certificate-auto-renewal)
12. [Routine operations](#12-routine-operations)
13. [Updating Lexora (deploying new code)](#13-updating-lexora-deploying-new-code)
14. [Backup and restore](#14-backup-and-restore)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Prerequisites

- **VPS / cloud server** running Ubuntu 22.04 LTS or 24.04 LTS, x86_64.
- **Minimum hardware:** 4 vCPUs, 8 GiB RAM, 40 GiB disk. Recommended 16 GiB+ RAM if you plan to switch the LLM to the 3B model.
- **Public IPv4 address.**
- **DNS A record** for `lexora.avantgarde.systems` already pointing at the server IP. Verify with `dig +short lexora.avantgarde.systems`.
- **SSH root access** (or a sudo user) to the server.
- **Outbound HTTPS** open on the server (workers download the LLM model from Hugging Face, the translation service calls Google Translate, the audio service uses Edge TTS).
- **Ports 80 and 443** open to the public Internet (firewall / cloud provider security group).

---

## 2. Server preparation

SSH into the server and bring the system up to date.

```bash
ssh root@<server-ip>

apt update && apt upgrade -y
apt install -y git ca-certificates curl gnupg lsb-release ufw
```

Optional but recommended — enable a basic firewall:

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw status
```

Set the hostname (optional, cosmetic):

```bash
hostnamectl set-hostname lexora.avantgarde.systems
```

---

## 3. Install Docker

Use the official Docker repository (NOT the `docker.io` package from the Ubuntu archive — it's older and missing `docker compose`).

```bash
# Remove any conflicting older packages
apt remove -y docker docker-engine docker.io containerd runc || true

# Add Docker's official GPG key + repository
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Confirm
docker --version
docker compose version
```

Enable Docker at boot:

```bash
systemctl enable --now docker
```

---

## 4. Issue the Let's Encrypt certificate

The certificate must exist on the host **before** the Lexora stack starts, because nginx fails to start without `/etc/letsencrypt/live/lexora.avantgarde.systems/fullchain.pem`.

> If you already have certbot installed and the certificate issued (as shown in your `ls /etc/letsencrypt/live/lexora.avantgarde.systems/` output), skip to §5. The certificate path is already in the right place.

Install certbot:

```bash
apt install -y certbot
```

Make sure no other process is bound to port 80, then issue the certificate in standalone mode:

```bash
# Stop anything listening on port 80 (if applicable)
systemctl stop nginx 2>/dev/null || true
ss -lntp | grep :80   # should be empty

# Issue the cert.  Replace the email with a real address you read —
# Let's Encrypt sends expiry reminders there.
certbot certonly --standalone \
  -d lexora.avantgarde.systems \
  -m your-email@avantgarde.systems \
  --agree-tos \
  --no-eff-email

# Verify the files exist
ls -l /etc/letsencrypt/live/lexora.avantgarde.systems/
# expected: cert.pem  chain.pem  fullchain.pem  privkey.pem  README
```

> **Why standalone, not webroot?** On a fresh server the Lexora nginx isn't running yet, so there's nothing to serve the webroot challenge. Once Lexora is running, certbot's automated renewals can use the certbot webroot path `/var/www/certbot/` that the Lexora nginx config exposes at `/.well-known/acme-challenge/`. See §11.

---

## 5. Clone the repository

Pick a stable working directory (the example uses `/opt/lexora`).

```bash
mkdir -p /opt
cd /opt
git clone https://github.com/<your-org>/Lexora.git lexora
cd lexora

# Switch to the M38 production branch
git checkout m38_production_readiness
git pull
```

> **Note:** `m38_production_readiness` is **not** merged into `main` yet. Deployment runs from this branch until M38 is merged. When that happens, switch with `git checkout main && git pull`.

---

## 6. Configure `.env.prod`

```bash
cd /opt/lexora
cp .env.prod.example .env.prod
chmod 600 .env.prod      # secrets live here — keep file readable only by root
```

Generate strong random values for every `CHANGE_ME_*` placeholder:

```bash
# Generate one secret each (run as many times as you need)
openssl rand -base64 32 | tr -d '/=+'
```

Edit `.env.prod`:

```bash
nano .env.prod
# or: vi .env.prod
```

Replace every `CHANGE_ME_*` placeholder. **Important constraints:**

- `DB_PASSWORD` **must equal** `POSTGRES_PASSWORD` (Odoo reads it to connect to Postgres).
- `ADMIN_PASSWD` is the **Odoo master password** used by the `/web/database/manager` web UI.
- `RABBITMQ_USER` and `RABBITMQ_PASS` must **not** be `guest/guest`.
- Domain is **not** in this file — it's hardcoded in `docker_compose/nginx/nginx.prod.conf`.

Validate the file:

```bash
make prod-env-check
# Expected output:
#   prod-env-check: OK (.env.prod exists and contains no CHANGE_ME_ placeholders)
```

If the check fails, it prints which line still has a `CHANGE_ME_` and exits.

---

## 7. Build and start the stack

```bash
cd /opt/lexora

# Build all custom images (odoo, translation, llm, anki, audio).
# First build pulls the model on first start — can take 5–10 minutes
# of CPU + ~1 GB of disk for the LLM GGUF.
make prod-build

# Start the full stack detached.
make prod-up
```

The `prod-up` target also runs `prod-env-check` first, so a missing or unfilled `.env.prod` will block startup.

Check that all nine services are running:

```bash
make prod-ps
```

Expected services (all should be `Up`):

```
lexora_nginx_prod        nginx:1.27-alpine             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
lexora_odoo_prod         lexora-prod-odoo
lexora_postgres_prod     postgres:15
lexora_redis_prod        redis:7-alpine
lexora_rabbitmq_prod     rabbitmq:3-management
lexora_translation_prod  lexora-prod-translation-service
lexora_llm_prod          lexora-prod-llm-service
lexora_anki_prod         lexora-prod-anki-service
lexora_audio_prod        lexora-prod-audio-service
```

Tail logs while everything settles:

```bash
make prod-logs    # Ctrl-C to detach
```

The LLM service downloads its GGUF model on first start; you'll see Hugging Face progress lines in `lexora_llm_prod` logs. Expect `llm_ready:true` after 1–3 minutes (depending on bandwidth).

---

## 8. Initialize the Odoo database

Browse to `https://lexora.avantgarde.systems/web/database/manager`. You should see the Odoo database manager.

1. Click **Create Database**.
2. Master Password = value of `ADMIN_PASSWD` in `.env.prod`.
3. Database Name = `lexora` (this name is referenced in the rest of this guide).
4. Email = your admin email (this becomes the first Odoo user).
5. Password = a strong password (this is the **admin user** password, distinct from `ADMIN_PASSWD`).
6. Language / Country = pick yours.
7. ☑ Demo data: leave **unchecked** in production.
8. Click **Create database**.

Odoo will initialise the base schema (~30–60 s) and redirect to the backend at `https://lexora.avantgarde.systems/odoo`.

---

## 9. Install the custom modules

The custom Lexora addons are mounted into the container at `/mnt/extra-addons` (read-only) but not yet installed in the database. Install them in the order required by `docs/PLAN.md`:

```bash
docker exec lexora_odoo_prod odoo \
  --config /etc/odoo/odoo.conf \
  -d lexora \
  --init language_security,language_core,language_words,\
language_translation,language_enrichment,language_audio,language_anki_jobs,\
language_chat,language_dashboard,language_pvp,language_portal,language_learning,\
base_search_fuzzy,web_notify,password_security,website_menu_by_user_status,website_require_login \
  --stop-after-init \
  --no-http
```

> Expected to take 2–5 minutes. Watch for `Modules loaded.` near the end of the output and **0 errors** (warnings about `noupdate` are normal).

After the install completes, restart Odoo so the live process picks up all new model fields:

```bash
docker restart lexora_odoo_prod
```

Wait ~15 seconds, then browse to `https://lexora.avantgarde.systems`. The Lexora landing page should now appear.

---

## 10. Health checks

```bash
# 1. Public HTTPS reachable
curl -I https://lexora.avantgarde.systems
# expected: HTTP/2 200 (or 303 if not logged in)

# 2. HTTP → HTTPS redirect
curl -I http://lexora.avantgarde.systems
# expected: HTTP/1.1 301 Moved Permanently  →  Location: https://...

# 3. TLS version + cipher
curl -v https://lexora.avantgarde.systems 2>&1 | grep -E "SSL connection|ALPN|ssl_protocol"

# 4. Worker services (only reachable from inside the bridge — use docker exec)
docker exec lexora_translation_prod curl -s http://localhost:8000/health
docker exec lexora_llm_prod          curl -s http://localhost:8000/health
docker exec lexora_anki_prod         curl -s http://localhost:8000/health
docker exec lexora_audio_prod        curl -s http://localhost:8000/health

# 5. RabbitMQ
docker exec lexora_rabbitmq_prod rabbitmqctl status | head -20

# 6. Postgres
docker exec lexora_postgres_prod psql -U odoo -l
```

If anything is not `200 OK` / `pong` / `ready:true`, jump to §15.

---

## 11. Certificate auto-renewal

Let's Encrypt certificates expire after 90 days. Certbot ships a systemd timer that runs `certbot renew` twice daily; on this server you already have it (the certbot output you provided confirmed `Certbot has set up a scheduled task to automatically renew this certificate in the background.`).

The only piece you need to add is a **post-renewal hook** that reloads the Lexora nginx container so it picks up the new fullchain.pem.

Create `/etc/letsencrypt/renewal-hooks/deploy/lexora-nginx-reload.sh`:

```bash
cat > /etc/letsencrypt/renewal-hooks/deploy/lexora-nginx-reload.sh <<'EOF'
#!/usr/bin/env bash
# Reload the Lexora nginx container after every successful renewal.
# Certbot calls every script in /etc/letsencrypt/renewal-hooks/deploy/
# only when a cert was actually renewed (no-op otherwise).
set -euo pipefail
if docker ps --format '{{.Names}}' | grep -q '^lexora_nginx_prod$'; then
    docker exec lexora_nginx_prod nginx -s reload
    logger -t lexora "nginx reloaded after Let's Encrypt renewal"
fi
EOF

chmod +x /etc/letsencrypt/renewal-hooks/deploy/lexora-nginx-reload.sh
```

Test the renewal pipeline (dry run — no actual renewal happens):

```bash
certbot renew --dry-run
```

You should see something like:

```
Account registered.
Simulating renewal of an existing certificate for lexora.avantgarde.systems
...
Congratulations, all simulated renewals succeeded:
  /etc/letsencrypt/live/lexora.avantgarde.systems/fullchain.pem (success)
```

The next real renewal (~30 days before expiry) will automatically reload nginx inside the container with no manual intervention.

---

## 12. Routine operations

All targets are in the `Makefile`. Run them from `/opt/lexora`.

| Command | What it does |
|---|---|
| `make prod-ps` | List all production containers + status |
| `make prod-logs` | Tail logs from every service (Ctrl-C to detach) |
| `make prod-restart SVC=odoo` | Restart one service (services: `postgres`, `redis`, `rabbitmq`, `odoo`, `nginx`, `translation-service`, `llm-service`, `anki-service`, `audio-service`) |
| `make prod-down` | Stop the whole stack (data preserved in named volumes) |
| `make prod-up` | Start everything again |
| `make prod-build` | Rebuild custom images (after a `git pull`) |

Looking at one container's logs:

```bash
docker logs -f --tail=100 lexora_odoo_prod
docker logs -f --tail=100 lexora_llm_prod
docker logs -f --tail=100 lexora_nginx_prod
```

---

## 13. Updating Lexora (deploying new code)

The deploy story is **manual** — no GitHub Actions, no CI/CD pipeline. This is intentional (see ADR-037).

```bash
# 1. SSH into the server
ssh root@<server-ip>
cd /opt/lexora

# 2. Pull the latest commits on the production branch
git fetch
git status                  # confirm you're on m38_production_readiness (or main once merged)
git pull

# 3. Rebuild any custom images that changed.
#    `make prod-build` is idempotent — it only rebuilds layers that changed.
make prod-build

# 4. Recreate the stack with the new images.
#    `docker compose up -d` is smart enough to recreate only the
#    services whose image or config changed.
make prod-up

# 5. If new Odoo models / fields landed, update the modules in the database.
#    Replace `language_portal,language_learning` with the modules that changed.
docker exec lexora_odoo_prod odoo \
  --config /etc/odoo/odoo.conf \
  -d lexora \
  --update language_portal,language_learning \
  --stop-after-init \
  --no-http

# 6. Restart Odoo so the live process picks up the new code.
docker restart lexora_odoo_prod

# 7. Smoke-check.
curl -I https://lexora.avantgarde.systems
make prod-logs
```

---

## 14. Backup and restore

### Backup

Use Odoo's built-in `/web/database/manager` to produce a `.zip` (includes the Postgres dump **and** the filestore):

1. Browse to `https://lexora.avantgarde.systems/web/database/manager`.
2. Click **Backup** next to the `lexora` database.
3. Master Password = `ADMIN_PASSWD` from `.env.prod`.
4. Format = `zip (includes filestore)`.
5. Click **Backup**. A `.zip` downloads.
6. **Copy it off the server** to your laptop / S3 / B2 / wherever.

Recommended cadence: daily for active deployments, weekly for staging.

> A future milestone (out of scope for M38) will add a scheduled `pg_dump` + offsite sync.

### Restore

```bash
# Run the helper which prints the steps (it doesn't do the restore itself —
# the operator does it via the web UI).
make prod-restore-db
```

Follow the printed steps. Restore via `/web/database/manager`'s **Restore** button, supply the `.zip`, the master password, and a target database name.

If the `.zip` is larger than 2 GB, raise `client_max_body_size` in `docker_compose/nginx/nginx.prod.conf` and run `make prod-restart SVC=nginx`.

---

## 15. Troubleshooting

### nginx fails to start: `cannot load certificate`

```
[emerg] cannot load certificate "/etc/letsencrypt/live/lexora.avantgarde.systems/fullchain.pem"
```

The cert files don't exist on the host. Re-run §4 (`certbot certonly --standalone -d lexora.avantgarde.systems …`). Confirm with `ls /etc/letsencrypt/live/lexora.avantgarde.systems/`.

### `prod-env-check` keeps failing

```
ERROR: .env.prod still contains CHANGE_ME_ placeholders.
```

Grep for the remaining placeholders and fill them in:

```bash
grep -n CHANGE_ME_ .env.prod
```

### Odoo container is up but `/odoo` returns 502

Most likely Odoo is still booting (first start can take 30–60 s after `make prod-up`). Tail the logs:

```bash
docker logs -f --tail=100 lexora_odoo_prod
```

If you see `password authentication failed for user "odoo"`, the `DB_PASSWORD` in `.env.prod` doesn't match `POSTGRES_PASSWORD`. Fix and run `make prod-restart SVC=odoo`.

### LLM service: `llm_ready:false` forever

The Qwen GGUF (~1 GB) is still downloading. Watch progress:

```bash
docker logs -f lexora_llm_prod
```

If the download repeatedly fails, the host has no outbound HTTPS to Hugging Face. Either fix the firewall or pre-seed the model into the `lexora_llm_models_prod` named volume (see `docker_compose/llm/docker-compose.yml` for the volume name; `LLM_AUTO_DOWNLOAD=0` in `.env.prod` to disable the automatic download).

### Translation service returns stub output (`[stub:…]`)

The `deep_translator` dep is missing or the worker can't reach Google. Check the worker logs:

```bash
docker logs --tail=100 lexora_translation_prod
```

If you see network errors, the host has no outbound HTTPS to Google. Set `TRANSLATE_PROVIDER=mymemory` in `.env.prod` and `make prod-restart SVC=translation-service`.

### Audio service: TTS works but transcription doesn't

Faster-Whisper hasn't finished loading its model yet, or `AUDIO_TRANSCRIPTION_ENABLED=0`. Check:

```bash
docker exec lexora_audio_prod curl -s http://localhost:8000/health
```

Expected: `{"whisper_ready":true,"consumer_alive":true,"tts_engine":"edge-tts",...}`.

### Postgres won't start

Usually a corrupted volume or a port collision (the prod stack does NOT publish Postgres to the host, but a previous dev stack might be holding port 5432).

```bash
docker logs lexora_postgres_prod
docker ps -a | grep postgres
```

If there's a stale dev `postgres_db` container, stop it first (`docker stop postgres_db`).

### Resetting everything (DESTROYS DATA)

> Use only if you intend to lose **all** production data — Postgres, Odoo filestore, Redis, RabbitMQ queues, model caches.

```bash
make prod-down-volumes
# You'll be prompted to type YES literally.
```

After this, you're back to a clean slate — repeat from §7.

---

## Out of scope (deliberate non-goals)

M38 ships the production substrate. The following are explicit future work:

- **Scheduled offsite backup automation.** Currently delegated to Odoo's `/web/database/manager`.
- **Monitoring stack** (Prometheus + Grafana + Loki). Dev compose has them; prod intentionally ships without alerting.
- **CI/CD pipeline.** Deploys are manual via `git pull` + `make prod-build` + `make prod-up`.
- **Multi-node / load-balanced topology.** Single VPS only.
- **HSTS preload list submission.** The header is preload-ready, but the actual submission to `hstspreload.org` is an operator step.

---

## References

- **Architecture decision record:** `docs/DECISIONS.md` § ADR-037
- **Milestone plan:** `docs/PLAN.md` § M38
- **Resume / task log:** `docs/TASKS.md` § M38
