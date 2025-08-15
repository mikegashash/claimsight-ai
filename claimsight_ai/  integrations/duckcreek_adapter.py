import os
from typing import Dict, Any
from .models import PolicyQuery

DC_BASE = os.getenv("DC_BASE_URL", "https://duckcreek.example.com")
DC_API_KEY = os.getenv("DC_API_KEY", "dev-key")

def pas_get_policy(q: PolicyQuery) -> Dict[str, Any]:
    return {
        "policyNumber": q.policy_id,
        "status": "Active",
        "state": "OH",
        "coverages": [{"code": "CovA", "limit": 300000}, {"code": "CovC", "limit": 50000}],
        "endorsements": [{"code": "WTR-BKP", "desc": "Water backup endorsement 10k"}],
    }

def pas_list_endorsements(policy_id: str) -> Dict[str, Any]:
    return {"policyNumber": policy_id, "endorsements": [{"code": "WTR-BKP", "desc": "Water backup 10k"}]}
