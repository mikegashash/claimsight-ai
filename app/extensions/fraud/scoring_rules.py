from typing import Dict, Any

def score_rules(c: Dict[str, Any], rings: Dict[str, set]) -> Dict[str, Any]:
    risk = 0.0
    reasons = []

    late_days = int(c.get("late_report_days", 0) or 0)
    lob = (c.get("line_of_business") or "").strip()
    sev = (c.get("injury_severity") or "").strip()
    police = int(c.get("police_report", 0) or 0)
    amount = float(c.get("claim_amount", 0) or 0)
    prior = int(c.get("prior_claims_count", 0) or 0)
    provider = (c.get("provider_id") or "").strip()
    shop = (c.get("repair_shop_id") or "").strip()

    if late_days > 30:
        risk += 0.25; reasons.append("late_report")
    if lob == "Auto" and amount > 4900 and sev in ("None","Minor") and police == 0:
        risk += 0.30; reasons.append("amount_vs_severity_no_police")
    if provider in rings["ring_providers"] or shop in rings["ring_shops"]:
        risk += 0.35; reasons.append("ring_link")
    if prior >= 3:
        risk += 0.20; reasons.append("frequent_prior_claims")
    if lob == "Home" and amount > 30000 and police == 0:
        risk += 0.25; reasons.append("home_inflated_no_police")

    risk = min(1.0, risk)
    label = 1 if risk >= 0.5 else 0
    return {"fraud_probability": risk, "label": label, "reasons": reasons}
