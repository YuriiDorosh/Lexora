ENV = --env-file .env
LOGS = docker logs
EXEC = docker exec -it
DC = docker compose
MANAGE_PY = python src/manage.py

APP_CONTAINER = odoo
WORKER_1_CONTAINER = celery_worker_1
WORKER_2_CONTAINER = celery_worker_2
WORKER_3_CONTAINER = celery_worker_3
WORKER_4_CONTAINER = celery_worker_4
WORKER_BEAT_CONTAINER = celery_beat
REDIS_CONTAINER = redis
NGINX_CONTAINER = nginx
DB_CONTAINER = postgres
ELASTIC_CONTAINER = elasticsearch
KIBANA_CONTAINER = kibana
APM_CONTAINER = apm-server
FASTAPI_CONTAINER = fastapi

NETWORK_NAME = backend
NETWORK_NAME_PROD = backend-prod

MAKE = make

.PHONY: check-network check-network-prod \
        up-all up-all-no-cache \
        up-monitoring up-monitoring-no-cache \
        down-all down-all-volumes \
        down-monitoring down-monitoring-volumes \
        up-all-without-monitoring up-all-no-cache-without-monitoring \
        up-all-without-monitoring-prod up-all-no-cache-without-monitoring-prod \
        down-all-without-monitoring down-all-without-monitoring-prod \
        up-db up-db-no-cache up-db-no-cache-prod \
        down-db down-db-prod down-db-volumes logs-db load-backup \
        up-odoo up-odoo-no-cache up-odoo-prod up-odoo-no-cache-prod \
        down-odoo down-odoo-prod down-odoo-volumes logs-odoo \
        migrations migrate superuser test collectstatic check-apm test-apm \
        up-pgadmin up-pgadmin-prod down-pgadmin down-pgadmin-prod down-pgadmin-volumes logs-pgadmin \
        up-adminer up-adminer-prod up-adminer-no-cache-prod down-adminer down-adminer-prod down-adminer-volumes logs-adminer \
        up-redis down-redis logs-redis \
        up-nginx down-nginx logs-nginx \
        up-elastic down-elastic logs-elastic \
        up-kibana down-kibana logs-kibana \
        up-apm down-apm logs-apm \
        stop-all rm-all

check-network:
	@echo "Checking for network $(NETWORK_NAME)..."
	@if ! docker network ls | grep -q "$(NETWORK_NAME)"; then \
		echo "Network $(NETWORK_NAME) does not exist. Creating..."; \
		docker network create $(NETWORK_NAME); \
	else \
		echo "Network $(NETWORK_NAME) already exists."; \
	fi

check-network-prod:
	@echo "Checking for network $(NETWORK_NAME_PROD)..."
	@if ! docker network ls | grep -q "$(NETWORK_NAME_PROD)"; then \
		echo "Network $(NETWORK_NAME_PROD) does not exist. Creating..."; \
		docker network create $(NETWORK_NAME_PROD); \
	else \
		echo "Network $(NETWORK_NAME_PROD) already exists."; \
	fi

# === High-level ===
up-all: check-network
	$(MAKE) up-db
	$(MAKE) up-odoo
	$(MAKE) up-pgadmin
	$(MAKE) up-adminer

up-all-no-cache: check-network
	$(MAKE) up-db-no-cache
	$(MAKE) up-odoo-no-cache
	$(MAKE) up-pgadmin
	$(MAKE) up-adminer

down-all:
	$(MAKE) down-db
	$(MAKE) down-odoo
	$(MAKE) down-pgadmin
	$(MAKE) down-adminer

up-all-without-monitoring: check-network
	$(MAKE) up-db
	$(MAKE) up-odoo
	$(MAKE) up-pgadmin
	$(MAKE) up-adminer

up-all-no-cache-without-monitoring: check-network
	$(MAKE) up-db-no-cache
	$(MAKE) up-odoo-no-cache
	$(MAKE) up-pgadmin
	$(MAKE) up-adminer

up-all-without-monitoring-prod: check-network-prod
	$(MAKE) up-db-no-cache-prod
	$(MAKE) up-odoo-prod
	$(MAKE) up-adminer-prod

