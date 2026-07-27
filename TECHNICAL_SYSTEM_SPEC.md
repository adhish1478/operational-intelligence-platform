# 📐 Operational Intelligence Platform (Sigint AI / AGY)
## Master System Architecture & Technical Specification Reference

---

## 🏛️ 1. Executive Summary & Core Mission

The **Operational Intelligence Platform (Sigint AI)** is an enterprise operational intelligence and incident triage platform built to eliminate operational signal overload. Modern software teams receive thousands of incoming telemetry events daily across disparate platforms (**Gmail**, **Slack**, **GitHub**, **Jira**, **Sentry**, **Datadog**, **PagerDuty**).

### The Core Problem:
Without an intelligent signal processing architecture:
1. Every raw email, commit notification, or alert floods the incident queue, causing severe alert fatigue.
2. Unrelated events get mistakenly grouped into a single ticket due to superficial word overlaps (e.g. matching generic words like `gateway` or `service`).
3. Related events from different platforms (e.g. a Datadog alert, a Sentry OOM exception, and a PagerDuty notification) fail to correlate because they use different terminology across different channels.

### The Solution:
Our platform introduces a **5-Stage Ingestion Pipeline** powered by a **Multi-Phase Hybrid Correlation Engine**, **LLM Signal Intelligence** (GPT-4o-mini), and a **Polyglot Persistence Model**. It filters noise, correlates cross-platform telemetry into active incident containers with high mathematical precision, and routes routine events into standalone evidence without polluting the operational incident dashboard.

---

## 💻 2. Technology Stack & Architectural Overview

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | **FastAPI (Python 3.11)** | High-performance asynchronous API & background worker processing |
| **Relational DB** | **PostgreSQL (SQLAlchemy 2.0 Async)** | Stores tenant organizations, user accounts, integration configs, and **`Investigations`** |
| **Document DB** | **MongoDB (Motor / PyMongo Async)** | Stores unstructured **`Evidence`** telemetry documents |
| **Message Broker** | **RabbitMQ (aio-pika 10.0+)** | Asynchronous event-driven queue pipeline, exponential backoff retries, DLQ, & Circuit Breaker |
| **Frontend Framework** | **React 18 + TypeScript + Vite** | Single Page Application (SPA) with strong type safety |
| **State & Query** | **TanStack Query v5 + Zustand** | In-memory server cache management, optimistic updates, and global auth state |
| **Styling & UI** | **Tailwind CSS + Lucide Icons + React-Markdown** | Linear / Palantir-inspired high-density operational design system with rich Markdown rendering |
| **Security & Crypto** | **Fernet (Cryptography) + PyJWT** | AES-128-CBC credential encryption, JWT token rotation, & OAuth 2.0 3LO token auto-refresh |
| **AI / Embeddings** | **OpenAI API (`text-embedding-3-small`)** | 1536-dimensional semantic vector embeddings for cross-platform signal correlation |
| **AI / Classification** | **OpenAI API (`gpt-4o-mini` & `gpt-4o`)** | LLM signal classifier for Slack/telemetry & automated Root Cause Analysis (RCA) diagnoses |

---

## 🗄️ 3. Polyglot Persistence & Data Model Strategy

Our database architecture decouples **Relational Incident Metadata** (PostgreSQL) from **Unstructured Telemetry Logs** (MongoDB).

```
                      ┌─────────────────────────────────────────┐
                      │    PostgreSQL (Relational Storage)      │
                      ├─────────────────────────────────────────┤
                      │ • Organizations  (Tenants)              │
                      │ • Users & Memberships                   │
                      │ • Integrations   (Platform Credentials) │
                      │ • Investigations (Incident Containers)  │
                      └────────────────────┬────────────────────┘
                                           │
                                  1-to-N   │ (Linked by investigation_id UUID)
                                           │
                      ┌────────────────────▼────────────────────┐
                      │     MongoDB (Unstructured Storage)      │
                      ├─────────────────────────────────────────┤
                      │ • Evidence Collection (Telemetry Logs)  │
                      │   - Gmail emails, Slack messages,       │
                      │     GitHub commits, Jira issues         │
                      └─────────────────────────────────────────┘
```

### 1. PostgreSQL Schema Highlights:
* **`organizations`**: Tenant boundary (`id`, `name`, `slug`, `created_at`).
* **`users`**: Platform user accounts (`id`, `email`, `hashed_password`, `first_name`, `last_name`).
* **`integrations`**: Platform connections (`id`, `organization_id`, `platform`, `credentials_encrypted`, `config`, `status`). Enforces 1-to-1 platform mapping per organization.
* **`investigations`**: Incident triage containers (`id`, `organization_id`, `title`, `description`, `severity`, `status`, `detected_at`).
  * `severity`: `critical`, `high`, `medium`, `low`
  * `status`: `open`, `investigating`, `resolved`, `closed`

### 2. MongoDB Schema (`evidence` collection):
* **`id`**: Unique UUID string identifier.
* **`investigation_id`**: UUID string referencing a PostgreSQL `investigation.id`, OR `null` for standalone evidence.
* **`type`**: Source platform (`gmail`, `slack`, `github`, `jira`, `alert`).
* **`summary`**: Event headline/subject.
* **`author_name`**: Sender or committer name.
* **`source_url`**: Direct link to source item.
* **`metadata`**: JSON object storing full payload headers, snippet, and multiline **`body`** text.
* **`created_at`**: Timestamp.

