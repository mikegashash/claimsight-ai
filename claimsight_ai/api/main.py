# services/api/main.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Dict

import sys
REPO_ROOT = Path(__file__).resolve().parents[2]  # repo root (parent of 'claimsight_ai')
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
try:
    from app.extensions.fraud.router import router as fraud_router
except ModuleNotFoundError:
    from claimsight_ai.extensions.fraud.router import router as fraud_router

# ---------- ENV / Paths ----------
APP_HOME = Path(os.environ.get("APP_HOME", Path.cwd()))
DATA_DIR = Path(os.environ.get("DATA_DIR", APP_HOME / "data"))
MODELS_DIR = Path(os.environ.get("MODELS_DIR", APP_HOME / "models"))

# Detect Codespaces and decide where to mount docs
IS_CODESPACES = bool(
    os.getenv("CODESPACE_NAME")
    or os.getenv("CODESPACES")
    or os.getenv("GITHUB_CODESPACE_TOKEN")
)
DOCS_AT_ROOT = os.getenv("DOCS_AT_ROOT", "1" if IS_CODESPACES else "0") == "1"
ROOT_PATH = os.getenv("ROOT_PATH", "")

# ---------- Models (dataclass fallback if integrations package not importable) ----------
try:
    from ..integrations.models import PolicyQuery, ClaimFNOL  # type: ignore
except Exception:
    from dataclasses import dataclass

    @dataclass
    class PolicyQuery:
        policy_id: Optional[str] = None
        coverage: Optional[str] = None
        text: Optional[str] = None

    @dataclass
    class ClaimFNOL:
        claim_id: Optional[str] = None
        policy_id: Optional[str] = None
        description: Optional[str] = None
        loss_date: Optional[str] = None
        metadata: Optional[Dict] = None

# ---------- Local services (relative imports; no PYTHONPATH issues) ----------
# TEMPORARILY COMMENTED OUT FOR DEBUGGING
# from ..rag.index_policies import build_index
# from ..rag.retriever import PolicyRetriever
# from ..rag.reranker import rerank

# from ..ocr.pii import mask_pii
# from ..snowflake_io import df_to_snowflake, snowflake_query
# from ..report import build_claim_packet_pdf

# Create stub functions for now
def build_index():
    return {"status": "stub"}

class PolicyRetriever:
    def __init__(self, k=5):
        self.k = k
    def search(self, query, where=None):
        return []

def rerank(query, hits, top_n=5):
    return hits[:top_n]

def mask_pii(text):
    return text

def df_to_snowflake(df, table):
    return {"status": "stub"}

def snowflake_query(query):
    return pd.DataFrame()

def build_claim_packet_pdf(claim, cov, risk):
    return b"PDF stub"

# ---------- Integrations (guarded; provide stubs if import fails) ----------
try:
    from ..integrations.guidewire_adapter import (
        pc_get_policy,
        cc_create_fnol,
        cc_get_claim,
    )
except Exception:
    def pc_get_policy(q: PolicyQuery):
        return {"policy_id": getattr(q, "policy_id", None), "endorsements": []}
    def cc_create_fnol(model: ClaimFNOL):
        return {"status": "mocked"}
    def cc_get_claim(claim_id: str):
        return {"claim_id": claim_id, "status": "mocked"}

try:
    from ..integrations.duckcreek_adapter import (
        pas_list_endorsements,
        pas_get_policy,
    )
except Exception:
    def pas_list_endorsements(policy_id: str):
        return {"policy_id": policy_id, "endorsements": []}
    def pas_get_policy(q: PolicyQuery):
        return {"policy_id": getattr(q, "policy_id", None), "endorsements": []}

# ---------- App ----------
app = FastAPI(
    title="ClaimSight AI API",
    version="0.1.0",
    docs_url="/" if DOCS_AT_ROOT else "/docs",
    openapi_url="/openapi.json",
    root_path=ROOT_PATH,
)

# ========= Globals =========
RETRIEVER: PolicyRetriever | None = None
MODEL: xgb.XGBClassifier | None = None
EXPLAINER: shap.TreeExplainer | None = None
FEATURES = ["amount", "claimant_history_count", "fire", "water", "theft", "collision"]

# ========= Helpers =========
def _one_hot_loss(loss_type: str):
    loss_types = ["fire", "water", "theft", "collision"]
    lt = str(loss_type).lower()
    return [1 if lt == k else 0 for k in loss_types]

def fetch_endorsements(policy_id: str) -> list[dict]:
    """Prefer Duck Creek; fall back to Guidewire."""
    if not policy_id:
        return []
    try:
        dc = pas_list_endorsements(policy_id)
        endos = dc.get("endorsements", []) or []
        if endos:
            return endos
    except Exception:
        pass
    try:
        gw = pc_get_policy(PolicyQuery(policy_id=policy_id))
        return gw.get("endorsements", []) or []
    except Exception:
        return []

