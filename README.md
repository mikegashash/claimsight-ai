# ClaimSight AI — Open-Source Claims Intelligence Platform

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Dockerized](https://img.shields.io/badge/docker-ready-informational)
![Status](https://img.shields.io/badge/status-MVP--demo-brightgreen)
![CI](https://github.com/mikegashash/claimsight-ai/actions/workflows/ci.yml/badge.svg?branch=main&event=push)
![Bootstrap CI](https://github.com/mikegashash/claimsight-ai/actions/workflows/bootstrap.yml/badge.svg?branch=main&event=push)



**ClaimSight AI** is an end-to-end claims intelligence platform for insurance:
- **RAG-powered policy reasoning** with citations (vector search + **cross-encoder reranker**)
- **Fraud/risk scoring** (XGBoost) with **SHAP** explanations
- **Document triage** with **Presidio PII masking**
- **Streamlit UI** + **FastAPI** + **Docker Compose**
- **Snowflake connector** for enterprise data integration

> Privacy-first: synthetic sample data included; PII masking is built-in.

## Developer Experience (Makefile)

- **make up       # build, seed data, start stack
- **make test     # run pytest inside API container
- **make train    # train toy XGBoost model via admin API
- **make logs     # tail logs
- **make down     # stop stack


## Architecture

```mermaid
flowchart LR
    subgraph UI["Streamlit UI"]
      U1[Upload Claim & Docs]
      U2[Coverage Q&A]
      U3[Risk Score + SHAP]
    end

    subgraph API["FastAPI"]
      A1[/POST /claims/coverage/]
      A2[/POST /claims/risk/]
      A3[/POST /triage/docs/]
      A4[/GET /integrations/snowflake/*/]
    end

    subgraph RAG["RAG Service"]
      R1[Chunk + Embed Policies]
      R2[FAISS/Chroma Vector DB]
      R3[Cross-Encoder Reranker]
    end

    subgraph ML["Risk Model"]
      M1[Feature Build]
      M2[XGBoost Classifier]
      M3[SHAP Explainer]
    end

    subgraph Data["Storage"]
      D1[(Postgres metadata)]
      D2[(MinIO/S3 - docs)]
      D3[(Vector store)]
      D4[(models/)]
      D5[(data/claims.csv)]
    end

    subgraph Integrations["Enterprise Integrations"]
      S1[(Snowflake)]
    end

    UI -->|REST| API
    A1 --> RAG
    RAG --> A1
    A2 --> ML
    ML --> A2
    A3 -->|OCR + PII| D2
    API --> D1
    API --> D3
    API --> D4
    API --> D5
    API --> S1
```
###  Core System Integrations (stubs)

| Endpoint                                                | Description                                 |
|---------------------------------------------------------|---------------------------------------------|
| `/adapters/guidewire/policy/{policy_id}`                | Guidewire **PolicyCenter** policy summary   |
| `/adapters/guidewire/claim/{claim_id}`                  | Guidewire **ClaimCenter** claim details     |
| `/adapters/guidewire/fnol` (POST)                       | Create FNOL payload stub                    |
| `/adapters/duckcreek/policy/{policy_id}`                | Duck Creek PAS policy summary               |
| `/adapters/duckcreek/policy/{policy_id}/endorsements`   | Duck Creek endorsements list                |

> These are safe **stubs** for demos/unit tests. Replace base URLs/auth to connect to real environments via REST/SOAP.

**Coverage logic (demo):**  
The `/claims/coverage` endpoint blends **RAG** (policy text with citations) and **core systems data** (Duck Creek / Guidewire endorsements).  
- If `loss_type=water` and **WTR-BKP** (or equivalent) is present, result is **yes (endorsement)**.  
- Otherwise, water backup is **excluded** per policy text.  
- Fire / theft follow “perils insured against” language.  
- All responses include **citations** and, when applicable, **endorsement codes**.



