from fastapi import FastAPI, UploadFile
from typing import List

app = FastAPI(title="ClaimSight AI API")

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/claims/coverage")
def coverage_check(claim: dict):
    # TODO: integrate RAG
    return {
        "coverage": "yes",
        "rationale": "Loss type covered per policy section 3.1",
        "citations": ["Section 3.1"]
    }

@app.post("/claims/risk")
def risk_score(claim: dict):
    # TODO: integrate ML model
    return {
        "score": 0.83,
        "reasons": ["High prior claim count", "Amount exceeds peer median"],
        "top_features": ["prior_claim_count", "loss_amount"]
    }

@app.post("/triage/docs")
async def triage_docs(files: List[UploadFile]):
    # TODO: integrate OCR + classification
    return [{"filename": f.filename, "doc_type": "invoice"} for f in files]
