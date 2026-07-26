# 🔮 Future Architecture & Feature Roadmap

---

## 📡 1. Real-Time Telemetry Push (SSE / WebSockets)

### Context & Goal
Currently, the Attention Deck and Investigation Details dashboards rely on polling via TanStack Query. As incoming telemetry event volume grows across multi-tenant organizations, real-time event delivery via Server-Sent Events (SSE) or WebSockets will provide instantaneous dashboard updates without page refreshes.

### Proposed Architecture

```
                               ┌───────────────────────────────────┐
                               │       Incoming Webhook Ingest     │
                               │ (Slack, Jira, GitHub, Gmail, etc.)│
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │   Ingestion Pipeline Orchestrator  │
                               │      (backend/app/ingest)         │
                               └─────────────────┬─────────────────┘
                                                 │
                                       (Event Correlated)
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │    Redis Pub/Sub Event Bus        │
                               │   Channel: `org:{org_id}:events`  │
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │   FastAPI Event Stream Gateway    │
                               │      `GET /api/v1/events/stream`  │
                               │     (Server-Sent Events / SSE)    │
                               └─────────────────┬─────────────────┘
                                                 │
                                           (HTTP Stream)
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │       React Frontend SPA          │
                               │  EventSource -> TanStack Query    │
                               │      Cache Invalidation           │
                               └───────────────────────────────────┘
```

### Technical Specification

1. **Protocol Choice: Server-Sent Events (SSE)**
   - Single-directional server-to-client streaming over standard HTTP/2 or HTTP/1.1.
   - Built-in browser reconnection handling (`EventSource` API).
   - Simpler authentication (standard Bearer JWT in header or short-lived stream token in query parameter) compared to WebSocket handshakes.

2. **Backend Gateway Endpoint (`backend/app/events/routes.py`)**:
   - `GET /api/v1/events/stream`
   - Validates JWT access token and active tenant organization.
   - Yields `text/event-stream` formatted messages:
     ```http
     HTTP/1.1 200 OK
     Content-Type: text/event-stream
     Cache-Control: no-cache
     Connection: keep-alive

     event: evidence_created
     data: {"investigation_id": "...", "evidence_id": "...", "type": "slack", "summary": "..."}
     ```

3. **Frontend Connection Orchestrator (`frontend/src/lib/sse.ts`)**:
   - Global SSE client subscribing to the active tenant stream upon user authentication.
   - Triggers optimistic cache invalidations (`queryClient.invalidateQueries(['investigations'])`, `queryClient.invalidateQueries(['evidence'])`).
   - Plays dynamic toast notifications for critical incoming incident signals.

---

## 🧠 2. Additional Future Enhancements

* **Asynchronous Multi-Evidence LLM Clustering**: Background worker pool using Celery/Arq to cluster independent standalone evidence logs into emerging incidents based on semantic drift detection.
* **Bi-directional Slack Bot Interaction**: Inline interactive Slack buttons (`[Approve Fix]`, `[Acknowledge]`, `[Close Incident]`) sending callback webhooks directly to OIP backend endpoints.
* **Vector Search Database Upgrade**: Migration from MongoDB vector search / cosine similarity fallback to Qdrant or Milvus for sub-10ms similarity queries across millions of historical telemetry embeddings.
