import streamlit as st
import requests
import pandas as pd
from io import StringIO

st.set_page_config(page_title="ClaimSight AI", layout="wide")

api_url = "http://localhost:8000"

st.title("💡 ClaimSight AI — Insurance Claims Intelligence")

tabs = st.tabs([
    "🏠 Home",
    "📄 OCR & PII Masking",
    "📜 Coverage Check",
    "📊 Risk Scoring",
    "📈 RAG Search",
])

# ---------------- HOME TAB ----------------
with tabs[0]:
    st.header("Welcome")
    st.write("""
        ClaimSight AI integrates **RAG search**, **document AI**, and **predictive analytics** 
        into a single, enterprise-grade insurance intelligence platform.
    """)

# ---------------- OCR TAB ----------------
with tabs[1]:
    st.header("Document OCR & PII Masking")
    uploaded_file = st.file_uploader("Upload a document image or PDF", type=["png", "jpg", "jpeg", "pdf"])
    if uploaded_file is not None:
        files = {"file": uploaded_file}
        mask_pii = st.checkbox("Mask PII", value=True)
        resp = requests.post(f"{api_url}/ocr", files=files, params={"mask_pii": mask_pii})
        if resp.status_code == 200:
            st.subheader("Extracted Text")
            st.text(resp.json().get("text", ""))
        else:
            st.error(f"OCR failed: {resp.text}")

# ---------------- COVERAGE CHECK TAB ----------------
with tabs[2]:
    st.header("Coverage Check")
    with st.form(key="coverage_form"):
        claim_id = st.text_input("Claim ID")
        policy_id = st.text_input("Policy ID")
        loss_type = st.selectbox("Loss Type", ["fire", "water", "theft", "wind", "liability"])
        amount = st.number_input("Claim Amount", min_value=0.0)
        zip_code = st.text_input("ZIP Code")
        notes = st.text_area("Notes / Description")
        claimant_history_count = st.number_input("Prior Claims (Claimant)", min_value=0, step=1)
        submitted = st.form_submit_button("Check Coverage")

    if submitted:
        payload = {
            "claim_id": claim_id,
            "policy_id": policy_id,
            "loss_type": loss_type,
            "amount": amount,
            "zip": zip_code,
            "notes": notes,
            "claimant_history_count": claimant_history_count
        }

        try:
            # Coverage API
            cov_resp = requests.post(f"{api_url}/claims/coverage", json=payload, timeout=60)
            cov_resp.raise_for_status()
            coverage_data = cov_resp.json()

            st.subheader("Coverage Decision")
            st.write(f"**Decision:** {coverage_data.get('coverage')}")
            st.write(f"**Rationale:** {coverage_data.get('rationale')}")

            if coverage_data.get("endorsements"):
                st.subheader("Endorsements")
                st.table(pd.DataFrame(coverage_data["endorsements"]))

            if coverage_data.get("citations"):
                st.subheader("Citations")
                for cite in coverage_data["citations"]:
                    st.write(f"- {cite}")

            # Risk API
            risk_resp = requests.post(f"{api_url}/claims/risk", json={
                "loss_type": loss_type,
                "amount": amount,
                "claimant_history_count": claimant_history_count
            }, timeout=60)
            risk_resp.raise_for_status()
            risk_data = risk_resp.json()

            st.subheader("Risk Score")
            st.write(f"**Score:** {risk_data.get('score')}")
            if "reasons" in risk_data:
                st.write("**Reasons:**")
                for r in risk_data["reasons"]:
                    st.write(f"- {r}")

            # --- NEW PDF DOWNLOAD FEATURE ---
            st.write("---")
            st.subheader("Case Packet")
            if st.button("Generate PDF Case Packet"):
                try:
                    pdf_resp = requests.post(f"{api_url}/reports/claim_packet", json=payload, timeout=60)
                    pdf_resp.raise_for_status()
                    st.download_button(
                        label="Download Case Packet PDF",
                        data=pdf_resp.content,
                        file_name=f"claimsight_case_packet_{claim_id or 'N_A'}.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"PDF generation failed: {e}")

        except Exception as e:
            st.error(f"Coverage or Risk request failed: {e}")

# ---------------- RISK SCORING TAB ----------------
with tabs[3]:
    st.header("Risk Scoring (Standalone)")
    with st.form(key="risk_form"):
        loss_type_risk = st.selectbox("Loss Type", ["fire", "water", "theft", "wind", "liability"])
        amount_risk = st.number_input("Claim Amount", min_value=0.0, key="risk_amount")
        claimant_hist_risk = st.number_input("Prior Claims (Claimant)", min_value=0, step=1, key="risk_hist")
        submitted_risk = st.form_submit_button("Get Risk Score")

    if submitted_risk:
        try:
            risk_resp = requests.post(f"{api_url}/claims/risk", json={
                "loss_type": loss_type_risk,
                "amount": amount_risk,
                "claimant_history_count": claimant_hist_risk
            })
            risk_resp.raise_for_status()
            st.json(risk_resp.json())
        except Exception as e:
            st.error(f"Risk request failed: {e}")

# ---------------- RAG SEARCH TAB ----------------
with tabs[4]:
    st.header("RAG Search")
    query = st.text_input("Enter a search query")
    if st.button("Search"):
        try:
            rag_resp = requests.get(f"{api_url}/rag/search", params={"q": query})
            rag_resp.raise_for_status()
            st.json(rag_resp.json())
        except Exception as e:
            st.error(f"RAG search failed: {e}")