> **Key Architectural Guarantee**: Evidence can exist independently (`investigation_id = null`) as standalone operational telemetry, eliminating PostgreSQL table clutter for non-incident events.

---

## 🔌 4. Integration Architecture & OAuth Flows

### 4.1 Connected Integrations Summary

| Platform | Auth Method | Webhook Delivery | Tracked Scope |
|---|---|---|---|
| **Slack** | OAuth 2.0 (Bot Token) | Event Subscriptions → `POST /api/v1/ingest/slack` | Multi-channel (`tracked_channels[]`) |
| **Jira** | OAuth 2.0 (3LO Authorization Code) | Dynamic Webhooks → `POST /api/v1/ingest/jira` | Multi-project (`tracked_projects[]`) |
| **GitHub** | OAuth 2.0 (App Installation) | Repository Webhooks → `POST /api/v1/ingest/{integration_id}` | Multi-repo (`tracked_repos[]`) |
| **Gmail** | Google OAuth 2.0 | Background Polling (60s interval) | User-configured triage rules |

### 4.2 Slack OAuth & Event Subscription

**Bot Scopes**: `channels:read`, `groups:read`, `chat:write`, `app_mentions:read`, `users:read`, `reactions:read`

OAuth flow: `GET /api/v1/integrations/slack/authorize` → Slack OAuth → `GET /api/v1/integrations/slack/callback`

**Multi-Channel Tracking**: UI dynamically fetches workspace channels from Slack `conversations.list` API. Users select multiple channels. Events from non-tracked channels are dropped at Step 1 (Platform Filter).

**Event Types Processed**: `message`, `message_changed`, `message_deleted`, `channel_topic`, `channel_purpose`, `file_share`, `reaction_added`

### 4.3 Jira OAuth 2.0 (3LO) & Dynamic Webhooks

**Scopes**: `read:jira-work`, `write:jira-work`, `read:jira-user`, `manage:jira-webhook`, `offline_access`

OAuth flow:
1. `GET /api/v1/integrations/jira/authorize` → Redirects to `auth.atlassian.com/authorize`
2. User grants consent → `GET /api/v1/integrations/jira/callback`
3. Callback exchanges authorization code for tokens via `POST auth.atlassian.com/oauth/token`
4. Fetches Cloud ID via `GET api.atlassian.com/oauth/token/accessible-resources`
5. Dynamically fetches workspace project keys (`GET /rest/api/3/project`)
6. Registers dynamic webhooks with project-specific JQL filter: `project in ("KAN", "PROD")`

**Webhook Events Registered (8 total)**:
`jira:issue_created`, `jira:issue_updated`, `jira:issue_deleted`, `comment_created`, `comment_updated`, `comment_deleted`, `worklog_created`, `attachment_created`

### 4.4 GitHub OAuth & Repository Webhooks

OAuth flow: `GET /api/v1/integrations/github/authorize` → GitHub OAuth → `GET /api/v1/integrations/github/callback`

**Events Processed**: `pull_request`, `workflow_run`, `issues`, `push`

### 4.5 Gmail Google OAuth & Background Polling

OAuth flow: `GET /api/v1/integrations/gmail/authorize` → Google OAuth → `GET /api/v1/integrations/gmail/callback`

**Polling**: Background worker polls Gmail API every 60 seconds for new messages since `last_checked_time`.

---

## ⚙️ 5. The 5-Stage Ingestion Pipeline Architecture

Every incoming signal (polled via background worker every 60s or received via webhooks) flows through **RabbitMQ Asynchronous Dispatch (Step -1)** followed by **5 sequential pipeline stages**:

