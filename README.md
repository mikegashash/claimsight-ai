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
    U1["Upload docs"]
    U2["Ask coverage Qs"]
    U3["View risk + SHAP"]
    U4["Download report"]
  end

  subgraph API["FastAPI (uvicorn)"]
    A1["POST /ocr"]
    A2["POST /triage/docs"]
    A3["POST /claims/coverage"]
    A4["POST /claims/risk"]
    A5["POST /reports/claim_packet"]
    A6["GET /integrations/*"]
  end

  subgraph PII["PII (Presidio)"]
    P1["Detect entities"]
    P2["Mask / redact"]
  end

  subgraph RAG["RAG engine"]
    R1["Embed query"]
    R2["Vector search (Chroma)"]
    R3["Rerank (cross-encoder)"]
    R4["Compose answer + citations"]
  end

  subgraph MODELS["Models"]
    M1["XGBoost risk"]
    M2["Embedding model"]
    M3["Cross-encoder"]
  end

  subgraph STORES["Stores"]
    V["Chroma vectors"]
    PG["Postgres"]
    FS["models/, reports/"]
  end

  subgraph INT["Integrations"]
    GW["Guidewire"]
    SF["Snowflake"]
  end

  %% flows
  U1 --> A1 --> PII
  PII -->|clean text| A2 --> RAG
  U2 --> A3 --> RAG
  R1 --> R2 --> R3 --> R4
  RAG --- M2
  RAG --- M3
  R2 --- V

  RAG -->|passages + citations| A3
  A3 --> PG
  A4 --> M1
  M1 -->|score + SHAP| A4
  A5 --> FS
  A6 --> GW
  A6 --> SF

  A4 --- PG
  A5 --- PG


```
## Coverage Q&A (RAG with citations)
```mermaid
sequenceDiagram
    autonumber
    participant UI as Streamlit UI
    participant API as FastAPI
    participant GW as Guidewire Adapter
    participant RAG as RAG Orchestrator
    participant ENC as Embedder
    participant VDB as Chroma (vectors)
    participant RER as Cross-encoder
    participant PG as Postgres

    UI->>API: POST /claims/coverage {policy_id, question, context}
    alt policy_id present
        API->>GW: fetchPolicy(policy_id)
        GW-->>API: policy metadata
    end
    API->>RAG: buildQueries(question, policy_metadata)
    RAG->>ENC: embed(question)
    ENC-->>RAG: q_vector
    RAG->>VDB: search(q_vector, k)
    VDB-->>RAG: candidate passages
    RAG->>RER: rerank(candidates, question)
    RER-->>RAG: top passages (scored)
    RAG-->>API: answer + citations
    API->>PG: persist coverage_result (audit)
    API-->>UI: 200 {answer, citations, audit_id}
```

## OCR → PII Masking → Triage
```mermaid
sequenceDiagram
    autonumber
    participant UI as Streamlit UI
    participant API as FastAPI
    participant OCR as OCR Engine
    participant PII as Presidio (PII)
    participant TRI as Triage Classifier
    participant PG as Postgres

    UI->>API: POST /ocr (multipart/form-data)
    API->>OCR: extractText(file)
    OCR-->>API: raw_text
    API->>PII: analyze(raw_text)
    PII-->>API: entities
    API->>PII: anonymize(raw_text, entities)
    PII-->>API: masked_text
    API->>TRI: classify(masked_text)
    TRI-->>API: doc_type, confidence
    API->>PG: upsert {doc_meta, doc_type, pii_stats}
    API-->>UI: 200 {masked_text, doc_type, pii_summary}

```

## Coverage Q&A (RAG with citations)
```mermaid
sequenceDiagram
    autonumber
    participant UI as Streamlit UI
    participant API as FastAPI
    participant GW as Guidewire Adapter
    participant RAG as RAG Orchestrator
    participant ENC as Embedder
    participant VDB as Chroma (vectors)
    participant RER as Cross-encoder
    participant PG as Postgres

    UI->>API: POST /claims/coverage {policy_id, question, context}
    alt policy_id present
        API->>GW: fetchPolicy(policy_id)
        GW-->>API: policy metadata
    end
    API->>RAG: buildQueries(question, policy_metadata)
    RAG->>ENC: embed(question)
    ENC-->>RAG: q_vector
    RAG->>VDB: search(q_vector, k)
    VDB-->>RAG: candidate passages
    RAG->>RER: rerank(candidates, question)
    RER-->>RAG: top passages (scored)
    RAG-->>API: answer + citations
    API->>PG: persist coverage_result (audit)
    API-->>UI: 200 {answer, citations, audit_id}
```

## Risk scoring with SHAP
```mermaid
sequenceDiagram
    autonumber
    participant UI as Streamlit UI
    participant API as FastAPI
    participant FE as Feature Builder
    participant XGB as XGBoost Model
    participant SHAP as SHAP Explainer
    participant PG as Postgres

    UI->>API: POST /claims/risk {claim_json}
    API->>FE: buildFeatures(claim_json)
    FE-->>API: features
    API->>XGB: predict_proba(features)
    XGB-->>API: risk_score
    API->>SHAP: explain(features)
    SHAP-->>API: top_features (contribs)
    API->>PG: persist {risk_score, shap}
    API-->>UI: 200 {risk_score, explanation}

```

## Report generation (auditable packet)
```mermaid
sequenceDiagram
    autonumber
    participant UI as Streamlit UI
    participant API as FastAPI
    participant PG as Postgres
    participant FS as File Store (models/reports)
    participant SF as Snowflake (optional)

    UI->>API: POST /reports/claim_packet {claim_id}
    API->>PG: fetch claim, coverage_result, risk_result
    API->>FS: compose PDF/JSON bundle
    FS-->>API: report_path
    opt export to Snowflake
        API->>SF: upsert claim analytics
        SF-->>API: ack
    end
    API-->>UI: 200 {download_url, report_meta}

```

## CI Badge
```mermaid
sequenceDiagram
    autonumber
    participant Dev as You
    participant GH as GitHub
    participant CI as Actions Runner
    participant PyPI as Pip/Wheels

    Dev->>GH: push / PR (branch)
    GH->>CI: trigger ci.yml
    CI->>PyPI: pip install -e . + API deps
    CI->>CI: pytest -vv (small models)
    alt tests pass
        CI-->>GH: success ✔
        GH-->>Dev: green checks (merge allowed)
    else tests fail
        CI-->>GH: failure ✖
        GH-->>Dev: logs & red badge
    end

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