# ========= Startup =========
@app.on_event("startup")
def startup():
    """SIMPLIFIED STARTUP FOR DEBUGGING"""
    global RETRIEVER, MODEL, EXPLAINER
    
    print("=== API STARTUP BEGINNING ===")
    print(f"APP_HOME: {APP_HOME}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"MODELS_DIR: {MODELS_DIR}")
    print(f"IS_CODESPACES: {IS_CODESPACES}")
    print(f"DOCS_AT_ROOT: {DOCS_AT_ROOT}")
    
    # Temporarily comment out everything complex
    # try:
    #     out = build_index()
    #     print("Policy index build:", out)
    # except Exception as e:
    #     print("Index build error (continuing):", e)

    # RETRIEVER = PolicyRetriever(k=5)

    # model_path = MODELS_DIR / "risk_xgb.json"
    # if model_path.exists():
    #     mdl = xgb.XGBClassifier()
    #     mdl.load_model(str(model_path))
    #     MODEL = mdl
    #     bg = pd.DataFrame([[1000, 0, 0, 1, 0, 0]], columns=FEATURES)
    #     EXPLAINER = shap.TreeExplainer(MODEL, bg)
    #     print("Loaded XGB risk model.")
    # else:
    #     print("Risk model not found. Train via POST /admin/train_risk")
    
    print("=== API STARTUP COMPLETE - BASIC MODE ===")

# ========= Health =========
@app.get("/healthz")
def health_check():
    return {"status": "ok"}

# If docs are NOT at root, expose "/" as a redirect to /docs
if not DOCS_AT_ROOT:
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs", status_code=307)

# ========= RAG search =========
@app.get("/rag/search")
def rag_search(q: str, policy_id: str | None = None):
    if RETRIEVER is None:
        raise HTTPException(status_code=503, detail="Retriever not initialized")
    where = {"policy_id": policy_id} if policy_id else None
    hits = RETRIEVER.search(q, where=where)
    hits = rerank(q, hits, top_n=5)
    return {"query": q, "results": hits}

# ========= Coverage =========
@app.post("/claims/coverage")
def coverage_check(claim: dict):
    if RETRIEVER is None:
        raise HTTPException(status_code=503, detail="Retriever not initialized")

    loss_type = str(claim.get("loss_type", "")).lower()
    notes = claim.get("notes", "") or ""
    policy_id = claim.get("policy_id")

    q = f"Loss type: {loss_type}. Is it covered? Notes: {notes}"
    where = {"policy_id": policy_id} if policy_id else None
    hits = RETRIEVER.search(q, where=where)
    hits = rerank(q, hits, top_n=5)

    endorsements = fetch_endorsements(policy_id) if policy_id else []
    has_water_backup = any(
        (e.get("code", "").upper() in {"WTR-BKP", "WATER-BACKUP", "WTRBKP"})
        or ("water backup" in (e.get("desc", "").lower()))
        for e in endorsements
    )

    covered = None
    reasons, cites = [], []
    for h in hits:
        t = (h["text"] or "").lower()
        cites.append(f'{h["meta"].get("policy_id","unknown")} – {h["meta"].get("section","unknown")}')

        if "water backup" in t and "excluded" in t and loss_type == "water":
            if has_water_backup:
                covered = "yes (endorsement)"; reasons.append("Water backup endorsement present.")
            else:
                covered = "no"; reasons.append("Water backup excluded unless endorsed.")
        if "endorsement" in t and "water backup" in t and loss_type == "water" and has_water_backup:
            covered = "yes (endorsement)"; reasons.append("Endorsement allows water backup with sublimits.")
        if any(k in t for k in ["fire", "lightning", "windstorm", "hail"]) and loss_type == "fire":
            covered = "yes"; reasons.append("Perils include fire/lightning/wind/hail.")
        if "flood" in t and "excluded" in t and ("flood" in notes or loss_type == "water"):
            covered = "no"; reasons.append("Flood is excluded by policy.")
        if "theft" in t and loss_type == "theft":
            covered = "yes"; reasons.append("Theft covered subject to limits.")

    if covered is None and has_water_backup and loss_type == "water":
        covered = "yes (endorsement)"; reasons.append("WTR-BKP endorsement found.")

    if not covered:
        covered = "unknown"; reasons.append("Insufficient evidence; manual review required.")

    return {
        "coverage": covered,
        "rationale": " ".join(dict.fromkeys(reasons)),
        "citations": list(dict.fromkeys(cites)),
        "endorsements": [{"code": e.get("code"), "desc": e.get("desc")} for e in endorsements],
        "retrieval_preview": hits[:2],
    }

# ========= Risk =========
@app.post("/claims/risk")
def risk_score(claim: dict):
    amount = float(claim.get("amount", 0))
    prior = int(claim.get("claimant_history_count", 0))
    loss = str(claim.get("loss_type", "")).lower()

    x = pd.DataFrame([[amount, prior] + _one_hot_loss(loss)], columns=FEATURES)

    if MODEL is None:
        score = min(0.99, 0.3 + (amount / 50000.0) + 0.1 * prior)
        reasons = []
        if prior > 2: reasons.append("High prior claim count")
        if amount > 20000: reasons.append("Amount exceeds peer median")
        return {"score": round(float(score), 3), "reasons": reasons, "top_features": ["amount","claimant_history_count"]}

    proba = float(MODEL.predict_proba(x)[0, 1])
    shap_vals = EXPLAINER.shap_values(x)[0]
    top_idx = np.argsort(-np.abs(shap_vals))[:3]
    reasons = [f"{FEATURES[i]} ({shap_vals[i]:+.3f})" for i in top_idx]
    return {"score": round(proba, 3), "reasons": reasons, "top_features": [FEATURES[i] for i in top_idx]}

# ========= OCR + PII =========
@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...), mask_pii_flag: bool = True):
    try:
        content = await file.read()
        text = ""
        if (file.content_type or "").startswith("image/"):
            try:
                from PIL import Image
                import io, pytesseract
                img = Image.open(io.BytesIO(content))
                text = pytesseract.image_to_string(img) or ""
            except Exception:
                text = ""
        if not text:
            text = f"Uploaded: {file.filename}"
        if mask_pii_flag:
            text = mask_pii(text)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========= Triage =========
