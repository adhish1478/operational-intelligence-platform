# Resume Alignment & Architecture Roadmap

This document maps the Operational Intelligence Platform (OIP) features to the operational claims on the engineering resume.

## Resume Baseline Claims

```text
Operational Command Center — AI-Powered Operational Intelligence Platform
FastAPI, React, PostgreSQL, MongoDB, Redis, RabbitMQ, Kafka, OpenAI, Docker

• Architected an operational intelligence platform that aggregates signals from Slack, Jira, GitHub, Gmail, and Notion into a unified investigation workspace, enabling proactive detection of customer escalations, release blockers, and operational risks.
• Designed event-driven ingestion pipelines using Kafka and RabbitMQ to process cross-platform activity streams, normalize evidence records, and trigger asynchronous investigation workflows at scale.
• Implemented multi-agent analysis workflows that correlate customer communications, engineering tickets, pull requests, and system events to generate root-cause investigations, business impact assessments, and recommended actions.
• Built investigation-centric dashboards with evidence timelines, entity relationships, and operational reporting, allowing users to trace incidents across services, customers, projects, and teams from a single interface.
```

---

## Phase Roadmap

### Phase 1: Asynchronous Event Queue Pipeline (RabbitMQ) [IN PROGRESS]
- **Branch**: `feature/rabbitmq-event-pipeline`
- **Topology**:
  - `oip.events.exchange` (Topic Exchange)
  - `oip.events.ingest` (Main Ingestion Queue)
  - `oip.events.retry` (Retry Queue with TTL exponential backoff)
  - `oip.events.dlq` (Dead Letter Queue for poison messages)
- **Features**:
  - Asynchronous webhook producer via `aio-pika`
  - Worker consumer with exponential backoff retries ($2^n$ delay)
  - State Machine Circuit Breaker (`CLOSED` -> `OPEN` -> `HALF-OPEN`)
  - Integration into FastAPI ingestion endpoints

### Phase 2: Multi-Agent Analysis Workflow
- **Features**:
  - Orchestrate specialized analysis sub-agents:
    1. **RCA Agent**: Technical root cause & stack trace parsing.
    2. **Business Impact Agent**: Financial risk, affected SLA, customer blast radius.
    3. **Remediation Agent**: Recommended hotfix steps & verification commands.

### Phase 3: Entity Relationship Topology Graph Visualizer
- **Features**:
  - Graph/node visualization connecting Services ↔ Customers ↔ Projects ↔ Teams in `InvestigationDetails.tsx`.

### Phase 4: Notion Integration Connector
- **Features**:
  - Notion API integration for runbooks, release notes, and incident docs.