```
 [Raw Webhook Event]
        │
        ▼
 ┌────────────────┐
 │    Step -1     │ ──► Publishes to RabbitMQ `oip.events.exchange`
 │ Asynchronous   │     • Consumer Queue: `oip.events.ingest`
 │ RabbitMQ Queue │     • Stateful `CircuitBreaker` (CLOSED -> OPEN -> HALF-OPEN)
 └───────┬────────┘     • Exponential Backoff Retries: 2s -> 4s -> 8s -> 16s -> 32s
         │              • Poison Message Isolation: `oip.events.dlq`
         ▼
 ┌────────────────┐
 │    Step 0      │ ── (Duplicate event_id / client_msg_id in cache?) ──► IGNORED
 │ Deduplication   │
 └───────┬────────┘
         │ (New Event)
         ▼
 ┌───────────────┐
 │    Step 1     │ ── (Fails Boundary Check?) ──► IGNORED (0 DB Writes)
 │ Platform      │
 │ Filter        │
 └──────┬────────┘
        │ (Passes)
        ▼
 ┌───────────────┐
 │    Step 2     │ ──► Normalizes to uniform schema:
 │ Normalize     │     { summary, author_name, source_url, metadata.body }
 │ Payload       │     [Slack]: Resolve user/channel IDs + LLM classify
 └──────┬────────┘     [Jira]: Extract event tags + author resolution
        │
        ▼
 ┌───────────────┐
 │  Step 2.5     │ ── (Slack edit/delete?) ──► UPDATE/RETRACT MongoDB Evidence
 │ Evidence      │    (Jira edit/delete?)  ──► UPDATE/RETRACT MongoDB Evidence
 │ Lifecycle     │
 └──────┬────────┘
        │ (New event)
        ▼
 ┌───────────────┐
 │    Step 3     │
 │ Signal/Noise  │ ── (Fails Rules?) ──► IGNORED (0 DB Writes)
 │ Classifier    │
 └──────┬────────┘
        │ (Is Valid Signal)
        ▼
 ┌───────────────┐
 │  Step 3.5     │ ── (Slack thread_ts?) ──► THREAD CORRELATED (Deterministic)
 │ Deterministic │    (Jira issue_key?)  ──► ISSUE-KEY CORRELATED (Deterministic)
 │ Correlation   │
 └──────┬────────┘
        │ (No deterministic match)
        ▼
 ┌───────────────┐
 │  Step 3.75    │ ── (Text contains Jira issue key e.g. KAN-999?)
 │ Cross-Platform│    ──► CROSS-PLATFORM LINKED (Slack/GitHub/Gmail -> Jira Investigation)
 │ Key Linking   │
 └──────┬────────┘
        │ (No issue key match)
        ▼
 ┌───────────────┐
 │    Step 4     │
 │ Hybrid        │ ── (Score >= 0.25 Threshold) ──► CORRELATED (Attach Evidence to
 │ Correlation   │                                  Existing Investigation in MongoDB)
 │ Engine        │
 └──────┬────────┘
        │ (Uncorrelated: Score < 0.25)
        ▼
 ┌───────────────┐
 │    Step 5     │
 │ Incident      ├──── (Incident Worthy?) ─────► CREATED (Spawn New SQL Investigation
 │ Worthiness    │                                + Link Evidence in MongoDB)
 │ & Routing     │
 └──────┬────────┴──── (Routine Event?) ───────► EVIDENCE_ONLY (Store in MongoDB with
                                                   investigation_id = null)
```

---

### Detailed Stage Specifications:

#### **Step -1: Asynchronous Event Queue Pipeline (RabbitMQ) & Production Considerations**

The messaging tier acts as an asynchronous buffer between incoming platform webhooks and backend database correlation workers. Webhook HTTP handlers (`/api/v1/ingest/...`) immediately serialize raw event envelopes and publish them to RabbitMQ `oip.events.exchange` with a non-blocking `status: queued` response (~5-15ms overhead).

##### **Architecture Details:**
1. **Exchange & Queue Topology**:
   - `oip.events.exchange` (Topic Exchange) routes messages by platform key (`event.ingest.<platform>`).
   - `oip.events.ingest` (Main Consumer Queue) feeds `IngestEventWorker`.
   - `oip.events.retry` (Exponential Backoff Queue) uses per-message TTL ($2^{\text{retry\_count}} \times 2000\text{ms}$) with `x-dead-letter-exchange: oip.events.exchange` to dead-letter expired retries back to main processing without blocking other messages.
   - `oip.events.dlq` (Dead Letter Queue) isolates poison messages after `QUEUE_MAX_RETRIES` (5 attempts).
2. **Circuit Breaker State Machine**:
   - `CircuitBreaker` in `CLOSED` state monitors worker execution.
   - Tripped to `OPEN` state after 5 consecutive downstream database/OpenAI failures.
   - Automatically defers inbound events to the retry queue for a 30s cooldown before probing in `HALF_OPEN` state.
3. **Resilient Fallback**:
   - If RabbitMQ broker is unreachable, webhook endpoints seamlessly fall back to synchronous in-process correlation without breaking API execution.

##### **Current Production Limitations & Bottlenecks (Architectural Trade-offs):**
* **Lack of Consumer Prefetch (QoS Tuning)**: Currently, the worker consumer operates without `channel.set_qos(prefetch_count=N)`. Under high webhook burst events (e.g. 5,000 GitHub push notifications/minute), RabbitMQ delivers all queued messages to the single consumer's memory buffer simultaneously, creating potential worker memory spikes.
* **Single Worker Replica Scalability Limit**: The current deployment runs a single `IngestEventWorker` event loop instance. While RabbitMQ natively supports competing consumers (multiple worker containers consuming concurrently from `oip.events.ingest`), horizontal auto-scaling (KEDA / HPA) is not yet wired up.
* **Unmonitored Dead Letter Queue (DLQ)**: Poison messages failing after 5 retries are safely isolated in `oip.events.dlq`, but there is currently no background worker monitoring DLQ depth or triggering automated alert notifications (e.g. PagerDuty / Slack alerts for unprocessable webhooks).
* **Metrics & Telemetry Observability Gap**: Broker metrics (queue depth, message ingestion rate, consumer lag, retry counts) are currently visible only via the RabbitMQ Management UI (`localhost:15672`) rather than exported directly to a centralized Prometheus / Grafana dashboard.
* **Basic Connection Recovery**: Utilizes direct async AMQP connection pooling (`aio_pika.connect`) with try-catch fallback rather than `aio_pika.connect_robust()` for automatic silent TCP socket reconnection during transient network partitioning.

