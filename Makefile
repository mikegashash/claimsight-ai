# -------------------------------
# ClaimSight AI - Developer Makefile
# -------------------------------

SHELL := /bin/bash
# Prefer `docker compose`, fall back to `docker-compose`
DC := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

# ========= Basics =========
.PHONY: help
help:
	@echo "ClaimSight AI — Make targets"
	@echo "  make up            # Build & start stack (detached)"
	@echo "  make build         # Build images only"
	@echo "  make down          # Stop and remove stack"
	@echo "  make logs          # Tail all service logs"
	@echo "  make ps            # Show running containers"
	@echo "  make restart       # Restart stack"
	@echo "  make clean         # Remove containers/images/volumes (DANGEROUS)"

# ========= Data =========
.PHONY: seed
seed:  ## Generate synthetic data/policies (inside API container context)
	$(DC) run --rm api python scripts/make_synth_data.py || true
	$(DC) run --rm api python scripts/make_fake_policies.py || true

# ========= Dev/Run =========
.PHONY: build
build:
	$(DC) build

.PHONY: up
up: build seed
	$(DC) up -d
	@echo "API: http://localhost:8000/docs"
	@echo "UI : http://localhost:8501"

.PHONY: down
down:
	$(DC) down

.PHONY: restart
restart: down up

.PHONY: logs
logs:
	$(DC) logs -f

.PHONY: ps
ps:
	$(DC) ps

# ========= Tests =========
.PHONY: test
test:  ## Run pytest inside the API container
	$(DC) run --rm api pytest -q

# ========= Model training =========
.PHONY: train
train:  ## Train toy XGBoost model by calling admin endpoint
	@curl -s -X POST http://localhost:8000/admin/train_risk | jq . || \
	 (echo "Tip: make sure the stack is up: 'make up'"; exit 1)

# ========= Utilities =========
.PHONY: shell-api
shell-api:  ## Interactive shell inside API container
	$(DC) exec api bash || true

.PHONY: shell-ui
shell-ui:
	$(DC) exec ui bash || true

.PHONY: clean
clean:  ## WARNING: nukes volumes and cached models
	$(DC) down -v --remove-orphans || true
	docker image prune -f || true