up-all-no-cache-without-monitoring-prod: check-network-prod
	$(MAKE) up-db-no-cache-prod
	$(MAKE) up-odoo-no-cache-prod
	$(MAKE) up-adminer-no-cache-prod

down-all-without-monitoring:
	$(MAKE) down-db
	$(MAKE) down-odoo

down-all-without-monitoring-prod:
	$(MAKE) down-db-prod
	$(MAKE) down-odoo-prod
	$(MAKE) down-adminer-prod

down-all-volumes:
	$(MAKE) down-db-volumes
	$(MAKE) down-odoo-volumes
	$(MAKE) down-pgadmin-volumes
	$(MAKE) down-adminer-volumes

# === Monitoring stack ===
up-monitoring:
	$(DC) -f docker_compose/elastic/docker-compose.yml \
	      -f docker_compose/kibana/docker-compose.yml \
	      -f docker_compose/apm/docker-compose.yml $(ENV) up -d

up-monitoring-no-cache:
	$(DC) -f docker_compose/elastic/docker-compose.yml \
	      -f docker_compose/kibana/docker-compose.yml \
	      -f docker_compose/apm/docker-compose.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/elastic/docker-compose.yml \
	      -f docker_compose/kibana/docker-compose.yml \
	      -f docker_compose/apm/docker-compose.yml $(ENV) up -d

down-monitoring:
	$(DC) -f docker_compose/elastic/docker-compose.yml \
	      -f docker_compose/kibana/docker-compose.yml \
	      -f docker_compose/apm/docker-compose.yml down

down-monitoring-volumes:
	$(DC) -f docker_compose/elastic/docker-compose.yml \
	      -f docker_compose/kibana/docker-compose.yml \
	      -f docker_compose/apm/docker-compose.yml down -v

logs-monitoring:
	$(LOGS) $(ELASTIC_CONTAINER)
	$(LOGS) $(KIBANA_CONTAINER)
	$(LOGS) $(APM_CONTAINER)

# === DB ===
up-db:
	$(DC) -f docker_compose/db/docker-compose.yml $(ENV) up -d

up-db-no-cache:
	$(DC) -f docker_compose/db/docker-compose.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/db/docker-compose.yml $(ENV) up -d

up-db-no-cache-prod:
	$(DC) -f docker_compose/db/docker-compose-prod.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/db/docker-compose-prod.yml $(ENV) up -d

down-db:
	$(DC) -f docker_compose/db/docker-compose.yml down

down-db-prod:
	$(DC) -f docker_compose/db/docker-compose-prod.yml down

down-db-volumes:
	$(DC) -f docker_compose/db/docker-compose.yml down -v

logs-db:
	$(LOGS) $(DB_CONTAINER)

# make load-backup FILE=your_backup_file.dump
load-backup:
	@echo "Restoring backup $(FILE) into database..."
	docker exec -i $(DB_CONTAINER) pg_restore -U $(POSTGRES_USER) -d $(POSTGRES_DB) "/backups/$(FILE)"

# === Odoo full backups (DB + filestore) ===
# make backup-odoo
backup-odoo:
	@bash scripts/backup_odoo.sh

# make restore-odoo FILE=./backups/odoo_backup_lexora_2026-04-25_03-00-00.tar.gz
restore-odoo:
	@bash scripts/restore_odoo.sh "$(FILE)"

# make restore-odoo-force FILE=./backups/odoo_backup_lexora_2026-04-25_03-00-00.tar.gz
restore-odoo-force:
	@bash scripts/restore_odoo.sh "$(FILE)" --force

# === Scripts / tooling ===
health:
	@bash scripts/health_check.sh

health-json:
	@bash scripts/health_check.sh --json

odoo-shell:
	@bash scripts/odoo_shell.sh

db-shell:
	@bash scripts/db_shell.sh

# make update-module MODULE=language_portal
update-module:
	@bash scripts/update_module.sh "$(MODULE)"

# make update-module-test MODULE=language_portal
update-module-test:
	@bash scripts/update_module.sh "$(MODULE)" --test

# === Odoo/App ===
up-odoo:
	$(DC) -f docker_compose/odoo/docker-compose.yml $(ENV) up -d