#### **Step 0: Event Deduplication**
In-memory `PROCESSED_EVENT_IDS` set (capped at 10,000 entries, auto-cleared on overflow). Suppresses duplicate `event_id` or `client_msg_id` from Slack retries and webhook replays.

#### **Step 1: Platform Filter (`platform_filter`)**
Validates workspace boundary criteria:
* **GitHub**: Checks if incoming repository (`repository.full_name`) matches `tracked_repos` in integration config.
* **Slack**: Checks if incoming channel matches `tracked_channels[]` or `channel_id`.
* **Jira**: Checks if project key matches `tracked_projects[]`.
* **Gmail**: Pass-through (no boundary restriction).

#### **Step 2: Payload Normalization (`normalize_payload`)**
Parses platform-specific JSON payloads into a uniform dictionary containing `summary`, `author_name`, `source_url`, and structured `metadata`:

**Gmail**: Base64url decodes multiline email bodies (`body`), header subjects, and sender info.

**GitHub Webhooks**:
  * `pull_request`: Title, head branch (`fix/auth-gateway-oom`), base branch (`main`), state (`opened`, `merged`), author, body text, and repo slug.
  * `workflow_run`: CI workflow name, conclusion (`failure`, `success`), head branch, build runner actor, and log URL.
  * `issues`: Issue number, title, body, and operational labels (`bug`, `P0`, `critical`, `blocker`).
  * `push`: Branch ref (`refs/heads/main`), commit message, committer, and repo slug.

**Slack Events**:
  * Extracts subtype (`message`, `message_changed`, `message_deleted`, `channel_topic`, `channel_purpose`, `file_share`, `reaction_added`).
  * Extracts channel ID, user ID, `ts`, `thread_ts`, client message ID, file metadata, reaction emoji, previous text (for edits).
  * Generates clickable permalink: `https://slack.com/archives/{channel}/p{clean_ts}`.
  * **Post-normalization**: Resolves opaque Slack user IDs → display names via `users.info` API. Resolves channel IDs → channel names via `conversations.info` API. Results cached in-memory (`SLACK_USER_CACHE`, `SLACK_CHANNEL_CACHE`).
  * **LLM Signal Intelligence**: Text classified by GPT-4o-mini into `signal_type` (`incident` | `debugging` | `status_update` | `discussion` | `noise`), `urgency` (`critical` | `high` | `medium` | `low` | `none`), extracted `entities`, and `reasoning`. Falls back to keyword heuristics if `OPENAI_API_KEY` unset.

**Jira Webhooks**:
  * Extracts issue key, title, issue type, priority, status, project key & name.
  * Differentiates 8 event types with distinct summary tags:
    - `jira:issue_created` → `Jira [KAN-3] [CREATED] (Bug/To Do): Title`
    - `jira:issue_updated` → `Jira [KAN-3] [UPDATED] (Bug/In Progress): Title`
    - `jira:issue_deleted` → `Jira [KAN-3] [DELETED]: Title`
    - `comment_created` → `Jira [KAN-3] [NEW COMMENT] by Author: Comment text`
    - `comment_updated` → `Jira [KAN-3] [COMMENT EDITED] by Author: Updated text`
    - `comment_deleted` → `Jira [KAN-3] [COMMENT DELETED] by Author`
    - `attachment_created` → `Jira [KAN-3] [ATTACHMENT]: error_log.txt (4096 bytes)`
    - `worklog_created` → `Jira [KAN-3] [WORKLOG]: 2h 30m logged by Author`
  * Author resolution: Parses `comment.author.displayName`, `attachment.author.displayName`, `worklog.author.displayName`, or `payload.user.displayName` depending on event type.
  * Generates clickable permalink: `https://{site}.atlassian.net/browse/{key}`.

#### **Step 2.5: Evidence Lifecycle (Edits & Deletions)**
Handles mutable evidence for platforms that support message edits and deletions:

**Slack**:
  * `message_changed` → `handle_slack_edit()`: Updates existing MongoDB evidence record in-place. Sets `metadata.edited = True`, `metadata.previous_text`, appends `[edited]` to summary.
  * `message_deleted` → `handle_slack_delete()`: Marks existing MongoDB evidence record as retracted. Sets `metadata.retracted = True`, appends `[RETRACTED]` to summary.

**Jira** (Implemented & Operational):
  * `comment_updated` → `handle_jira_comment_edit()`: Updates existing comment evidence in MongoDB. Sets `metadata.comment`, `metadata.edited = True`, appends `[edited]` to summary.
  * `comment_deleted` → `handle_jira_comment_delete()`: Marks existing comment evidence as retracted in MongoDB (`metadata.retracted = True`, appends `[RETRACTED]`).
  * `jira:issue_deleted` → `handle_jira_issue_delete()`: Marks ALL evidence items matching the issue key as retracted in MongoDB.

#### **Step 3: Signal / Noise Classifier (`classify_signal`)**

