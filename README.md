# ClaimSight AI — Open Source Claims Intelligence Platform

**ClaimSight AI** is an open-source, end-to-end insurance claims intelligence platform that combines:
- **RAG-powered policy reasoning** for accurate coverage determinations with citations
- **ML-based fraud/risk scoring** with explainable outputs
- **Document triage** for high-volume claims processing
- **Streamlit UI** for rapid demo and testing

Built for enterprise-scale claims workflows (Guidewire, Duck Creek, custom systems) with a **privacy-first, auditable, and modular architecture**.

---

## Features
- **Coverage Determination** – Answers coverage questions with policy section citations using Retrieval-Augmented Generation (RAG).
- **Fraud/Risk Scoring** – Tabular ML model + rules for fast, explainable risk assessment.
- **Explainable AI** – SHAP plots and human-readable reasons for every score.
- **Document Triage** – Auto-classify PDFs (e.g., invoices, police reports) and extract structured fields.
- **Synthetic Data** – 100% privacy-safe, production-like datasets for demo and testing.

---

## Tech Stack
**Core:** Python, FastAPI, Streamlit, FAISS/Chroma, Pandas, NumPy, scikit-learn, XGBoost, PyTorch  
**OCR/PII:** Tesseract, Presidio  
**MLOps:** MLflow, Docker Compose, GitHub Actions  
**Storage:** Postgres, MinIO (S3-compatible), Vector DB  
**Integration Ready:** Snowflake connector, Kafka stubs

---

## 📂 Repo Structure