@app.post("/triage/docs")
async def triage_docs(files: List[UploadFile]):
    out = []
    for f in files:
        masked = mask_pii(f.filename or "")
        out.append({"filename": f.filename, "doc_type": "invoice", "pii_masked_excerpt": masked})
    return out

# ========= Admin: train toy model =========
@app.post("/admin/train_risk")
def train_risk():
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(DATA_DIR / "claims.csv")
    df["fire"] = (df["loss_type"] == "fire").astype(int)
    df["water"] = (df["loss_type"] == "water").astype(int)
    df["theft"] = (df["loss_type"] == "theft").astype(int)
    df["collision"] = (df["loss_type"] == "collision").astype(int)

    X = df[FEATURES]; y = df["fraud_flag"].astype(int)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.08,
        subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0
    )
    model.fit(X_tr, y_tr)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODELS_DIR / "risk_xgb.json"))

    return {"status": "trained", "train_pos_rate": float(y_tr.mean()), "test_pos_rate": float(y_te.mean())}

train_risk_model = train_risk

# ========= Reports =========
@app.post("/reports/claim_packet")
def generate_claim_packet(claim: dict):
    cov = coverage_check(claim)
    risk = risk_score({
        "loss_type": claim.get("loss_type"),
        "amount": claim.get("amount", 0),
        "claimant_history_count": claim.get("claimant_history_count", 0),
    })
    pdf_bytes = build_claim_packet_pdf(claim, cov, risk)
    from fastapi.responses import Response
    filename = f"claimsight_case_packet_{claim.get('claim_id','N_A')}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})

# ========= Snowflake (optional) =========
@app.post("/integrations/snowflake/upload_claims")
def upload_claims_to_snowflake():
    try:
        df = pd.read_csv(DATA_DIR / "claims.csv")
        df_to_snowflake(df.head(100), table="CLAIMS_SAMPLE")
        return {"status": "uploaded", "rows": int(min(len(df), 100))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/integrations/snowflake/sample_query")
def snowflake_sample_query():
    try:
        df = snowflake_query('select * from "CLAIMS_SAMPLE" limit 5')
        return {"rows": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========= Adapters =========
@app.get("/adapters/guidewire/policy/{policy_id}")
def gw_policy(policy_id: str):
    return pc_get_policy(PolicyQuery(policy_id=policy_id))

@app.get("/adapters/guidewire/claim/{claim_id}")
def gw_claim(claim_id: str):
    return cc_get_claim(claim_id)

@app.post("/adapters/guidewire/fnol")
def gw_create_fnol(claim: dict):
    return cc_create_fnol(ClaimFNOL(**claim))

@app.get("/adapters/duckcreek/policy/{policy_id}")
def dc_policy(policy_id: str):
    return pas_get_policy(PolicyQuery(policy_id=policy_id))

@app.get("/adapters/duckcreek/policy/{policy_id}/endorsements")
def dc_endorsements(policy_id: str):
    return pas_list_endorsements(policy_id)

# after you create `app = FastAPI(...)`
app.include_router(fraud_router)
