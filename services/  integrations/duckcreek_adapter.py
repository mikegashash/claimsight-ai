"""
Duck Creek Policy (PAS) adapter stubs.
Replace base URLs and auth with your environment or Duck Creek Anywhere APIs.
"""

import os
from typing import Dict, Any
import requests
from .models import PolicyQuery

DC_BASE = os.getenv("DC_BASE_URL", "https://duckcreek.example.com")
DC_API_KEY = os.getenv("DC_API_KEY", "dev-key")

def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {DC_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def pas_get_policy(q: PolicyQuery) -> Dict[str, Any]:
    """Fetch PAS policy and endorsements (stub)."""
    # Real: GET {DC_BASE}/policy/v1/policies/{q.policy_id}
    return {
        "policyNumber": q.policy_id,
        "status": "Active",
        "state": "OH",
        "coverages": [
            {"code": "CovA", "limit": 300000},
            {"code": "CovC", "limit": 50000},
        ],
        "endorsements": [
            {"code": "WTR-BKP", "desc": "Water backup endorsement 10k"},
        ],
    }

def pas_list_endorsements(policy_id: str) -> Dict[str, Any]:
    """List endorsements for a policy (stub)."""
    return {
        "policyNumber": policy_id,
        "endorsements": [{"code": "WTR-BKP", "desc": "Water backup 10k"}],
    }
