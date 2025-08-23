import os, json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel
import yaml

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
