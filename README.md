# 🛡️ Operational Intelligence Platform (Sigint AI)

> **Autonomous Cross-Platform Telemetry Ingestion, Hybrid Correlation, and DAG Multi-Agent Incident Forensics.**

[![Backend API](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?style=flat&logo=postgresql)](https://www.postgresql.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg?style=flat&logo=mongodb)](https://www.mongodb.org)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.12-FF6600.svg?style=flat&logo=rabbitmq)](https://www.rabbitmq.com)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-Ready-2496ED.svg?style=flat&logo=docker)](https://www.docker.com)

---

## 📌 Executive Summary

Modern engineering organizations receive thousands of operational telemetry events daily across disparate channels (**Slack**, **GitHub**, **Jira**, **Gmail**, **Datadog**, **Sentry**). This causes severe signal noise, alert fatigue, and delayed Mean Time to Detect (MTTD).

The **Operational Intelligence Platform (Sigint AI)** is an enterprise signal processing engine that ingests, normalizes, and mathematically correlates cross-platform telemetry into unified **Investigation** containers, automatically running AI-driven root cause analyses without human intervention.

---

## ⚡ Key System Capabilities

- **🔄 5-Stage Asynchronous Ingestion Pipeline**:
  - `Ingestion`: Webhook receivers & pollers for Slack, GitHub, Jira, and Gmail.
  - `Normalization`: Converts platform-specific payloads into standard telemetry schemas.
  - `Classification`: LLM & heuristic classifier filtering routine chat noise from incident-worthy signals.
  - `Hybrid Correlation`: Combines temporal proximity, entity matching, and 1536-D semantic vector embeddings (`text-embedding-3-small`).
  - `Incident Routing`: Maps signals into active incident containers or standalone telemetry logs.

- **🤖 DAG Multi-Agent Forensics Engine**:
  - Executes a Directed Acyclic Graph (DAG) of specialized OpenAI LLM agents (`gpt-4o` & `gpt-4o-mini`):
    - `Triage Agent` ➔ `Technical RCA Agent` & `Business Impact / SLA Agent` ➔ `Remediation Agent`.
  - Streams real-time diagnostic progress via **Server-Sent Events (SSE)** (`/api/v1/investigations/{id}/diagnose/stream`).
  - Enforces strict **anti-hallucination post-processing**: generates executable `git revert <sha>` scripts *only* when code commits exist in evidence.

- **🗄️ Polyglot Persistence Architecture**:
  - **PostgreSQL**: Manages multi-tenant organizations, OAuth integration credentials, and relational `Investigations`.
  - **MongoDB**: Stores high-volume, unstructured `Evidence` telemetry streams with schema flexibility.

---

## ⚙️ Architecture Topology

```
   Incoming Events (Slack / GitHub / Jira / Gmail)
                         │
                         ▼
        ┌───────────────────────────────────┐
        │   FastAPI Webhook & Ingest API    │
        └────────────────┬──────────────────┘
                         │
                         ▼
        ┌───────────────────────────────────┐
        │    RabbitMQ Event Broker Queue    │
        └────────────────┬──────────────────┘
                         │
                         ▼
        ┌───────────────────────────────────┐
        │    Celery Telemetry Workers       │
        │ • Vector Embedding Generation     │
        │ • Multi-Phase Correlation Engine  │
        └───────┬───────────────────┬───────┘
                │                   │
                ▼                   ▼
     ┌──────────────────┐   ┌──────────────────┐
     │ PostgreSQL (Async│   │ MongoDB (Motor)  │
     │ Relational DB)   │   │ Telemetry Store  │
     └──────────────────┘   └──────────────────┘
                │
                ▼
        ┌───────────────────────────────────┐
        │   DAG Multi-Agent Diagnosis       │
        │ (Triage ➔ RCA ➔ SLA ➔ Fix)        │
        └───────────────────────────────────┘
```

---

## 🔌 Supported Platform Integrations

| Platform | Authentication | Webhook / Ingestion Method | Tracked Scope |
|---|---|---|---|
| **Slack** | OAuth 2.0 (Bot Token) | Event Subscriptions Webhook | Multi-channel (`tracked_channels[]`) |
| **GitHub** | OAuth 2.0 App | Repository Webhooks | Multi-repo (`tracked_repos[]`) |
| **Jira Cloud** | OAuth 2.0 (3LO) | Dynamic REST Webhooks | Multi-project (`tracked_projects[]`) |
| **Gmail** | Google OAuth 2.0 | Asynchronous Background Poller | Triage rules & label filters |

---

## 🚀 Quick Start (Docker Compose)

### 1. Prerequisites
- Docker Engine 24.0+ & Docker Compose v2+
- OpenAI API Key (for semantic vector embeddings & diagnosis engine)

### 2. Environment Setup
Create a `.env` file in the workspace root:

```bash
OPENAI_API_KEY=sk-proj-your-openai-key
JWT_SECRET=your-secure-jwt-secret
ENCRYPTION_KEY=your-fernet-key
```

### 3. Launch Services
Start all 9 containers in detached mode:

```bash
docker-compose up -d --build
```

The system will start:
- **FastAPI Backend API**: `http://localhost:8000/docs`
- **React Control Dashboard**: `http://localhost:5173`
- **RabbitMQ AMQP Management**: `http://localhost:15672`
- **PostgreSQL Database**: `localhost:5433`
- **MongoDB Evidence Store**: `localhost:27017`

---

## 🧪 Testing Suite

Execute the automated backend test suite inside the running backend container:

```bash
docker exec oip_backend pytest
```

---

## 📚 Technical Documentation

For in-depth architectural details, database schemas, and LLM prompt specifications:
- 📄 **[TECHNICAL_SYSTEM_SPEC.md](file:///Users/adhisharavind/Desktop/Service-Assistant/TECHNICAL_SYSTEM_SPEC.md)** — Comprehensive Master System Architecture & Specifications Document.
- 📄 **[HANDOFF.md](file:///Users/adhisharavind/Desktop/Service-Assistant/HANDOFF.md)** — Production Deployment & Oracle Cloud Always Free Setup Guide.

---

## 📄 License

Internal Operational Intelligence Platform — Proprietary & Confidential.
