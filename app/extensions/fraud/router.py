from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
import os, json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel
import yaml
# add near the existing imports
from typing import Any
from pydantic import BaseModel, field_validator

class SimpleClaim(BaseModel):
    claim_id: str
    line_of_business: str = "Auto"
    late_report_days: int = 0
    claim_amount: float = 0.0
    paid_to_date: float = 0.0
    reserve: float = 0.0
    claimant_age: int = 40
    injury_severity: int = 0
    police_report: int | bool = 0
    prior_claims_count: int = 0
    repair_shop_id: str | None = None
    provider_id: str | None = None

    # make booleans or "true"/"false" work for police_report
    @field_validator("police_report", mode="before")
    @classmethod
    def coerce_police(cls, v: Any) -> int:
        if isinstance(v, bool): return int(v)
        if isinstance(v, (int, float)): return int(v)
        if isinstance(v, str): return 1 if v.strip().lower() in {"1","true","yes","y"} else 0
        return 0

@router.post("/score_simple")
def score_simple(payload: SimpleClaim):
    """
    Friendlier scoring: fills defaults & coerces types, then reuses the same logic.
    """
    # convert to the strict Claim used by /score
    strict = Claim(**payload.model_dump())
    return score_one(strict)

from .scoring_rules import score_rules
from .features import enrich

# Config
CFG_PATH = os.path.join(os.path.dirname(__file__), "config", "rings.yaml")
with open(CFG_PATH, "r") as f:
    cfg = yaml.safe_load(f) or {}
RINGS = {
    "ring_providers": set(cfg.get("ring_providers", [])),
    "ring_shops": set(cfg.get("ring_shops", [])),
}

# Optional ML
MODEL = None
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model", "model.joblib")
ENGINE = os.getenv("FRAUD_ENGINE", "rules")  # "rules" | "ml"
if ENGINE == "ml" and os.path.exists(MODEL_PATH):
    import joblib
    MODEL = joblib.load(MODEL_PATH)

class Claim(BaseModel):
    claim_id: str
    line_of_business: str
    state: str
    incident_date: Optional[str] = None
    report_date: Optional[str] = None
    late_report_days: int
    claim_amount: float
    paid_to_date: float
    reserve: float
    claimant_age: int
    injury_severity: str
    police_report: int
    prior_claims_count: int
    vin: Optional[str] = ""
    provider_id: Optional[str] = ""
    repair_shop_id: Optional[str] = ""

router = APIRouter(prefix="/fraud", tags=["fraud"])

def score_ml(c: Dict[str, Any]) -> Dict[str, Any]:
    if MODEL is None:
        return score_rules(c, RINGS)
    import pandas as pd
    df = enrich(pd.DataFrame([c]))
    prob = float(MODEL.predict_proba(df)[0,1])
    return {"fraud_probability": prob, "label": int(prob>=0.5), "reasons": []}

@router.get("/health")
def health():
    return {"ok": True, "engine": ENGINE, "model_loaded": MODEL is not None}

@router.post("/score")
def score_one(payload: Claim):
    c = payload.dict()
    return score_ml(c) if ENGINE == "ml" else score_rules(c, RINGS)

@router.post("/bulk_score")
def score_bulk(payload: List[Claim]):
    if ENGINE == "ml":
        return [score_ml(p.dict()) for p in payload]
    return [score_rules(p.dict(), RINGS) for p in payload]
# ---- Model / Training helpers (read state from API module) ----
try:
    # we import the api module to peek at global MODEL / EXPLAINER the service owns
    from claimsight_ai.api import main as api_main
except Exception:
    api_main = None

# try to import the training function already defined in api.main
try:
    from claimsight_ai.api.main import train_risk_model as _train_risk_inproc
except Exception:
    _train_risk_inproc = None

@router.get("/model_status")
def fraud_model_status():
    loaded = bool(getattr(api_main, "MODEL", None)) if api_main else False
    explainer = bool(getattr(api_main, "EXPLAINER", None)) if api_main else False
    engine = "model" if loaded else "rules"
    return {
        "engine": engine,
        "model_loaded": loaded,
        "explainer_loaded": explainer,
        "features": getattr(api_main, "FEATURES", []),
        "models_dir": str(getattr(api_main, "MODELS_DIR", Path("models")).resolve()),
        "data_dir": str(getattr(api_main, "DATA_DIR", Path("data")).resolve()),
    }

@router.post("/admin/upload_csv")
async def admin_upload_csv(file: UploadFile = File(...)):
    """Upload a training CSV (writes to DATA_DIR/claims.csv)."""
    if file.filename and not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv")
    data_dir = getattr(api_main, "DATA_DIR", Path(os.environ.get("DATA_DIR", "data")))
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / "claims.csv"
    content = await file.read()
    target.write_bytes(content)
    # tiny sanity check: count lines
    line_count = content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0)
    return {"ok": True, "path": str(target.resolve()), "approx_rows": max(0, line_count - 1)}

@router.post("/admin/train")
def admin_train_now():
    """Trigger in-process training using the API's built-in function."""
    if _train_risk_inproc is None:
        raise HTTPException(status_code=500, detail="Training function not available in-process.")
    try:
        out = _train_risk_inproc()
        return {"ok": True, "result": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {e!s}") from e