**Gmail, GitHub, Jira (Default)**: Evaluates user-configured triage settings using an **Inclusive OR Model**:
* **Trigger 1 (Allowed Senders)**: Is the sender email/domain in `allowed_senders`?
* **Trigger 2 (Subject Rules)**: Does the subject match `subject_contains` or `subject_starts_with`?
* **Trigger 3 (Keyword Rules)**: Does the body/summary contain any `required_keywords`?
* If **ANY** trigger matches, the event is classified as an operational **Signal**. If none match, it is dropped as **Noise** (`status: "ignored"`).

**GitHub Specific Noise Filtering**:
* Drops `dependabot[bot]` PRs automatically.
* Drops background maintenance branches: `chore/*`, `docs/*`, `style/*`, `renovate/*`.
* Drops redundant `push` events to non-default PR branches (since the `pull_request` event lifecycle already tracks PR activity).

**Slack LLM-Based Noise Filtering**:
* Filters admin subtypes (`channel_join`, `channel_leave`, `channel_archive`).
* Rejects events where LLM classification returned `signal_type == "noise"` (social greetings, casual chatter).
* Heuristic fallback: Short social phrases ("hey", "thanks", "ok", "👍") auto-classified as noise.

#### **Step 3.5: Deterministic Correlation (Platform-Specific)**

**Slack Thread Correlation** (`correlate_slack_thread`):
* If a message is a thread reply (`thread_ts` present), queries MongoDB for the parent message's evidence record using `{"type": "slack", "metadata.ts": thread_ts, "metadata.channel_id": channel_id}`.
* Returns the parent message's `investigation_id` for O(1) deterministic correlation.
* Thread replies never spawn new investigations.

**Jira Issue-Key Correlation** (`correlate_jira_issue_key` — Implemented & Operational):
* If a Jira event references an issue key (e.g. `KAN-3`), performs O(1) lookup in MongoDB for active non-retracted evidence with that issue key linked to an investigation.
* Comments, attachments, worklogs, and status transitions on `KAN-3` all auto-link to the issue's existing investigation container without hitting the fuzzy hybrid engine.

#### **Step 3.75: Cross-Platform Issue-Key Correlation** (`correlate_cross_platform_keys` — Implemented & Operational)
* Scans incoming non-Jira events (Slack messages, GitHub PR titles/branches, Gmail alerts) for Jira issue keys (`KAN-100`, `PROD-42`, `SEC-9`) via `extract_jira_keys_from_text()`.
* If a referenced issue key matches an active investigation container in MongoDB, auto-links the incoming Slack/GitHub/Gmail event to that investigation deterministically!
* Eliminates multi-investigation fragmentation across platforms.

#### **Step 4: Multi-Phase Correlation Engine (`correlate_signal`)**
Evaluates the incoming signal against active open investigations for the tenant (`status IN ('open', 'investigating')`) using our **Phase 2 Hybrid Scoring Model**:
$$\text{Score} = \Big( 0.40 \cdot \text{EntityScore} + 0.40 \cdot \text{VectorScore} + 0.20 \cdot \text{KeywordScore} \Big) \cdot \text{TimeDecay}$$
* **Branch Entity Priority**: Extracts microservice identifiers directly from branch patterns (`fix/auth-gateway-pod-12-oom` $\rightarrow$ `services: {"auth-gateway-pod-12"}`).
* If a candidate scores $\ge 0.25$, the evidence is attached directly to that existing investigation (`status: "correlated"`).

#### **Step 5: Incident Worthiness & Storage Routing (`is_incident_worthy`)**
If Stage 4 returns no correlation match:

**Slack Incident Routing**:
* `True` ONLY if LLM `signal_type` in (`"incident"`, `"debugging"`) AND `urgency` in (`"critical"`, `"high"`).
* Reactions, topic changes, edits, deletes, and thread replies → `False`.

**GitHub Incident Routing**:
* CI Workflow Failures (`workflow_run.failure`, `cancelled`, `timed_out`).
* Issues labeled `bug`, `P0`, `critical`, or `blocker`.
* PRs on incident branches (`bug/*`, `hotfix/*`, `bugfix/*`, `incident/*`) containing critical incident keywords (`critical`, `outage`, `error`, `failed`, `leak`, `crash`, `panic`, `fatal`, `p0`, `p1`).
* Regular PRs/commits → `False` (stored as standalone evidence).

**Gmail Incident Routing**:
* **Operational System Monitoring Emails**: Emails from monitoring providers (`Datadog`, `Sentry`, `Grafana`, `Kubernetes`, `PagerDuty`, `CloudWatch`, `Prometheus`, `NewRelic`) or containing operational alert prefixes (`[ALERT]`, `[ERROR]`, `[CRITICAL]`, `incident`).
* **Personal Email Filtering**: Personal bank transaction alerts (`ICICI`, `CRED`, `SBI`), newsletters (`The Economist`, `Medium`, `Anaconda`, `NVIDIA`), trading digests (`Groww`, `NSE`), and job alerts (`LinkedIn`, `Indeed`, `hirist`) are filtered out and saved directly as **Standalone Evidence** (`investigation_id = null`).

**Jira Incident Routing** (Implemented & Operational):
* `True` ONLY if metadata `priority` in (`highest`, `high`, `critical`, `p0`, `p1`, `blocker`) OR `issue_type` in (`bug`, `incident`, `security`, `vulnerability`).
* Comments, worklogs, attachments, deletions, or lower priority tasks (`Story`, `Task`) → `False` (stored as standalone evidence or correlated via Step 3.5/3.75).

