from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class ClaimFNOL:
    claim_id: str
    policy_id: str
    loss_date: str
    loss_type: str
    amount: float
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    def to_dict(self): return asdict(self)

@dataclass
class PolicyQuery:
    policy_id: str
    effective_date: Optional[str] = None
    fields: Optional[list[str]] = None
    def to_dict(self): return asdict(self)
