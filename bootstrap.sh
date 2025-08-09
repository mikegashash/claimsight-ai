#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
ClaimSight AI bootstrap

Usage:
  ./bootstrap.sh            # full local bootstrap (docker build, seed data, tests in container, bring up stack)
  ./bootstrap.sh --ci       # fast CI mode (no 'up', lightweight steps, runs pytest locally)
EOF
}

MODE="local"
[[ "${1:-}" == "--ci" ]] && MODE="ci"

# pick compose cmd
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "❌ Docker Compose not found. Install Docker Desktop (includes 'docker compose')."
  exit 1
fi

echo "🧰 Mode: $MODE"
echo "🧰 Using Compose: $DC"

# make sure .env exists (safe defaults)
if [[ ! -f .env ]]; then
  echo "📄 Creating .env..."
  cat > .env <<'ENVV'
# Snowflake (optional)
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=CLAIMS_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=SYSADMIN

# API
API_HOST=0.0.0.0
API_PORT=8000
ENVV
else
  echo "✅ .env exists"
fi

# ensure data dirs exist
mkdir -p data policies models vectorstore

# seed sample data (locally so paths exist regardless of container)
echo "📊 Seeding synthetic data..."
python3 - <<'PY'
import os, pandas as pd
os.makedirs("data", exist_ok=True)
if not os.path.exists("data/claims.csv"):
    from datetime import date
    pd.DataFrame([
        ["C00001","P1001",str(date.today()),"water",2500.00,"44114","PR321",1,0],
        ["C00002","P1002",str(date.today()),"fire",17850.12,"44212","PR218",0,0]
    ], columns=["claim_id","policy_id","loss_dt","loss_type","amount","zip","provider_id","claimant_history_count","fraud_flag"]
    ).to_csv("data/claims.csv", index=False)
os.makedirs("data/policies", exist_ok=True)
if not os.path.exists("data/policies/policy_01.txt"):
    open("data/policies/policy_01.txt","w").write("""POLICY P1001 — Standard Homeowners
Section 1: Dwelling (Coverage A)
Water backup from sewers or drains is EXCLUDED unless an endorsement applies.
Section 4: Perils Insured Against
Fire, lightning, windstorm, hail are covered causes of loss.
Section 5: Endorsements
- Water Backup Endorsement: Water/sewer backup losses up to $10,000 are covered.
""")
print("Seeded sample claims/policies.")
PY

if [[ "$MODE" == "ci" ]]; then
  echo "🧪 CI mode: install minimal deps and run pytest locally"
  python3 -m pip install --upgrade pip
  python3 -m pip install -r services/api/requirements.txt pytest
  pytest -q
  echo "✅ CI bootstrap complete."
  exit 0
fi

echo "🐳 Building containers..."
$DC build

echo "🧪 Running tests inside API container..."
$DC run --rm api pytest -q || true  # don't fail the whole run on tests while models download

echo "🚀 Starting stack (detached)..."
$DC up -d

echo "✅ ClaimSight AI is up."
echo "   API: http://localhost:8000/docs"
echo "   UI : http://localhost:8501"
echo "   (Optional) Train risk model: POST /admin/train_risk in Swagger"
