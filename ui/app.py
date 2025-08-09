# ui/app.py
import json
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ClaimSight AI", layout="wide")
st.title("🧠 ClaimSight AI — Demo UI")

API_URL_DEFAULT = "http://api:8000"

with st.sidebar:
    st.markdown("### Settings")
    api_url = st.text_input("API base URL", API_URL_DEFAULT)
    st.caption("Tip: inside Docker Compose, API is http://api:8000")

tab_cov, tab_risk, tab_triage = st.tabs(["Coverage Check", "Risk Score", "Document Triage"])

# -----------------------
# Coverage
# -----------------------
with tab_cov:
    st.subheader("Policy Coverage Determination (RAG + Endorsements)")

    # Quick form
    with st.form("coverage_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            claim_id = st.text_input("Claim ID", "C00001")
            policy_id = st.text_input("Policy ID", "P1001")
            loss_type = st.selectbox("Loss Type", ["water", "fire", "theft", "collision"])
            amount = st.number_input("Claim Amount", min_value=0.0, value=2500.0, step=100.0)
        with c2:
            zip_code = st.text_input("ZIP", "44114")
            prior = st.number_input("Prior Claims (count)", min_value=0, value=1, step=1)
            notes = st.text_area("Notes", "Water backup in basement; sump failure during storm.")
        submitted = st.form_submit_button("Run Coverage Check", type="primary")

    # JSON payload editor (advanced)
    with st.expander("Advanced: Edit raw JSON payload"):
        payload = {
            "claim_id": claim_id,
            "policy_id": policy_id,
            "loss_type": loss_type,
            "amount": amount,
            "zip": zip_code,
            "claimant_history_count": prior,
            "notes": notes,
        }
        payload_str = st.text_area("Payload (JSON)", json.dumps(payload, indent=2), height=200)
        try:
            payload = json.loads(payload_str or "{}")
        except Exception:
            st.warning("Invalid JSON in payload editor; using form values.")

    if submitted:
        try:
            r = requests.post(f"{api_url}/claims/coverage", json=payload, timeout=30)
            r.raise_for_status()
            res = r.json()

            # Top-line result
            st.success(f"Coverage decision: **{res.get('coverage','n/a')}**")
            if res.get("rationale"):
                st.write("**Rationale**")
                st.write(res["rationale"])

            # Endorsements
            endos = res.get("endorsements") or []
            st.write("**Endorsements (from PAS/PC)**")
            if endos:
                df_endos = pd.DataFrame(endos)
                st.dataframe(df_endos, use_container_width=True)
            else:
                st.caption("No endorsements returned or none applicable.")

            # Citations
            cites = res.get("citations") or []
            st.write("**Policy Citations**")
            if cites:
                st.code("\n".join(cites))
            else:
                st.caption("No citations returned.")

            # Retrieval preview
            prev = res.get("retrieval_preview") or []
            if prev:
                st.write("**Top Retrieval Snippets**")
                for i, h in enumerate(prev, 1):
                    with st.expander(f"Hit {i} — {h.get('meta',{}).get('section','unknown')}"):
                        st.write(h.get("text","").strip() or "(empty)")
                        st.caption(f"distance={h.get('distance')}, meta={h.get('meta')}")

            # Raw response
            with st.expander("Raw Response"):
                st.json(res)

        except Exception as e:
            st.error(f"Coverage request failed: {e}")

# -----------------------
# Risk
# -----------------------
with tab_risk:
    st.subheader("Fraud / Risk Score (XGBoost + SHAP)")
    c1, c2, c3 = st.columns(3)
    with c1:
        loss_type_r = st.selectbox("Loss Type", ["water", "fire", "theft", "collision"], key="lt_r")
        amount_r = st.number_input("Claim Amount", min_value=0.0, value=7500.0, step=100.0, key="amt_r")
    with c2:
        prior_r = st.number_input("Prior Claims Count", min_value=0, value=0, step=1, key="prior_r")
        days_since = st.number_input("Days Since Policy Inception", min_value=0, value=120, step=10)
    with c3:
        provider_id = st.text_input("Provider ID", "PR321")
        zip_r = st.text_input("ZIP", "10001")

    if st.button("Get Risk Score", type="primary"):
        risk_payload = {
            "loss_type": loss_type_r,
            "amount": amount_r,
            "claimant_history_count": prior_r,
            "days_since_policy_start": days_since,
            "provider_id": provider_id,
            "zip": zip_r,
        }
        try:
            rr = requests.post(f"{api_url}/claims/risk", json=risk_payload, timeout=20)
            rr.raise_for_status()
            res = rr.json()
            st.metric("Risk Score", f"{res.get('score', 0):.2f}")
            st.write("**Top Reasons**")
            st.write("- " + "\n- ".join(res.get("reasons", [])) if res.get("reasons") else "n/a")
            st.write("**Top Features**")
            st.code(", ".join(res.get("top_features", [])) or "n/a")
            with st.expander("Raw Response"):
                st.json(res)
        except Exception as e:
            st.error(f"Risk request failed: {e}")

# -----------------------
# Triage
# -----------------------
with tab_triage:
    st.subheader("Document Triage (PII masking demo)")
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
                st.dataframe(df, use_container_width=True)
                with st.expander("Raw Response"):
                    st.json(res)
            except Exception as e:
                st.error(f"Request failed: {e}")
