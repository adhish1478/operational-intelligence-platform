# MVP Product Specification

This document defines the Minimum Viable Product (MVP) boundary, integration rule schemas, and API contracts for the **Operational Intelligence Platform (OIP)**.

---

## 1. Integration Configuration Rules & Schemas

Integrations store configuration rules inside the PostgreSQL `integrations.config` JSONB column.

### 1.1. Gmail Integration Configuration

```json
{
  "search_query": "label:alerts is:unread",
  "allowed_senders": [
    "alerts@datadog.com",
    "github@github.com",
    "pagerduty.com"
  ],
  "required_keywords": [
    "critical",
    "incident",
    "error",
    "failed",
    "outage"
  ],
  "optional_subject_filters": [
    "Alert:",
    "Urgent:"
  ]
}
```

#### Rule Enforcement Behavior
1. **Search Query**: The background Gmail worker polls emails matching `search_query`.
2. **Allowed Senders**: Ingest drops emails whose sender address does not match at least one string in `allowed_senders`.
3. **Required Keywords**: Ingest drops emails whose subject or body does not contain at least one keyword in `required_keywords`.

---

### 1.2. GitHub Integration Configuration

```json
{
  "tracked_repos": [
    "adhish1478/operational-intelligence-platform",
    "org/backend-service"
  ]
}
```

---

### 1.3. Slack Integration Configuration

```json
{
  "channel_id": "C041234567",
  "channel_name": "#production-alerts"
}
```

---

### 1.4. Jira Integration Configuration

```json
{
  "tracked_projects": [
    "PROD",
    "SEC"
  ]
}
```

---

## 2. Ingestion Response Contracts

When an event payload is submitted to `POST /api/v1/ingest/{integration_id}`, the ingestion service processes the payload and returns a JSON response matching one of four status categories:

### 2.1. Ignored Event (Filtered or Noise)
```json
{
  "status": "ignored",
  "reason": "Sender 'spammer@newsletter.com' is not in allowed_senders list."
}
```

### 2.2. Correlated Signal (Attached to Existing Investigation)
```json
{
  "status": "correlated",
  "investigation_id": "e4b321a0-5c62-4f81-9b12-3a456789abcd",
  "evidence_id": "c1d2e3f4-a5b6-7c8d-9e0f-1a2b3c4d5e6f"
}
```

### 2.3. Standalone Evidence Only (Not Incident-Worthy)
```json
{
  "status": "evidence_only",
  "evidence_id": "c1d2e3f4-a5b6-7c8d-9e0f-1a2b3c4d5e6f",
  "reason": "Signal stored as standalone evidence; not incident-worthy for new Investigation creation."
}
```

### 2.4. Created Investigation (Incident-Worthy Signal)
```json
{
  "status": "created",
  "investigation_id": "f8a7b6c5-d4e3-2f1a-0b9c-8d7e6f5a4b3c",
  "evidence_id": "c1d2e3f4-a5b6-7c8d-9e0f-1a2b3c4d5e6f"
}
```

---

## 3. Ingestion Pipeline Responsibilities Matrix

| Stage | Responsibility | Primary Method | Output |
| :--- | :--- | :--- | :--- |
| **Stage 1** | Platform Filter | `IngestService.platform_filter()` | `(allowed: bool, reason: str \| None)` |
| **Stage 2** | Payload Normalization | `IngestService.normalize_payload()` | `parsed_payload: dict` |
| **Stage 3** | Signal / Noise Classifier | `IngestService.classify_signal()` | `(is_signal: bool, reason: str \| None)` |
| **Stage 4** | Correlation Engine | `IngestService.correlate_signal()` | `matched_investigation: Investigation \| None` |
| **Stage 5a** | Incident-Worthiness Check | `IngestService.is_incident_worthy()` | `is_worthy: bool` |
| **Stage 5b** | Storage & Instantiation | `IngestService.correlate_and_process()` | Response Dictionary Contract |
