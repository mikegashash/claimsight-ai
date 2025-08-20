#!/usr/bin/env bash
set -euo pipefail

# Nice cache locations
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$PWD/.cache}"
export PYTHONPATH="${PYTHONPATH:-$PWD}"

echo "==> Python & pip"
python -V
python -m pip --version

echo "==> Upgrade pip"
python -m pip install --upgrade pip

echo "==> Install project and deps (Torch CPU wheels enabled)"
# Make torch resolve reliably on CPU-only runners/environments
export PIP_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cpu"

# Install your package first (editable)
python -m pip install -e .

# Install API requirements if present, otherwise fall back to root
if [ -f "claimsight_ai/api/requirements.txt" ]; then
  python -m pip install --no-cache-dir -r claimsight_ai/api/requirements.txt
else
  python -m pip install --no-cache-dir -r requirements.txt
fi

# Small spaCy model (optional; ignore if offline)
python -m spacy download en_core_web_sm || true

echo "==> Seed minimal policy data (idempotent)"
mkdir -p data/policies vectorstore
if [ ! -f data/policies/policy_sample.txt ]; then
  cat > data/policies/policy_sample.txt <<'TXT'
Section 1: Property Coverage
Dwelling (Cov A) $300,000; Personal Property (Cov C) $50,000.

Section 2: Water Backup Endorsement
Provides up to $10,000 for direct physical loss caused by water backup from sewers or drains.
TXT
fi

echo "==> Build vector index (idempotent; best-effort)"
python - <<'PY'
try:
    from claimsight_ai.rag.index_policies import build_index
    print("index:", build_index())
except Exception as e:
    import traceback; traceback.print_exc()
    print("Skipping index build (non-fatal).")
PY

echo "==> (Optional) Train toy risk model (best-effort)"
python - <<'PY'
try:
    from claimsight_ai.api.main import train_risk_model
    try:
        train_risk_model()
        print("risk model: trained")
    except Exception as e:
        import traceback; traceback.print_exc()
        print("risk model: skipped ->", e)
except Exception:
    print("risk model: function not available; skipping.")
PY

echo "==> Bootstrap complete."
echo "Run the API with:"
echo "  uvicorn claimsight_ai.api.main:app --host 0.0.0.0 --port 8000 --reload"
