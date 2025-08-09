# services/api/main.py

import sys, os as _os
sys.path.append(_os.path.abspath("/app/services"))  # allow 'services.*' imports when running in container

from fastapi import FastAPI, UploadFile, HTTPException
from typing import List
import os
import pandas as pd
import numpy as np

# ---- RAG (FAISS) ----
from rag.index_policies import build_index
from rag.retriever import PolicyRetriever
from rag.reranker import rerank

# ---- OCR / PII ----
from ocr.pii import mask_pii

# ---- Snowflake ----
from snowflake_io import df_to_snowflake, snowflake_query

# ---- Integrations (Guidewire / Duck Creek) ----
from integrations.models import PolicyQuery, ClaimFNOL
from integrations.guidewire_adapter import pc_get_policy, cc_create_fnol, cc_get_claim
from integrations.duckcreek_adapter import pas_list_endorsements, pas_get_policy

# ---- Risk Model (XGBoost + SHAP) ----
import xgboost as xgb
import shap

from report import build_claim_packet_pdf


app = FastAPI(title="ClaimSight AI API")

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
    """
    Prefer Duck Creek (PAS) endorsements; fall back to Guidewire PolicyCenter.
    Returns list like: [{"code": "WTR-BKP", "desc": "Water backup 10k"}, ...]
    """
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
        endos = gw.get("endorsements", []) or []
        return endos
    except Exception:
        pass
    return []


# ========= Startup =========
@app.on_event("startup")
def startup():
    """Build vector index (idempotent) and load risk model (if present)."""
    global RETRIEVER, MODEL, EXPLAINER

    # Build policy index so RAG has content (safe if already exists)
    try:
        out = build_index()
        print("Policy index build:", out)
    except Exception as e:
        print("Index build error (continuing):", e)

    RETRIEVER = PolicyRetriever(k=5)

    # Load risk model if exists
    model_path = "/app/models/risk_xgb.json"
    if os.path.exists(model_path):
        mdl = xgb.XGBClassifier()
        mdl.load_model(model_path)
        MODEL = mdl
        # Background for SHAP
        bg = pd.DataFrame([[1000, 0, 0, 1, 0, 0]], columns=FEATURES)
        EXPLAINER = shap.TreeExplainer(MODEL, bg)
        print("Loaded XGB risk model.")
    else:
        print("Risk model not found. Train via POST /admin/train_risk")


# ========= Health =========
@app.get("/healthz")
def health_check():
    return {"status": "ok"}


# ========= Coverage (RAG + Endorsements) =========
@app.post("/claims/coverage")
def coverage_check(claim: dict):
    """
    Coverage determination = RAG (policy text + reranker) + PAS/PC endorsements.
    - If loss_type=water & endorsement (WTR-BKP / “water backup”) present -> yes (endorsement).
    - Else follow policy exclusions/perils from retrieved sections.
    Returns rationale + citations + endorsements used.
    """
    if RETRIEVER is None:
        raise HTTPException(status_code=503, detail="Retriever not initialized")

    loss_type = str(claim.get("loss_type", "")).lower()
    notes = claim.get("notes", "") or ""
    policy_id = claim.get("policy_id")

    # 1) RAG retrieve + rerank
    q = f"Loss type: {loss_type}. Is it covered? Notes: {notes}"
    where = {"policy_id": policy_id} if policy_id else None
    hits = RETRIEVER.search(q, where=where)
    hits = rerank(q, hits, top_n=5)

    # 2) Endorsements
    endorsements = fetch_endorsements(policy_id) if policy_id else []
    has_water_backup = any(
        (e.get("code", "").upper() in {"WTR-BKP", "WATER-BACKUP", "WTRBKP"}) or
        ("water backup" in (e.get("desc", "").lower()))
        for e in endorsements
    )

    # 3) Fusion logic
    covered = None
    reasons, cites = [], []

    for h in hits:
        t = (h["text"] or "").lower()
        cites.append(f'{h["meta"].get("policy_id","unknown")} – {h["meta"].get("section","unknown")}')

        # Water
        if "water backup" in t and "excluded" in t and loss_type == "water":
            if has_water_backup:
                covered = "yes (endorsement)"
                reasons.append("Water backup endorsement present in PAS/PC.")
            else:
                covered = "no"
                reasons.append("Policy excludes water backup unless endorsed.")
        if "endorsement" in t and "water backup" in t and loss_type == "water" and has_water_backup:
            covered = "yes (endorsement)"
            reasons.append("Policy text + endorsement allow water backup with sublimits.")

        # Fire
        if any(k in t for k in ["fire", "lightning", "windstorm", "hail"]) and loss_type == "fire":
            covered = "yes"
            reasons.append("Perils insured against include fire/lightning/wind/hail.")

        # Flood exclusion
        if "flood" in t and "excluded" in t and ("flood" in notes or loss_type == "water"):
            covered = "no"
            reasons.append("Flood is excluded by policy.")

        # Theft
        if "theft" in t and loss_type == "theft":
            covered = "yes"
            reasons.append("Theft covered subject to limits/exclusions.")

    if covered is None and has_water_backup and loss_type == "water":
        covered = "yes (endorsement)"
        reasons.append("Endorsement WTR-BKP (or equivalent) found in PAS/PC.")

    if not covered:
        covered = "unknown"
        reasons.append("Insufficient evidence; manual review required.")

    unique_reasons = list(dict.fromkeys(reasons))
    unique_cites = list(dict.fromkeys(cites))
    endo_short = [{"code": e.get("code"), "desc": e.get("desc")} for e in endorsements] if endorsements else []

    return {
        "coverage": covered,
        "rationale": " ".join(unique_reasons),
        "citations": unique_cites,
        "endorsements": endo_short,
        "retrieval_preview": hits[:2],
    }


