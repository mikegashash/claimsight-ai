import os
from typing import Dict, Any
from .models import ClaimFNOL, PolicyQuery

GW_BASE = os.getenv("GW_BASE_URL", "https://guidewire.example.com")
GW_API_KEY = os.getenv("GW_API_KEY", "dev-key")

def pc_get_policy(q: PolicyQuery) -> Dict[str, Any]:
    # Stubbed response for demos/tests
    return {
        "policyId": q.policy_id,
        "effectiveDate": q.effective_date or "2024-01-01",
        "status": "InForce",
        "endorsements": [{"code": "WTR-BKP", "desc": "Water backup up to 10k"}],
        "limits": {"CovA": 300000, "CovC": 50000},
    }

def cc_create_fnol(c: ClaimFNOL) -> Dict[str, Any]:
    return {"created": True, "claimNumber": c.claim_id, "status": "Open", "routingQueue": "InitialReview"}

def cc_get_claim(claim_id: str) -> Dict[str, Any]:
    return {"claimNumber": claim_id, "status": "Open", "lossType": "water", "amount": 12000, "policyRef": "P1001"}