up-odoo-no-cache:
	$(DC) -f docker_compose/odoo/docker-compose.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/odoo/docker-compose.yml $(ENV) up -d

up-odoo-prod:
	$(DC) -f docker_compose/odoo/docker-compose-prod.yml $(ENV) up -d

up-odoo-no-cache-prod:
	$(DC) -f docker_compose/odoo/docker-compose-prod.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/odoo/docker-compose-prod.yml $(ENV) up -d

down-odoo:
	$(DC) -f docker_compose/odoo/docker-compose.yml down

down-odoo-prod:
	$(DC) -f docker_compose/odoo/docker-compose-prod.yml down

down-odoo-volumes:
	$(DC) -f docker_compose/odoo/docker-compose.yml down -v

logs-odoo:
	$(LOGS) $(APP_CONTAINER)

migrations:
	$(EXEC) $(APP_CONTAINER) sh -c 'PYTHONPATH=/app/src:$$PYTHONPATH ${MANAGE_PY} makemigrations'

migrate:
	$(EXEC) $(APP_CONTAINER) sh -c 'PYTHONPATH=/app/src:$$PYTHONPATH ${MANAGE_PY} migrate'

superuser:
	$(EXEC) $(APP_CONTAINER) sh -c 'PYTHONPATH=/app/src:$$PYTHONPATH ${MANAGE_PY} createsuperuser'

test:
	$(EXEC) $(APP_CONTAINER) ${MANAGE_PY} test

collectstatic:
	$(EXEC) $(APP_CONTAINER) sh -c 'PYTHONPATH=/app/src:$$PYTHONPATH ${MANAGE_PY} collectstatic --noinput'

check-apm:
	$(EXEC) $(APP_CONTAINER) sh -c 'PYTHONPATH=/app/src:$$PYTHONPATH ${MANAGE_PY} elasticapm check'

test-apm:
	$(EXEC) $(APP_CONTAINER) sh -c 'PYTHONPATH=/app/src:$$PYTHONPATH ${MANAGE_PY} elasticapm test'

# === PgAdmin ===
up-pgadmin:
	$(DC) -f docker_compose/pgadmin/docker-compose.yml $(ENV) up -d

up-pgadmin-prod:
	$(DC) -f docker_compose/pgadmin/docker-compose-prod.yml $(ENV) up -d

down-pgadmin:
	$(DC) -f docker_compose/pgadmin/docker-compose.yml down

down-pgadmin-prod:
	$(DC) -f docker_compose/pgadmin/docker-compose-prod.yml down

down-pgadmin-volumes:
	$(DC) -f docker_compose/pgadmin/docker-compose.yml down -v

logs-pgadmin:
	$(LOGS) pgadmin

# === Adminer ===
up-adminer:
	$(DC) -f docker_compose/adminer/docker-compose.yml $(ENV) up -d

up-adminer-prod:
	$(DC) -f docker_compose/adminer/docker-compose-prod.yml $(ENV) up -d

up-adminer-no-cache-prod:
	$(DC) -f docker_compose/adminer/docker-compose-prod.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/adminer/docker-compose-prod.yml $(ENV) up -d

down-adminer:
	$(DC) -f docker_compose/adminer/docker-compose.yml down

down-adminer-prod:
	$(DC) -f docker_compose/adminer/docker-compose-prod.yml down

down-adminer-volumes:
	$(DC) -f docker_compose/adminer/docker-compose.yml down -v

logs-adminer:
	$(LOGS) adminer-postgres

# === Redis ===
up-redis:
	$(DC) -f docker_compose/redis/docker-compose.yml $(ENV) up -d

down-redis:
	$(DC) -f docker_compose/redis/docker-compose.yml down

logs-redis:
	$(LOGS) $(REDIS_CONTAINER)

# === Nginx ===
up-nginx:
	$(DC) -f docker_compose/nginx/docker-compose.yml $(ENV) up -d

down-nginx:
	$(DC) -f docker_compose/nginx/docker-compose.yml down

logs-nginx:
	$(LOGS) $(NGINX_CONTAINER)

# === Elastic ===
up-elastic:
	$(DC) -f docker_compose/elastic/docker-compose.yml $(ENV) up -d