---

## 🫀 6. Deep Dive: The Core Heart — Multi-Phase Correlation Engine

The correlation engine is the core intelligence of our platform. It answers the question:
> *"Does an incoming telemetry signal belong to an active, ongoing incident, or is it a separate issue?"*

### The Problem With Naive Token Matching:
Simple word-counting algorithms fail in production because:
1. **Generic Word Overlap**: Titles containing generic terms like `gateway` or `service` get incorrectly grouped together even if one is `Auth Gateway` and the other is `Payment Service`.
2. **Lack of Temporal Awareness**: An incident created 10 minutes ago is actively evolving, whereas an investigation opened 3 weeks ago shouldn't pull in new signals.
3. **Vocabulary Mismatch**: A Datadog email might say `Memory Exhaustion` while a Sentry email says `OutOfMemoryError`. Simple set intersection fails to match them.

---

### 🔬 The 3-Phase Multi-Phase Architecture

```
                               ┌────────────────────────────────────────────────────────┐
                               │             INCOMING TELEMETRY SIGNAL                  │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                                                           ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                       PHASE 1: DETERMINISTIC ENGINE                                              │
 ├─────────────────────────────────────────┬──────────────────────────────────────────┬─────────────────────────────┤
 │ 1. Entity Extraction (`extract_entities`)│ 2. Composite Fingerprint                  │ 3. Exponential Time Decay   │
 │    Extracts:                            │    (`build_investigation_fingerprint`)   │    (`compute_time_decay`)   │
 │    • Services: auth-gateway-pod-12     │    Combines: Title + Summaries of all    │    Formula:                 │
 │    • Errors:   502, OutOfMemoryError    │    previously attached evidence from     │    decay = 0.5^(hours / 24) │
 │    • Alert IDs: PD4920, STRIPE-CRIT-9021│    MongoDB into a composite text.       │    Recent = 1.0 | 7d = 0.007 │
 └─────────────────────────────────────────┴──────────────────────────────────────────┴─────────────────────────────┘
                                                           │
                                                           ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                    PHASE 2: SEMANTIC VECTOR EMBEDDING ENGINE                                     │
 ├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ • OpenAI `text-embedding-3-small` (1536-dimensional vector array)                                                │
 │ • Cosine Vector Similarity (`cosine_similarity`): cos(θ) = (A · B) / (||A|| ||B||)                               │
 │ • Automatic Phase 1 Fallback: If OPENAI_API_KEY is unconfigured, returns None & falls back gracefully.          │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                           │
                                                           ▼
 ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                      HYBRID CORRELATION SCORING FORMULA                                          │
 ├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │                                                                                                                  │
 │   FinalScore = [ ( EntityMatch * 0.40 ) + ( CosineVectorSim * 0.40 ) + ( KeywordJaccard * 0.20 ) ] * TimeDecay    │
 │                                                                                                                  │
 │   • EntityMatch = Service Match (+0.60) + Error Code Match (+0.25) + Alert ID Match (+0.15)                     │
 │   • Threshold: If FinalScore >= 0.25 ──► Match Confirmed (CORRELATED)                                             │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Step-by-Step Function Breakdown:

#### 1. Entity Extraction (`extract_entities(text: str) -> dict[str, set[str]]`)
Scans text using targeted regular expressions to isolate high-value system entities:
```python
{
    "services": {"auth-gateway-pod-12"},
    "errors": {"502", "OutOfMemoryError"},
    "alert_ids": {"PD4920", "STRIPE-CRIT-9021"}
}
```

#### 2. Composite Fingerprint Builder (`build_investigation_fingerprint`)
Fetches all evidence documents linked to a candidate investigation from MongoDB and combines them:
$$\text{Composite Text} = \text{Investigation Title} + \text{Evidence Summary \#1} + \text{Evidence Summary \#2} + \dots$$

#### 3. Exponential Time Decay (`compute_time_decay(detected_at, half_life_hours=24.0) -> float`)
Calculates an age decay multiplier:
$$\text{TimeDecay} = 0.5^{\left(\frac{\text{hours\_elapsed}}{24.0}\right)}$$
* **0 Hours Ago**: `1.0` (100% full weight)
* **24 Hours Ago**: `0.5` (50% weight)
* **7 Days Ago**: `0.0078` (0.78% weight)

#### 4. Vector Embedding Generator (`generate_embedding(text) -> list[float] | None`)
Calls OpenAI's `text-embedding-3-small` model to convert text into a 1536-dimensional float vector array. Returns `None` gracefully if unconfigured.

#### 5. Cosine Similarity Calculator (`cosine_similarity(vec_a, vec_b) -> float`)
Calculates dot product similarity between 1536-dimensional vectors:
$$\cos(\theta) = \frac{\mathbf{A} \cdot \mathbf{B}}{\|\mathbf{A}\| \|\mathbf{B}\|}$$

#### 6. Hybrid Correlation Scorer (`score_hybrid_correlation`)
Combines Entity Match (40%), Vector Cosine Similarity (40%), and Keyword Overlap (20%) multiplied by Time Decay:
$$\text{FinalScore} = \Big(\text{EntityMatch} \times 0.40 + \text{CosineSimilarity} \times 0.40 + \text{KeywordMatch} \times 0.20\Big) \times \text{TimeDecay}$$

* **Phase 1 Fallback**: If vector embeddings are `None`, it seamlessly falls back to:
$$\text{FinalScore} = \Big(\text{EntityMatch} \times 0.50 + \text{KeywordMatch} \times 0.30\Big) \times \text{TimeDecay}$$

---

### 📊 Real-World Mathematical Walkthrough Example

#### Active Investigation #1 (Opened 1 Hour Ago):
* **Title**: `Datadog Alert: High Memory Spikes on auth-gateway-pod-12`
* **Attached Evidence**: `Sentry OutOfMemoryError in GatewayController`
* **Timestamp**: 1 hour ago (`TimeDecay = 0.97`)

#### Incoming Email Payload:
* **Subject**: `PagerDuty Incident #4920: Token validation timeout on auth-gateway-pod-12`
* **Body**: `504 Gateway Timeout errors detected on auth-gateway-pod-12`

