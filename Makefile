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