down-elastic:
	$(DC) -f docker_compose/elastic/docker-compose.yml down

logs-elastic:
	$(LOGS) $(ELASTIC_CONTAINER)

# === Kibana ===
up-kibana:
	$(DC) -f docker_compose/kibana/docker-compose.yml $(ENV) up -d

down-kibana:
	$(DC) -f docker_compose/kibana/docker-compose.yml down

logs-kibana:
	$(LOGS) $(KIBANA_CONTAINER)

# === APM ===
up-apm:
	$(DC) -f docker_compose/apm/docker-compose.yml $(ENV) up -d

down-apm:
	$(DC) -f docker_compose/apm/docker-compose.yml down

logs-apm:
	$(LOGS) $(APM_CONTAINER)

# === Utils ===
stop-all:
	docker stop $$(docker ps -aq) || true

rm-all:
	docker rm $$(docker ps -aq) || true

# ============================================================
# === Dev stack (M0+) ========================================
# ============================================================
RABBITMQ_CONTAINER = rabbitmq
TRANSLATION_CONTAINER = translation_service
LLM_CONTAINER = llm_service
ANKI_CONTAINER = anki_service
AUDIO_CONTAINER    = audio_service
.PHONY: up-dev down-dev logs-dev ps-dev \
        up-rabbitmq down-rabbitmq logs-rabbitmq \
        up-translation down-translation up-translation-no-cache logs-translation \
        up-llm down-llm up-llm-no-cache logs-llm \
        up-anki down-anki up-anki-no-cache logs-anki \
        up-audio down-audio up-audio-no-cache logs-audio

# Start the full local development stack:
#   postgres · odoo · nginx · rabbitmq · redis · translation · llm · anki · audio
up-dev: check-network
	$(MAKE) up-db
	$(DC) -f docker_compose/rabbitmq/docker-compose.yml $(ENV) up -d
	$(DC) -f docker_compose/redis/docker-compose.yml $(ENV) up -d
	$(MAKE) up-odoo
	$(DC) -f docker_compose/translation/docker-compose.yml $(ENV) up -d
	$(DC) -f docker_compose/llm/docker-compose.yml $(ENV) up -d
	$(DC) -f docker_compose/anki/docker-compose.yml $(ENV) up -d
	$(DC) -f docker_compose/audio/docker-compose.yml $(ENV) up -d

down-dev:
	$(DC) -f docker_compose/audio/docker-compose.yml down
	$(DC) -f docker_compose/anki/docker-compose.yml down
	$(DC) -f docker_compose/llm/docker-compose.yml down
	$(DC) -f docker_compose/translation/docker-compose.yml down
	$(MAKE) down-odoo
	$(DC) -f docker_compose/redis/docker-compose.yml down
	$(DC) -f docker_compose/rabbitmq/docker-compose.yml down
	$(MAKE) down-db

# List every container that belongs to the dev stack (quick health glance).
ps-dev:
	@docker ps --filter "name=^$(DB_CONTAINER)$$" \
	           --filter "name=^$(APP_CONTAINER)$$" \
	           --filter "name=^$(NGINX_CONTAINER)$$" \
	           --filter "name=^$(RABBITMQ_CONTAINER)$$" \
	           --filter "name=^$(REDIS_CONTAINER)$$" \
	           --filter "name=^$(TRANSLATION_CONTAINER)$$" \
	           --filter "name=^$(LLM_CONTAINER)$$" \
	           --filter "name=^$(ANKI_CONTAINER)$$" \
	           --filter "name=^$(AUDIO_CONTAINER)$$" \
	           --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Tail the last 50 lines of every dev-stack container's log.
# Useful when diagnosing cross-service issues (e.g. RabbitMQ event flow).
logs-dev:
	@for c in $(DB_CONTAINER) $(APP_CONTAINER) $(NGINX_CONTAINER) \
	         $(RABBITMQ_CONTAINER) $(REDIS_CONTAINER) \
	         $(TRANSLATION_CONTAINER) $(LLM_CONTAINER) \
	         $(ANKI_CONTAINER) $(AUDIO_CONTAINER); do \
	    echo "───────── $$c ─────────"; \
	    docker logs --tail 50 $$c 2>&1 || echo "(container $$c not running)"; \
	done

