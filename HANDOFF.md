# 🚀 Operational Intelligence Platform — Architecture & Deployment Handoff Guide

## 📌 Executive System Overview
The **Operational Intelligence Platform (OIP)** is an enterprise-grade, multi-agent AI incident triage and forensics platform. It automatically ingests signals across engineering tools (**GitHub, Slack, Jira, Gmail**), correlates evidence, detects incidents, and executes **DAG-orchestrated Multi-Agent Root Cause Analysis (RCA)** with strict grounding and zero LLM hallucinations.

---

## 🛠️ Complete Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | React 18, Vite, TypeScript, TailwindCSS, Lucide Icons, React Query, SSE EventSource |
| **Backend API** | FastAPI (Python 3.11), Pydantic v2, AsyncOpenAI (GPT-4o Structured Outputs), SSE Streaming |
| **Database Layer** | **PostgreSQL 16** (Relational metadata via SQLAlchemy Async), **MongoDB 7** (Raw telemetry via Motor) |
| **Messaging & Workers** | **RabbitMQ 3.13**, Background Worker Tasks, Alembic Database Migrations |
| **Observability** | Prometheus v2.51, Grafana v10.4, Nginx Reverse Proxy (HTTP/2) |
| **Orchestration** | Docker Compose (9 Microservice Containers) |

---

## 📂 Git & Branching Status

- **GitHub Repository**: `https://github.com/adhish1478/operational-intelligence-platform`
- **Active Branch**: `feat/sleek-dashboard-ui` *(Clean, committed, and fully pushed to origin)*
- **Previous Branch**: `feature/multi-agent-analysis`
- **Test Suite Status**: **52 / 52 Pytest Unit & Integration Tests Passing (100% Green)**

---

## 🐳 Docker Container Topology & Port Mappings

The entire platform runs in containerized isolation via `docker-compose.yml`:

| Service Name | Container Name | Internal Port | Host Port | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `frontend` | `oip_frontend` | 80 | `5173` | React SPA served via Nginx |
| `backend` | `oip_backend` | 8000 | `8000` | FastAPI REST & SSE API Engine |
| `worker` | `76afb6503177_oip_worker` | 8000 | N/A | Async Telemetry & Ingestion Worker |
| `db` | `oip_db` | 5432 | `5433` | PostgreSQL Relational Database |
| `mongodb` | `oip_mongodb` | 27017 | `27017` | MongoDB Document Store for Evidence |
| `rabbitmq` | `oip_rabbitmq` | 5672, 15672 | `5672`, `15672` | Message Broker & AMQP Management |
| `nginx` | `oip_nginx` | 80, 443 | `80`, `443` | Reverse Proxy & SSL Router |
| `prometheus` | `oip_prometheus` | 9090 | `9090` | System Metric Collector |
| `grafana` | `oip_grafana` | 3000 | `3000` | Operational Dashboard Visualization |

---

## 🧠 Multi-Agent DAG Forensics Architecture

The diagnosis engine executes a 2-stage Directed Acyclic Graph (DAG):

```mermaid
graph TD
    A["Incoming Telemetry Signal / Trigger"] --> B["Triage & Router Agent"]
    B -->|"Critical / High Severity"| C["Stage 1: Parallel Execution"]
    C --> D["Technical RCA Agent"]
    C --> E["Business Impact & Financial SLA Agent"]
    D --> F["Stage 2: Remediation & Hotfix Agent"]
    E --> F
    F --> G["Unified Structured Output & SSE Stream"]
```

### Strict Grounding & Anti-Hallucination Enforcements:
1. **GitHub Commit Check**:
   - If an investigation contains code commits (GitHub PR/Push), it extracts the exact SHA hash and generates a `git revert <hash>` command.
   - If an investigation contains **NO code commits** (e.g. Slack/Gmail only), `offending_commit` is strictly set to `null`, `error_fingerprints` to `[]`, and `git_rollback_command` to `"N/A - No offending commit hash identified in evidence stream"`.
2. **Post-Parse Enforcement**:
   - Python-level post-processing overrides any attempted LLM hallucination before saving to DB or sending over SSE.

---

## 🔐 Environment Variables (`.env`)

Check your `.env` file before launching:

```env
# Core Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
SECRET_KEY=super-secret-key-change-in-production

# Open AI API Key (For DAG Multi-Agent GPT-4o Diagnosis)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx

# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=operational_intel
DATABASE_URL=postgresql+asyncpg://postgres:postgres@oip_db:5432/operational_intel

# MongoDB Configuration
MONGO_URI=mongodb://oip_mongodb:27017
MONGO_DB_NAME=evidence_store

# RabbitMQ Broker
RABBITMQ_URL=amqp://guest:guest@oip_rabbitmq:5672//
```

---

## 🚀 Step-by-Step Deployment Instructions

### Option 1: Full Docker Compose Deployment (Local or Single VPS like Oracle Cloud)
1. **Clone Repo & Switch Branch**:
   ```bash
   git clone https://github.com/adhish1478/operational-intelligence-platform.git
   cd operational-intelligence-platform
   git checkout feat/sleek-dashboard-ui
   ```
2. **Configure `.env`**:
   Ensure `OPENAI_API_KEY` is set.
3. **Spin Up All 9 Containers**:
   ```bash
   docker-compose up -d --build
   ```
4. **Verify Health**:
   ```bash
   docker exec oip_backend pytest
   ```

### Option 2: Serverless / Cloud Service Deployment
- **Frontend (React)**: Host on **Vercel** or **Netlify** (Root directory: `frontend/`, Build Command: `npm run build`, Output Directory: `dist`).
- **Backend (FastAPI)**: Host on **Render.com** or **Koyeb** (Root directory: `backend/`, Command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`).
- **PostgreSQL**: Provision a free instance on **Neon.tech** or **Supabase**.
- **MongoDB**: Provision a free M0 cluster on **MongoDB Atlas**.
- **RabbitMQ**: Provision a free instance on **CloudAMQP**.

---

## 📋 Key API Endpoints & Routes

| HTTP Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/investigations/` | Fetch all operational investigations |
| `PATCH` | `/api/v1/investigations/{id}` | Update status (e.g. resolve incident) |
| `POST` | `/api/v1/investigations/{id}/diagnose` | Run Multi-Agent DAG Forensics |
| `GET` | `/api/v1/investigations/{id}/diagnose/stream` | SSE Live Stream for Multi-Agent steps |
| `GET` | `/api/v1/investigations/evidence/recent` | Real-time correlated evidence stream |
| `GET` | `/api/v1/reports/` | Generated intelligence reports |