#### Mathematical Evaluation:
1. **Entity Match Score (40% Weight)**:
   * Both incoming email & investigation refer to `auth-gateway-pod-12`.
   * Service Match = `+0.60` $\rightarrow 0.60 \times 0.40 = \mathbf{0.24}$.
2. **Vector Cosine Similarity (40% Weight)**:
   * OpenAI embedding vector similarity = `0.85`.
   * Vector Score = $0.85 \times 0.40 = \mathbf{0.34}$.
3. **Keyword Jaccard Overlap (20% Weight)**:
   * Non-stop-words overlap (`auth`, `gateway`, `timeout`) = `0.30`.
   * Keyword Score = $0.30 \times 0.20 = \mathbf{0.06}$.
4. **Time Decay**:
   * Elapsed 1 hour $\rightarrow \text{TimeDecay} = 0.97$.

$$\text{Base Score} = 0.24 + 0.34 + 0.06 = 0.64$$
$$\mathbf{Final Score} = 0.64 \times 0.97 = \mathbf{0.621}$$

Since $\mathbf{0.621} \ge 0.25$ threshold: **MATCH CONFIRMED (CORRELATED)**. The email is attached to Investigation #1!

---

## 🎯 7. Platform-Specific Correlation Intelligence

### 7.1 Slack Correlation Engine (Implemented ✅)

Slack has the most sophisticated correlation pipeline with 3 layers:

```
 [Incoming Slack Event]
        │
        ▼
 ┌───────────────────────┐
 │  Layer 1: LLM Intel   │  GPT-4o-mini classifies text into signal_type + urgency
 │  classify_slack_signal │  (~$0.000018/call, ~300ms, JSON response format)
 └──────────┬────────────┘
            │
            ▼
 ┌───────────────────────┐
 │  Layer 2: Lifecycle   │  Edits → update MongoDB record in-place
 │  handle_slack_edit    │  Deletes → mark as [RETRACTED]
 │  handle_slack_delete  │
 └──────────┬────────────┘
            │
            ▼
 ┌───────────────────────┐
 │  Layer 3: Deterministic│  Thread replies → O(1) parent lookup via thread_ts
 │  correlate_slack_thread│  Returns parent investigation_id
 └──────────┬────────────┘
            │ (No thread match)
            ▼
 [Falls through to Step 4: Hybrid Correlation Engine]
```

**Key Capabilities**:
* **LLM Signal Intelligence**: Every Slack message classified by GPT-4o-mini with heuristic fallback.
* **Deterministic Thread Correlation**: Thread replies link to parent investigation in O(1).
* **Evidence Mutation**: Edits update, deletions retract existing MongoDB records.
* **User/Channel Resolution**: Opaque Slack IDs resolved to human-readable names with in-memory caching.

### 7.2 Jira Correlation Engine (Planned — Phase 2 🔜)

See Section 10: Jira Correlation Engine Roadmap.

### 7.3 GitHub Correlation Engine (Implemented ✅)

GitHub uses the generic hybrid correlation engine (Step 4) with platform-specific noise filtering and incident-worthiness rules. Branch entity extraction (`fix/auth-gateway-oom` → `services: {"auth-gateway"}`) provides strong deterministic signal for entity matching.

### 7.4 Gmail Correlation Engine (Implemented ✅)

Gmail uses the generic hybrid correlation engine (Step 4) with operational sender detection and personal email filtering. Monitoring provider emails (`Datadog`, `Sentry`, `PagerDuty`) are incident-worthy; personal emails are stored as standalone evidence.

---

## 🔒 8. Authentication, Security & Cookie Architecture

### 1. Dual-Token Authentication Architecture:
* **Access Tokens**: Short-lived JWTs (15-minute expiration) passed via `Authorization: Bearer <token>` headers.
* **Refresh Tokens**: Long-lived JWTs (7-day expiration) stored in **`HttpOnly`**, **`SameSite=Lax`** cookies (`refresh_token`).