# === RabbitMQ ===
up-rabbitmq:
	$(DC) -f docker_compose/rabbitmq/docker-compose.yml $(ENV) up -d

down-rabbitmq:
	$(DC) -f docker_compose/rabbitmq/docker-compose.yml down

logs-rabbitmq:
	$(LOGS) $(RABBITMQ_CONTAINER)

# === Translation service ===
up-translation:
	$(DC) -f docker_compose/translation/docker-compose.yml $(ENV) up -d

up-translation-no-cache:
	$(DC) -f docker_compose/translation/docker-compose.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/translation/docker-compose.yml $(ENV) up -d

down-translation:
	$(DC) -f docker_compose/translation/docker-compose.yml down

logs-translation:
	$(LOGS) $(TRANSLATION_CONTAINER)

# === LLM service ===
up-llm:
	$(DC) -f docker_compose/llm/docker-compose.yml $(ENV) up -d

up-llm-no-cache:
	$(DC) -f docker_compose/llm/docker-compose.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/llm/docker-compose.yml $(ENV) up -d

down-llm:
	$(DC) -f docker_compose/llm/docker-compose.yml down

logs-llm:
	$(LOGS) $(LLM_CONTAINER)

# === Anki import service ===
up-anki:
	$(DC) -f docker_compose/anki/docker-compose.yml $(ENV) up -d

up-anki-no-cache:
	$(DC) -f docker_compose/anki/docker-compose.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/anki/docker-compose.yml $(ENV) up -d

down-anki:
	$(DC) -f docker_compose/anki/docker-compose.yml down

logs-anki:
	$(LOGS) $(ANKI_CONTAINER)

# === Audio / TTS service ===
up-audio:
	$(DC) -f docker_compose/audio/docker-compose.yml $(ENV) up -d

up-audio-no-cache:
	$(DC) -f docker_compose/audio/docker-compose.yml $(ENV) build --no-cache
	$(DC) -f docker_compose/audio/docker-compose.yml $(ENV) up -d

down-audio:
	$(DC) -f docker_compose/audio/docker-compose.yml down

logs-audio:
	$(LOGS) $(AUDIO_CONTAINER)


# =============================================================================
# Developer tooling
# =============================================================================
.PHONY: install-dev lint fmt fmt-check typecheck security pre-commit-install \
        pre-commit-run audit

## Install all dev tools into the local venv
install-dev:
	pip install -r requirements/dev-requirements.txt
	pre-commit install --install-hooks

## Ruff lint (auto-fix)
lint:
	ruff check --fix src/addons services

## Ruff format (apply)
fmt:
	ruff format src/addons services

## Ruff format (check only — used in CI)
fmt-check:
	ruff format --check src/addons services

## Mypy type-check on FastAPI services
typecheck:
	mypy services/translation/main.py services/llm/main.py \
	     services/anki/main.py services/audio/main.py

## Bandit security scan
security:
	bandit -c pyproject.toml -ll -r services/ src/addons/language_*/

## pip-audit — check all service deps for known CVEs
audit:
	@for svc in translation llm anki audio; do \
	  echo "=== $$svc ==="; \
	  pip-audit -r services/$$svc/requirements.txt; \
	done

## Run all pre-commit hooks against all files
pre-commit-install:
	pre-commit install --install-hooks

pre-commit-run:
	pre-commit run --all-files

## Full local quality gate (lint + fmt-check + typecheck + security)
check:
	$(MAKE) lint
	$(MAKE) fmt-check
	$(MAKE) typecheck
	$(MAKE) security

# ============================================================
# M38 — Production targets
# ============================================================
# Manual deployment workflow (NO GitHub Actions):
#   git pull
#   cp .env.prod.example .env.prod  # first time only
#   vi .env.prod                    # fill in real secrets
#   make prod-env-check
#   make prod-build
#   make prod-up
#
# See docs/DECISIONS.md ADR-037 for the architectural rationale.
# ============================================================

PROD_COMPOSE = docker compose -f docker-compose.prod.yml
PROD_ENV     = --env-file .env.prod