# ========= Risk (XGBoost + SHAP or heuristic) =========
@app.post("/claims/risk")
def risk_score(claim: dict):
    """
    Returns risk score from toy XGBoost model if trained; else heuristic fallback.
    Also returns top SHAP features when model is present.
    """
    amount = float(claim.get("amount", 0))
    prior = int(claim.get("claimant_history_count", 0))
    loss = str(claim.get("loss_type", "")).lower()

    x = pd.DataFrame([[amount, prior] + _one_hot_loss(loss)], columns=FEATURES)

    if MODEL is None:
        score = min(0.99, 0.3 + (amount / 50000.0) + 0.1 * prior)
        reasons = []
        if prior > 2:
            reasons.append("High prior claim count")
        if amount > 20000:
            reasons.append("Amount exceeds peer median")
        return {
            "score": round(float(score), 3),
            "reasons": reasons,
            "top_features": ["amount", "claimant_history_count"],
        }

    proba = float(MODEL.predict_proba(x)[0, 1])
    shap_vals = EXPLAINER.shap_values(x)[0]
    top_idx = np.argsort(-np.abs(shap_vals))[:3]
    reasons = [f"{FEATURES[i]} ({shap_vals[i]:+.3f})" for i in top_idx]

    return {
        "score": round(proba, 3),
        "reasons": reasons,
        "top_features": [FEATURES[i] for i in top_idx],
    }


# ========= Document Triage (PII mask demo) =========
@app.post("/triage/docs")
async def triage_docs(files: List[UploadFile]):
    """
    Demo: returns masked excerpt using filename text.
    (Extend with real OCR + Presidio masking on extracted text.)
    """
    out = []
    for f in files:
        fname = f.filename or ""
        masked = mask_pii(fname)
        out.append({"filename": f.filename, "doc_type": "invoice", "pii_masked_excerpt": masked})
    return out


# ========= Admin: train toy model =========
@app.post("/admin/train_risk")
def train_risk():
    """
    Train a toy XGBoost classifier on synthetic data/claims.csv.
    Saves to /app/models/risk_xgb.json (picked up on next startup).
    """
    from sklearn.model_selection import train_test_split

    df = pd.read_csv("/app/data/claims.csv")
    df["fire"] = (df["loss_type"] == "fire").astype(int)
    df["water"] = (df["loss_type"] == "water").astype(int)
    df["theft"] = (df["loss_type"] == "theft").astype(int)
    df["collision"] = (df["loss_type"] == "collision").astype(int)

    X = df[FEATURES]
    y = df["fraud_flag"].astype(int)

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0
    )
    model.fit(X_tr, y_tr)

    os.makedirs("/app/models", exist_ok=True)
    model.save_model("/app/models/risk_xgb.json")

    return {
        "status": "trained",
        "train_pos_rate": float(y_tr.mean()),
        "test_pos_rate": float(y_te.mean()),
    }


# ========= Snowflake Integrations (optional) =========
@app.post("/integrations/snowflake/upload_claims")
def upload_claims_to_snowflake():
    try:
        df = pd.read_csv("/app/data/claims.csv")
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


# ========= Guidewire / Duck Creek Adapter Endpoints =========
@app.get("/adapters/guidewire/policy/{policy_id}")
def gw_policy(policy_id: str):
    q = PolicyQuery(policy_id=policy_id)
    return pc_get_policy(q)


@app.get("/adapters/guidewire/claim/{claim_id}")
def gw_claim(claim_id: str):
    return cc_get_claim(claim_id)


@app.post("/adapters/guidewire/fnol")
def gw_create_fnol(claim: dict):
    model = ClaimFNOL(**claim)
    return cc_create_fnol(model)


@app.get("/adapters/duckcreek/policy/{policy_id}")
def dc_policy(policy_id: str):
    q = PolicyQuery(policy_id=policy_id)
    return pas_get_policy(q)


@app.get("/adapters/duckcreek/policy/{policy_id}/endorsements")
def dc_endorsements(policy_id: str):
    return pas_list_endorsements(policy_id)

@app.post("/reports/claim_packet")
def generate_claim_packet(claim: dict):
    """
    Generates a PDF 'case packet' by calling coverage + risk internally,
    then returns a PDF file (bytes) as application/pdf.
    """
    # 1) Call coverage & risk
    cov = coverage_check(claim)
    risk = risk_score({
        "loss_type": claim.get("loss_type"),
        "amount": claim.get("amount", 0),
        "claimant_history_count": claim.get("claimant_history_count", 0)
    })

    # 2) Build PDF
    pdf_bytes = build_claim_packet_pdf(claim, cov, risk)

    # 3) Return as binary response
    from fastapi.responses import Response
    filename = f"claimsight_case_packet_{claim.get('claim_id','N_A')}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})

