# -------------------------------
# ClaimSight AI - Developer Makefile
# -------------------------------

SHELL := /bin/bash
# Prefer `docker compose`, fall back to `docker-compose`
DC := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

SVC  ?= api
PORT ?= 8000
SEED ?= 1            # set SEED=0 to skip seeding on `make up`

.DEFAULT_GOAL := help

# ========= Basics =========
.PHONY: help
help:
	@echo "ClaimSight AI — Make targets"
	@awk 'BEGIN{FS=":.*## "}; /^[a-zA-Z0-9_.-]+:.*## /{printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: build
build: ## Build images
	$(DC) build

.PHONY: up
up: build ## Build & start stack; wait for API; optional seed
	$(DC) up -d postgres chroma $(SVC)
	$(MAKE) wait
	@if [ "$(SEED)" = "1" ]; then $(MAKE) seed; fi
	@echo "API: http://localhost:$(PORT)/docs"
	@echo "UI : http://localhost:8501"

.PHONY: wait
wait: ## Wait for /healthz (from inside container)
	@echo "Waiting for API on :$(PORT)..."
	@for i in $$(seq 1 60); do \
	  $(DC) exec -T $(SVC) python - <<'PY' >/dev/null 2>&1 && { echo "API ready"; exit 0; } || true; \
import urllib.request as U; U.urlopen("http://localhost:8000/healthz")
PY
	  sleep 1; \
	done; \
	echo "API did not become ready"; exit 1

.PHONY: down
down: ## Stop stack (keep volumes)
	$(DC) down --remove-orphans

.PHONY: clean
clean: ## Stop stack + remove volumes and dangling images (DANGEROUS)
	$(DC) down -v --remove-orphans || true
	docker image prune -f || true

.PHONY: logs
logs: ## Tail API logs
	$(DC) logs -f $(SVC)

.PHONY: logs-all
logs-all: ## Tail all service logs
	$(DC) logs -f

.PHONY: ps
ps: ## Show running containers
	$(DC) ps

.PHONY: restart
restart: ## Restart API container
	$(DC) restart $(SVC)

# ========= Data =========
.PHONY: seed
seed: ## Generate synthetic data/policies inside running API container
	$(DC) exec -T $(SVC) python scripts/make_synth_data.py || true
	$(DC) exec -T $(SVC) python scripts/make_fake_policies.py || true

# ========= Tests =========
.PHONY: test
test: ## Run pytest inside API container
	$(DC) exec -T $(SVC) pytest -vv -p no:cacheprovider

# ========= Model training =========
.PHONY: train
train: ## Train toy XGBoost model via admin API
	$(DC) exec -T $(SVC) python - <<'PY'
import urllib.request, json
req = urllib.request.Request("http://localhost:8000/admin/train_risk",
                             data=b"{}", method="POST",
                             headers={"Content-Type":"application/json"})
with urllib.request.urlopen(req) as r:
    print("status:", r.status); print(r.read().decode()[:300])
PY

# ========= Utilities =========
.PHONY: shell-api
shell-api: ## Shell into API container (bash or sh)
	-$(DC) exec $(SVC) bash || $(DC) exec $(SVC) sh

.PHONY: shell-ui
shell-ui: ## Shell into UI container (bash or sh)
	-$(DC) exec ui bash || $(DC) exec ui sh

.PHONY: compose-config
compose-config: ## Show resolved docker compose config
	$(DC) config

.PHONY: doctor
doctor: ## Print sys.path & verify imports inside container
	$(DC) exec -T $(SVC) python - <<'PY'
import sys, importlib; print("sys.path[:10]:\n"+"\n".join(sys.path[:10]))
importlib.import_module("claimsight_ai.integrations"); print("imports OK")
PY