.PHONY: prod-env-check prod-up prod-down prod-build prod-logs prod-ps prod-restart prod-restore-db

## Validate .env.prod exists and has no CHANGE_ME_ placeholders
prod-env-check:
	@if [ ! -f .env.prod ]; then \
	  echo "ERROR: .env.prod is missing.  Run: cp .env.prod.example .env.prod && \$$EDITOR .env.prod"; \
	  exit 1; \
	fi
	@if grep -q '^[A-Z_]*=CHANGE_ME_' .env.prod; then \
	  echo "ERROR: .env.prod still contains CHANGE_ME_ placeholders.  Unfilled variables:"; \
	  grep -n '^[A-Z_]*=CHANGE_ME_' .env.prod | sed 's/^/  /'; \
	  echo ""; \
	  echo "Generate strong secrets with: openssl rand -base64 32 | tr -d '/='"; \
	  exit 1; \
	fi
	@echo "prod-env-check: OK (.env.prod exists and contains no CHANGE_ME_ placeholders)"

## Build (or rebuild) custom production images: odoo + 4 worker services
prod-build: prod-env-check
	$(PROD_COMPOSE) $(PROD_ENV) build

## Build with no cache (slower but pulls fresh base images)
prod-build-no-cache: prod-env-check
	$(PROD_COMPOSE) $(PROD_ENV) build --no-cache

## Start the full production stack (detached)
prod-up: prod-env-check
	$(PROD_COMPOSE) $(PROD_ENV) up -d
	@echo ""
	@echo "Production stack starting.  Health-check after ~60 s:"
	@echo "  curl -I https://lexora.avantgarde.systems"
	@echo "  make prod-logs        # tail every service"
	@echo "  make prod-ps          # list containers"

## Stop the production stack (volumes preserved)
prod-down:
	$(PROD_COMPOSE) $(PROD_ENV) down

## DESTRUCTIVE — stop AND remove named volumes.  Only run if you
## intend to lose ALL production data (Postgres, Odoo filestore,
## Redis, RabbitMQ, model caches).  Required to type the literal
## word YES to proceed.
prod-down-volumes:
	@read -p "Type YES to permanently delete ALL production volumes: " confirm; \
	if [ "$$confirm" = "YES" ]; then \
	  $(PROD_COMPOSE) $(PROD_ENV) down -v; \
	else \
	  echo "Aborted."; exit 1; \
	fi

## Tail logs from every prod service (Ctrl-C to detach)
prod-logs:
	$(PROD_COMPOSE) $(PROD_ENV) logs -f --tail=200

## List prod containers
prod-ps:
	$(PROD_COMPOSE) $(PROD_ENV) ps

## Restart a single prod service.  Usage: make prod-restart SVC=odoo
prod-restart:
	@if [ -z "$(SVC)" ]; then \
	  echo "Usage: make prod-restart SVC=<service-name>"; \
	  echo "Services: postgres redis rabbitmq odoo nginx translation-service llm-service anki-service audio-service"; \
	  exit 1; \
	fi
	$(PROD_COMPOSE) $(PROD_ENV) restart $(SVC)

## Documentation-only helper: prints the steps to restore a .zip
## backup via Odoo's /web/database/manager.  No automation —
## the operator does the restore via the web UI.
prod-restore-db:
	@echo "════════════════════════════════════════════════════════════"
	@echo " Restore an Odoo .zip backup on the production host"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo " 1. Make sure the prod stack is up: make prod-up"
	@echo " 2. Browse to:  https://lexora.avantgarde.systems/web/database/manager"
	@echo " 3. Click 'Restore Database'"
	@echo " 4. Master Password:  value of ADMIN_PASSWD in .env.prod"
	@echo " 5. File:             your .zip backup (max 2 GB)"
	@echo " 6. Database Name:    a name for the restored DB"
	@echo " 7. Click 'Continue'"
	@echo ""
	@echo " If the upload exceeds 2 GB, raise nginx's client_max_body_size"
	@echo " in docker_compose/nginx/nginx.prod.conf and run"
	@echo " 'make prod-restart SVC=nginx'."
	@echo "════════════════════════════════════════════════════════════"
