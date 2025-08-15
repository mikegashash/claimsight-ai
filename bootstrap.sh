#!/usr/bin/env bash
set -euo pipefail

# 0) Nice cache location for HF models (avoid /app permission noise)
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"

# 1) Python deps (Torch CPU wheel for Codespaces)
python -m pip install --upgrade pip
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.3.1
python -m pip install -r requirements.txt --no-input

# 2) Seed minimal policy data (idempotent)
mkdir -p data/policies vectorstore
if [ ! -f data/policies/policy_sample.txt ]; then
  cat > data/policies/policy_sample.txt <<'TXT'
Section 1: Property Coverage
Dwelling (Cov A) $300,000; Personal Property (Cov C) $50,000.

Section 2: Water Backup Endorsement
Provides up to $10,000 for direct physical loss caused by water backup from sewers or drains.
TXT
fi

# 3) Build FAISS index (idempotent)
python - <<'PY'
from claimsight_ai.rag.index_policies import build_index
print("index:", build_index())
PY

# 4) (Optional) Pre-train toy risk model so /claims/risk is ready
python - <<'PY'
from claimsight_ai.api.main import train_risk_model
try:
    train_risk_model()
    print("risk model: trained")
except Exception as e:
    print("risk model: skipped ->", e)
PY

echo "Bootstrap complete. Run:"
echo "  python -m uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload"

