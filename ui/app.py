import json
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ClaimSight AI", layout="wide")
st.title("🧠 ClaimSight AI — MVP Demo")

API_URL = st.secrets.get("API_URL", "http://api:8000")

with st.sidebar:
    st.markdown("### Settings")
    api_url = st.text_input("API base URL", API_URL)
    st.markdown("---")
    st.caption("Tip: API container is `http://api:8000` inside Docker Compose.")

tab_cov, tab_risk, tab_triage = st.tabs(["Coverage Check", "Risk Score", "Document Triage"])

with tab_cov:
    st.subheader("Policy Coverage Determination (RAG placeholder)")
    col1, col2 = st.columns(2)
    with col1:
        claim_id = st.text_input("Claim ID", "C00001")
        policy_id = st.text_input("Policy ID", "P1234")
        loss_type = st.selectbox("Loss Type", ["fire", "water", "theft", "collision"])
        amount = st.number_input("Claim Amount", min_value=0.0, value=2500.0, step=100.0)
    with col2:
        zip_code = st.text_input("ZIP", "44114")
        claimant_history_count = st.number_input("Prior Claims (count)", min_value=0, value=1, step=1)
        notes = st.text_area("Notes", "Water backup in basement; sump failure during storm.")

    if st.button("Run Coverage Check", type="primary"):
        payload = {
            "claim_id": claim_id,
            "policy_id": policy_id,
            "loss_type": loss_type,
            "amount": amount,
            "zip": zip_code,
            "claimant_history_count": claimant_history_count,
            "notes": notes
        }
        try:
            r = requests.post(f"{api_url}/claims/coverage", json=payload, timeout=20)
            r.raise_for_status()
            res = r.json()
            st.success(f"Coverage: {res.get('coverage','n/a')}")
            st.write("**Rationale**")
            st.write(res.get("rationale", ""))
            st.write("**Citations**")
            st.code("\n".join(res.get("citations", [])) or "None")
            st.write("**Raw Response**")
            st.json(res)
        except Exception as e:
            st.error(f"Request failed: {e}")

with tab_risk:
    st.subheader("Fraud/Risk Score (ML placeholder)")
    c1, c2, c3 = st.columns(3)
    with c1:
        loss_type_r = st.selectbox("Loss Type", ["fire", "water", "theft", "collision"], key="lt_r")
        amount_r = st.number_input("Claim Amount", min_value=0.0, value=7500.0, step=100.0, key="amt_r")
    with c2:
        prior_r = st.number_input("Prior Claims Count", min_value=0, value=0, step=1, key="prior_r")
        days_since = st.number_input("Days Since Policy Inception", min_value=0, value=120, step=10)
    with c3:
        provider_id = st.text_input("Provider ID", "PR321")
        zip_r = st.text_input("ZIP", "10001")

    if st.button("Get Risk Score", type="primary"):
        payload = {
            "loss_type": loss_type_r,
            "amount": amount_r,
            "claimant_history_count": prior_r,
            "days_since_policy_start": days_since,
            "provider_id": provider_id,
            "zip": zip_r
        }
        try:
            r = requests.post(f"{api_url}/claims/risk", json=payload, timeout=20)
            r.raise_for_status()
            res = r.json()
            st.metric("Risk Score", f"{res.get('score', 0):.2f}")
            st.write("**Top Reasons**")
            reasons = res.get("reasons", [])
            st.write("- " + "\n- ".join(reasons) if reasons else "n/a")
            st.write("**Top Features**")
            st.code(", ".join(res.get("top_features", [])) or "n/a")
            st.write("**Raw Response**")
            st.json(res)
        except Exception as e:
            st.error(f"Request failed: {e}")

with tab_triage:
    st.subheader("Document Triage (OCR/classification placeholder)")
    files = st.file_uploader("Upload PDFs/Images", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
    if st.button("Classify Documents"):
        if not files:
            st.warning("Please upload at least one document.")
        else:
            try:
                files_payload = [("files", (f.name, f.read(), f.type)) for f in files]
                r = requests.post(f"{api_url}/triage/docs", files=files_payload, timeout=60)
                r.raise_for_status()
                res = r.json()
                st.success("Classification Results")
                df = pd.DataFrame(res)
                st.dataframe(df)
                st.write("**Raw Response**")
                st.json(res)
            except Exception as e:
                st.error(f"Request failed: {e}")
