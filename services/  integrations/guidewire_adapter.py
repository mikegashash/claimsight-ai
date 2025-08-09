"""
Guidewire REST adapter stubs (ClaimCenter/PolicyCenter).
Replace base URLs and auth implementation with your environment.
"""

import os, time
from typing import Dict, Any, Optional
import requests
from .models import ClaimFNOL, PolicyQuery

GW_BASE = os.getenv("GW_BASE_URL", "https://guidewire.example.com")
GW_API_KEY = os.getenv("GW_API_KEY", "dev-key")

def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {GW_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

# --- PolicyCenter ---
def pc_get_policy(q: PolicyQuery) -> Dict[str, Any]:
    """Fetch policy summary/details (stubbed to demo shape)."""
    # In real life: GET {GW_BASE}/policycenter/policies/{q.policy_id}?fields=...
    # Here we return a mock for demo / unit tests:
    return {
        "policyId": q.policy_id,
        "effectiveDate": q.effective_date or "2024-01-01",
        "status": "InForce",
        "endorsements": [
            {"code": "WTR-BKP", "desc": "Water backup up to 10k"},
        ],
        "limits": {"CovA": 300000, "CovC": 50000},
    }

# --- ClaimCenter ---
def cc_create_fnol(c: ClaimFNOL) -> Dict[str, Any]:
    """Create FNOL record (ClaimCenter). Returns claim number."""
    # Real: POST {GW_BASE}/claimcenter/claims
    # resp = requests.post(url, headers=_headers(), json=c.to_dict()); resp.raise_for_status()
    # return resp.json()
    return {
        "created": True,
        "claimNumber": c.claim_id,
        "status": "Open",
        "routingQueue": "InitialReview",
    }

def cc_get_claim(claim_id: str) -> Dict[str, Any]:
    """Fetch a claim record by ID (stub)."""
    return {
        "claimNumber": claim_id,
        "status": "Open",
        "lossType": "water",
        "amount": 12000,
        "insured": {"name": "Jane Doe"},
        "policyRef": "P1001",
    }