### 2. Silent Refresh Token Interceptor (`frontend/src/lib/api.ts`):
When an access token expires and an API call returns `401 Unauthorized`:
1. `api.ts` intercepts the response before logging out.
2. Automatically dispatches a background call to `POST /api/v1/auth/refresh` with `credentials: 'include'`.
3. Obtains a new 15-minute access token, updates the Zustand auth store, and retries the original API request transparently without redirecting the user to the landing page.
4. Concurrent requests during a refresh are queued and retried automatically.

### 3. Credential Encryption (`credentials_encrypted`):
Integration OAuth tokens and client secrets are encrypted at rest using **Fernet (AES-128-CBC)** symmetric encryption derived from `SECRET_KEY`. Raw OAuth credentials are never stored in plain text.

---

## 🎨 9. Frontend Architecture & User Interface Design

The frontend follows a **Linear / Palantir-inspired high-density operational light theme**:

### Key Components:
1. **Attention Deck Dashboard (`/dashboard`)**:
   * Triage view displaying **Threatened Business Targets**, active investigation metrics, and the **Active Signal Stream**.
2. **Integrations Page (`/integrations`)**:
   * 4 integration cards: **Slack**, **Jira**, **GitHub**, **Gmail**.
   * 1-click OAuth popup connection for all platforms.
   * Expandable drawer configurations:
     - **Slack**: Dynamic channel list from Slack API, multi-channel checkbox selection.
     - **Jira**: Text input for tracked project keys (dynamic project list planned).
     - **GitHub**: Dynamic repo list from GitHub API, multi-repo checkbox selection.
     - **Gmail**: Opens `GmailSettingsModal` for triage rule configuration.
3. **Gmail Settings Modal (`GmailSettingsModal.tsx`)**:
   * 3-section configuration drawer:
     * **Section 1**: Allowed Senders & Domains + auto-complete suggestions.
     * **Section 2**: Keyword Rules + starter templates (`Database Outages`, `CI/CD Build Failures`, `Security Alerts`).
     * **Section 3**: Subject Rules (`Contains` & `Starts With`).
     * **Live Preview Panel**: Real-time signal matching preview against sample emails.
4. **Interactive Evidence Detail Modal (`EvidenceDetailModal.tsx`)**:
   * Formatted email & telemetry reader dialog.
   * Clicking any item in the Active Signal Stream or Evidence Feed opens full multiline email body payloads, sender avatars, timestamps, and structured metadata tags.

---

## 🚀 10. Jira Correlation Engine Roadmap (Status: ✅ COMPLETED & DEPLOYED)

The Jira correlation engine has been fully implemented across all **3 planned phases**, achieving complete feature parity with the Slack correlation engine:

### Phase 1: Issue-Key Deterministic Correlation (✅ COMPLETED)
* **Function**: `correlate_jira_issue_key()` inserted at Step 3.5.
* Performs O(1) MongoDB lookup for active evidence matching `metadata.issue_key`.
* Comments, attachments, worklogs, status changes, and deletions on `KAN-3` automatically link to the ticket's existing investigation container without hitting the hybrid scoring engine.

### Phase 2: Evidence Lifecycle (✅ COMPLETED)
* **Functions**: `handle_jira_comment_edit()`, `handle_jira_comment_delete()`, `handle_jira_issue_delete()`.
* Comment edits mutate existing MongoDB evidence in-place (`metadata.edited = True`).
* Comment deletions mark existing comment evidence as `[RETRACTED]`.
* Issue deletions mark ALL evidence records matching the issue key as `[RETRACTED]`.

### Phase 3: Intelligent Incident Routing (✅ COMPLETED)
* Replaced generic keyword scanning for Jira with structured metadata routing in `is_incident_worthy`.
* High/Highest priority issues or `Bug`/`Incident` issue types spawn NEW SQL investigation containers.
* Secondary activities (`Task`, `Story`, comments, worklogs, attachments) land in standalone evidence or deterministic correlation.

---

## 🧪 11. Database Isolation & Testing Workflow

### 1. Test Isolation:
* Automated testing executes against an isolated MongoDB database (`oip_mongo_test`) configured in `backend/app/core/config.py` when `ENVIRONMENT == "testing"`, keeping production evidence collections 100% intact.

### 2. Deduplication & 1-to-1 Platform Constraints:
* `IntegrationService.create_integration` enforces a 1-to-1 platform constraint per organization. If an integration already exists for `(organization_id, platform)`, it updates credentials in-place instead of creating duplicate database rows.

---

## 🔮 12. Phase 3 Roadmap: Enterprise Scale

* **Real-Time SSE / WebSocket Push**: Telemetry push architecture detailed in [`FUTURE_PLANS.md`](file:///Users/adhisharavind/Desktop/Service-Assistant/FUTURE_PLANS.md).
* **Asynchronous LLM Signal Clustering**: Background worker tasks utilizing LLMs to summarize multi-evidence investigation timelines into automated root-cause diagnoses.
* **Human Triage Feedback Loop**: Learning correlation weights dynamically based on operator actions (e.g. manually moving or splitting evidence items across investigations).
* **Cross-Platform Correlation Intelligence**: ✅ Implemented via Step 3.75 (`correlate_cross_platform_keys`).
* **Dynamic Jira Project List in UI**: Replace manual text input for tracked projects with dynamic project list fetched from Jira REST API (matching GitHub/Slack UI pattern).
