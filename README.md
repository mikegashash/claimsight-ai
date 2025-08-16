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
    U1[Upload docs]
    U2[Ask coverage Qs]
    U3[View risk + SHAP]
    U4[Download report]
  end

  subgraph API["FastAPI (uvicorn)"]
    A1[/POST /ocr/]
    A2[/POST /triage/docs/]
    A3[/POST /claims/coverage/]
    A4[/POST /claims/risk/]
    A5[/POST /reports/claim_packet/]
    A6[/GET /integrations/.../]
  end

  subgraph PII["PII Pipeline (Presidio)"]
    P1[Detect entities]
    P2[Mask/Redact]
  end

  subgraph RAG["RAG Engine"]
    R1[Embed query]
    R2[Vector search (Chroma)]
    R3[Rerank (cross-encoder)]
    R4[Compose answer + citations]
  end

  subgraph MODELS["Model Store"]
    M1[XGBoost risk model]
    M2[Embedding model]
    M3[Cross-encoder]
  end

  subgraph STORES["Stores"]
    V[(Chroma vectors)]
    PG[(Postgres)]
    FS[(models/, reports/, logs)]
  end

  subgraph INT["Integrations"]
    GW[Guidewire adapter]
    SF[Snowflake]
  end

  U1 --> A1 --> PII
  PII -->|clean text| A2 -->|typed docs| RAG
  U2 --> A3 --> RAG
  RAG -->|top passages + citations| A3
  A3 --> PG
  A4 --> M1
  M1 -->|score + SHAP| A4
  A5 --> FS
  A6 --> GW
  A6 --> SF

  RAG --- M2
  RAG --- M3
  R2 --- V
  A4 --- PG
  A5 --- PG

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




