from dataclasses import dataclass
from typing import Optional, Dict

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
