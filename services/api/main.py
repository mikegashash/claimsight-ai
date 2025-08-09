from fastapi import FastAPI, UploadFile
from typing import List
import os, json, math



from rag.reranker import rerank

from integrations.models import PolicyQuery, ClaimFNOL
from integrations.guidewire_adapter import pc_get_policy, cc_create_fnol, cc_get_claim
from integrations.duckcreek_adapter import pas_get_policy, pas_list_endorsements

import sys, os as _os
sys.path.append(_os.path.abspath("/app/services"))

from ocr.pii import mask_pii

from fastapi import HTTPException
from snowflake_io import df_to_snowflake, snowflake_query

@app.post("/integrations/snowflake/upload_claims")
def upload_claims_to_snowflake():
    try:
        df = pd.read_csv("/app/data/claims.csv")
        df_to_snowflake(df.head(100), table="CLAIMS_SAMPLE")
        return {"status": "uploaded", "rows": int(min(len(df),100))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/integrations/snowflake/sample_query")
def snowflake_sample_query():
    try:
        df = snowflake_query('select * from "CLAIMS_SAMPLE" limit 5')
        return {"rows": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- RAG imports ---
from rag.index_policies import build_index
from rag.retriever import PolicyRetriever

# --- Risk model imports ---
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import joblib

import sys, os as _os
sys.path.append(_os.path.abspath("/app/services"))


app = FastAPI(title="ClaimSight AI API")

RETRIEVER = None
MODEL = None
FEATURES = ["amount","claimant_history_count","fire","water","theft","collision"]
EXPLAINER = None

def _one_hot_loss(loss_type: str):
    loss_types = ["fire","water","theft","collision"]
    return [1 if loss_type == lt else 0 for lt in loss_types]

@app.on_event("startup")
def startup():
    # Build RAG index if empty / start fresh
    try:
        out = build_index()
        print("Policy index built:", out)
    except Exception as e:
        print("Index build error (continuing):", e)
    global RETRIEVER
    RETRIEVER = PolicyRetriever(k=5)

    # Load risk model if exists
    global MODEL, EXPLAINER
    model_path = "/app/models/risk_xgb.json"
    if os.path.exists(model_path):
        MODEL = xgb.XGBClassifier()
        MODEL.load_model(model_path)
        # Dummy background for SHAP TreeExplainer
        bg = pd.DataFrame([[1000,0,0,1,0,0]], columns=FEATURES)
        EXPLAINER = shap.TreeExplainer(MODEL, bg)
        print("Loaded XGB risk model.")
    else:
        print("Risk model not found. Train via /admin/train_risk")

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/claims/coverage")
def coverage_check(claim: dict):
    """
    Simple RAG-driven heuristic:
    - Build a query from claim facts (loss_type, notes)
    - Retrieve top-k sections
    - Apply tiny rules to infer coverage (demo)
    """
    loss_type = claim.get("loss_type","").lower()
    notes = claim.get("notes","")
    policy_id = claim.get("policy_id")

    q = f"Loss type: {loss_type}. Question: is it covered? Notes: {notes}"
    where = {"policy_id": policy_id} if policy_id else None
    hits = RETRIEVER.search(q, where=where)

    # tiny heuristic demo with citations
    covered = None
    reasons = []
    cites = []

    for h in hits:
        t = (h["text"] or "").lower()
        sec = h["meta"].get("section","unknown")
        # collect citations
        cites.append(f'{h["meta"].get("policy_id","unknown")} – {sec}')

        if "water backup" in t and "excluded" in t and loss_type == "water":
            covered = "no"
            reasons.append("Policy states water backup excluded unless endorsed.")
        if "endorsement" in t and "water backup" in t and loss_type == "water":
            covered = "yes (endorsement)"
            reasons.append("Water backup endorsement applies with sublimits.")
        if any(k in t for k in ["fire", "lightning", "windstorm", "hail"]) and loss_type == "fire":
            covered = "yes"
            reasons.append("Perils insured against include fire.")

        if "flood" in t and "excluded" in t and ("flood" in notes or loss_type=="water"):
            covered = "no"
            reasons.append("Flood is excluded.")

        if "theft" in t and loss_type == "theft":
            covered = "yes"
            reasons.append("Theft covered subject to limits.")

    # fallback if nothing definitive
    if not covered:
        covered = "unknown"
        reasons.append("Insufficient evidence; manual review required.")

    return {
        "coverage": covered,
        "rationale": " ".join(dict.fromkeys(reasons)),
        "citations": list(dict.fromkeys(cites)),
        "retrieval_preview": hits[:2] # helpful for demo
    }

@app.post("/claims/risk")
def risk_score(claim: dict):
    """
    Toy XGBoost model with SHAP explanations.
    If model missing, returns heuristic score.
    """
    amount = float(claim.get("amount", 0))
    prior = int(claim.get("claimant_history_count", 0))
    loss_type = str(claim.get("loss_type","")).lower()
    one_hot = _one_hot_loss(loss_type)
    x = pd.DataFrame([[amount, prior] + one_hot], columns=FEATURES)

    if MODEL is None:
        # heuristic fallback
        score = min(0.99, 0.3 + (amount/50000.0) + 0.1*prior)
        reasons = []
        if prior > 2: reasons.append("High prior claim count")
        if amount > 20000: reasons.append("Amount exceeds peer median")
        return {"score": round(float(score), 3), "reasons": reasons, "top_features": ["amount","claimant_history_count"]}
    else:
        proba = float(MODEL.predict_proba(x)[0,1])
        shap_vals = EXPLAINER.shap_values(x)[0]
        # top features
        top_idx = np.argsort(-np.abs(shap_vals))[:3]
        reasons = [f"{FEATURES[i]} ({shap_vals[i]:+.3f})" for i in top_idx]
        return {"score": round(proba,3), "reasons": reasons, "top_features": [FEATURES[i] for i in top_idx]}

@app.post("/triage/docs")
async def triage_docs(files: List[UploadFile]):
    return [{"filename": f.filename, "doc_type": "invoice"} for f in files]

# Simple admin endpoint to train a toy model on synthetic data
@app.post("/admin/train_risk")
def train_risk():
    import os
    from sklearn.model_selection import train_test_split
    df = pd.read_csv("/app/data/claims.csv")
    # Create toy features
    df["fire"] = (df["loss_type"]=="fire").astype(int)
    df["water"] = (df["loss_type"]=="water").astype(int)
    df["theft"] = (df["loss_type"]=="theft").astype(int)
    df["collision"] = (df["loss_type"]=="collision").astype(int)
    X = df[["amount","claimant_history_count","fire","water","theft","collision"]]
    y = df["fraud_flag"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9, reg_lambda=1.0
    )
    model.fit(X_train, y_train)

    os.makedirs("/app/models", exist_ok=True)
    model.save_model("/app/models/risk_xgb.json")
    # Prime explainer background next startup
    return {"status":"trained", "train_pos_rate": float(y_train.mean()), "test_pos_rate": float(y_test.mean())}
