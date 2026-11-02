# VDS Ecosystem Infrastructure Makefile
# Phase: ecosystem-infrastructure-evolution v2.10.0
#
# Quick targets for the unified docker/ three-tier compose topology.
# Run from vds-scripts repo root.
#
# Tiers (per ADR-INF-10):
#   - Tier 1 docker-compose.infra.yml     : postgres, redis, qdrant
#   - Tier 2 docker-compose.services.yml  : memory-api/worker, scheduler, multi-agent (long-running)
#   - Tier 3 docker-compose.cli.yml       : audit, pdf, progress, db-query, vds-cli, mcp-server (CLI)
#
# Long-running services use `up -d` (`make up-memory`, etc.).
# CLI containers use `run --rm` (`make run-audit ARGS="workflow run --project X"`).

.PHONY: help \
        env-link \
        up-infra up-memory up-scheduler up-multi-agent up-services \
        run-audit run-audit-migrate run-pdf run-progress run-progress-migrate run-db-query run-vds-cli \
        down restart status verify build-cli clean-volumes

# Hybrid project-identity anchor: -p flag + `name: vds-platform` in compose YAML
# both pin the project as "vds-platform" regardless of CWD (ADR-INF-7).
COMPOSE_PROJECT := vds-platform
INFRA           := -f docker/docker-compose.infra.yml
SERVICES        := -f docker/docker-compose.infra.yml -f docker/docker-compose.services.yml
CLI             := -f docker/docker-compose.infra.yml -f docker/docker-compose.cli.yml
ALL             := -f docker/docker-compose.infra.yml -f docker/docker-compose.services.yml -f docker/docker-compose.cli.yml

DC := docker compose -p $(COMPOSE_PROJECT)

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# === One-time bootstrap: env symlink (v2.0.17 N.52 consolidation) ===========
# Compose's `${VAR}` substitution reads from compose's own .env (or shell),
# NOT from the per-service env_file: block. To make ~/.vds/.env feed BOTH
# in-container env_file AND YAML interpolation, link docker/.env -> ~/.vds/.env.
env-link: ## Create docker/.env -> ~/.vds/.env symlink (idempotent; gitignored)
	@if [ ! -L docker/.env ]; then \
		ln -sf $$HOME/.vds/.env docker/.env && \
		echo "Linked docker/.env -> ~/.vds/.env"; \
	else \
		echo "docker/.env already linked"; \
	fi

# === Long-running services (Tier 2; `up -d` keeps them running) ============
# Per spec v2.12.2 P4 deploy postmortem: `--build` is included by default so
# pulling latest master always rebuilds the service image. Operators who want
# to skip the build (image is fresh) can set NO_BUILD=1.
BUILD_FLAG := $(if $(NO_BUILD),,--build)

up-infra: env-link ## Start shared infrastructure only (postgres, redis, qdrant)
	$(DC) $(INFRA) --profile infra up -d

up-memory: env-link ## Start infra + memory-api + memory-worker (rebuilds image; set NO_BUILD=1 to skip)
	$(DC) $(SERVICES) --profile memory up -d $(BUILD_FLAG)

up-scheduler: env-link ## Start infra + scheduler-orchestrator (rebuilds image; needs VDS_SCHEDULER_ENABLED=true; set NO_BUILD=1 to skip)
	# Phase 217 HTTP refactor: scheduler depends_on memory-api; activate both --profile scheduler and --profile memory.
	$(DC) $(SERVICES) --profile scheduler --profile memory up -d $(BUILD_FLAG)

up-multi-agent: env-link ## Start infra + multi-agent-orchestrator (rebuilds image; set NO_BUILD=1 to skip)
	$(DC) $(SERVICES) --profile multi-agent up -d $(BUILD_FLAG)

up-services: env-link ## Start infra + all 4 long-running services (rebuilds images; set NO_BUILD=1 to skip)
	# Tier 3B retired in v2.15.10 (ADR-INF-10): long-running services only need services.yml.
	$(DC) $(SERVICES) --profile full up -d $(BUILD_FLAG)

# === CLI containers (Tier 3; `run --rm` invocation pattern) ================
# Override ARGS to pass subcommands. ARGS defaults to --help.
ARGS ?= --help

run-audit: env-link ## Run audit CLI (set ARGS="workflow run --project X")
	$(DC) $(CLI) --profile audit run --rm audit-orchestrator $(ARGS)

# v2.15.10 (ADR-INF-10): Tier 3B migrate containers retired.
# Migrations run via --entrypoint override against the orchestrator service container.
run-audit-migrate: env-link ## Run audit Alembic migrations to head (one-shot)
	$(DC) $(CLI) --profile audit run --rm --no-deps --entrypoint /opt/venv/bin/alembic audit-orchestrator -c /app/audit_orchestrator/alembic.ini upgrade head

run-pdf: env-link ## Run pdf CLI (set ARGS="merge a.pdf b.pdf -o c.pdf")
	$(DC) $(CLI) --profile pdf run --rm pdf-orchestrator $(ARGS)

run-progress: env-link ## Run progress CLI (set ARGS="generate --project X")
	$(DC) $(CLI) --profile progress run --rm progress-report-orchestrator $(ARGS)

# v2.15.10 (ADR-INF-10): Tier 3B migrate containers retired.
# Migrations run via --entrypoint override against the orchestrator service container.
run-progress-migrate: env-link ## Run progress Alembic migrations to head (one-shot)
	$(DC) $(CLI) --profile progress run --rm --no-deps --entrypoint /opt/venv/bin/alembic progress-report-orchestrator -c /app/progress_report_orchestrator/alembic.ini upgrade head

run-db-query: env-link ## Run db-query CLI (set ARGS="query --connection prod -q 'SELECT 1'")
	$(DC) $(CLI) --profile db-query run --rm db-query-orchestrator $(ARGS)

run-vds-cli: env-link ## Run unified vds-cli router (set ARGS="<service> <command>")
	$(DC) $(CLI) --profile vds-cli run --rm vds-cli $(ARGS)

# === Build / build CLI images ahead of time ================================

build-cli: ## Pre-build all 6 CLI images (audit, pdf, progress, db-query, vds-cli, mcp-server)
	$(DC) $(CLI) --profile cli build

# === Lifecycle =============================================================

down: ## Stop and remove ALL containers (volumes preserved)
	$(DC) $(ALL) --profile full --profile cli down

restart: down up-services ## Stop everything and start the long-running services

status: ## Show running containers and ports
	@docker ps --filter "name=vds-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

verify: ## Run topology verification (stdlib python3, no uv)
	python3 scripts/verify-infra-topology.py --profile infra

clean-volumes: ## Remove all VDS-managed volumes (DESTRUCTIVE — prompts first)
	@echo "About to remove: vds_postgres_data vds_redis_data vds_qdrant_data vds-audit-cache vds-memory-logs vds-pdf-cache vds-progress-cache"
	@read -p "Type YES to confirm: " confirm && [ "$$confirm" = "YES" ] || (echo "Aborted." && exit 1)
	docker volume rm -f vds_postgres_data vds_redis_data vds_qdrant_data vds-audit-cache vds-memory-logs vds-pdf-cache vds-progress-cache 2>/dev/null || true
