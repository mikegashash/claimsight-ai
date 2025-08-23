import pandas as pd

CATEGORICAL = ["line_of_business","state","injury_severity","police_report"]
NUMERIC = [
    "late_report_days","claim_amount","paid_to_date","reserve",
    "prior_claims_count","claimant_age","paid_ratio","reserve_ratio"
]

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    num_cast = ["claim_amount","paid_to_date","reserve","late_report_days",
                "prior_claims_count","claimant_age","police_report"]
    for col in num_cast:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    with pd.option_context("mode.use_inf_as_na", True):
        df["paid_ratio"] = (df.get("paid_to_date",0) / df.get("claim_amount",1)).fillna(0).clip(0,5)
        df["reserve_ratio"] = (df.get("reserve",0) / df.get("claim_amount",1)).fillna(0).clip(0,5)

    for col in ["incident_date","report_date"]:
        if col in df.columns:
            d = pd.to_datetime(df[col], errors="coerce")
            df[f"{col}_dow"] = d.dt.dayofweek.fillna(-1)
            df[f"{col}_month"] = d.dt.month.fillna(0)
    return df
