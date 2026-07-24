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
Our platform introduces a **5-Stage Ingestion Pipeline** powered by a **Multi-Phase Hybrid Correlation Engine** and a **Polyglot Persistence Model**. It filters noise, correlates cross-platform telemetry into active incident containers with high mathematical precision, and routes routine events into standalone evidence without polluting the operational incident dashboard.

---

## 💻 2. Technology Stack & Architectural Overview

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | **FastAPI (Python 3.11)** | High-performance asynchronous API & background worker processing |
| **Relational DB** | **PostgreSQL (SQLAlchemy 2.0 Async)** | Stores tenant organizations, user accounts, integration configs, and **`Investigations`** |
| **Document DB** | **MongoDB (Motor / PyMongo Async)** | Stores unstructured **`Evidence`** telemetry documents |
| **Frontend Framework** | **React 18 + TypeScript + Vite** | Single Page Application (SPA) with strong type safety |
| **State & Query** | **TanStack Query v5 + Zustand** | In-memory server cache management, optimistic updates, and global auth state |
| **Styling & UI** | **Tailwind CSS + Lucide Icons** | Linear / Palantir-inspired high-density operational light design system |
| **Security & Crypto** | **Fernet (Cryptography) + PyJWT** | AES-128-CBC credential encryption & JWT access/refresh token rotation |
| **AI / Embeddings** | **OpenAI API (`text-embedding-3-small`)** | 1536-dimensional semantic vector embeddings for cross-platform signal correlation |

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

## ⚙️ 4. The 5-Stage Ingestion Pipeline Architecture

Every incoming signal (polled via background worker every 60s or received via webhooks) flows through **5 sequential pipeline stages**:

```
 [Raw Event Payload]
        │
        ▼
 ┌───────────────┐
 │    Stage 1    │ ── (Fails Boundary Check?) ──► IGNORED (0 DB Writes)
 │ Platform      │
 │ Filter        │
 └──────┬────────┘
        │ (Passes)
        ▼
 ┌───────────────┐
 │    Stage 2    │ ──► Normalizes to uniform schema:
 │ Normalize     │     { summary, author_name, source_url, metadata.body }
 │ Payload       │
 └──────┬────────┘
        │
        ▼
 ┌───────────────┐
 │    Stage 3    │
 │ Signal/Noise  │ ── (Fails Rules?) ─────────► IGNORED (0 DB Writes)
 │ Classifier    │
 └──────┬────────┘
        │ (Is Valid Signal)
        ▼
 ┌───────────────┐
 │    Stage 4    │
 │ Correlation   │ ── (Score >= 0.25 Threshold) ──► CORRELATED (Attach Evidence to
 │ Engine        │                                  Existing Investigation in MongoDB)
 └──────┬────────┘
        │ (Uncorrelated: Score < 0.25)
        ▼
 ┌───────────────┐
 │    Stage 5    │
 │ Incident      ├──── (Incident Worthy?) ─────► CREATED (Spawn New SQL Investigation
 │ Worthiness    │                                + Link Evidence in MongoDB)
 │ & Routing     │
 └──────┬────────┴──── (Routine Event?) ───────► EVIDENCE_ONLY (Store in MongoDB with
                                                   investigation_id = null)
```

---

### Detailed Stage Specifications:

#### **Stage 1: Platform Filter (`platform_filter`)**
Validates workspace boundary criteria:
* **GitHub**: Checks if incoming repository (`repository.full_name`) matches `tracked_repos` in integration config.
* **Slack**: Checks if incoming channel matches `configured_channel_id`.
* **Jira**: Checks if project key matches `tracked_projects`.

#### **Stage 2: Payload Normalization (`normalize_payload`)**
Parses platform-specific JSON payloads into a uniform dictionary containing `summary`, `author_name`, `source_url`, and structured `metadata`:
* **Gmail**: Base64url decodes multiline email bodies (`body`), header subjects, and sender info.
* **GitHub Webhooks**:
  * `pull_request`: Title, head branch (`fix/auth-gateway-oom`), base branch (`main`), state (`opened`, `merged`), author, body text, and repo slug.
  * `workflow_run`: CI workflow name, conclusion (`failure`, `success`), head branch, build runner actor, and log URL.
  * `issues`: Issue number, title, body, and operational labels (`bug`, `P0`, `critical`, `blocker`).
  * `push`: Branch ref (`refs/heads/main`), commit message, committer, and repo slug.

#### **Stage 3: Signal / Noise Classifier (`classify_signal`)**
Evaluates user-configured triage settings using an **Inclusive OR Model**:
* **Trigger 1 (Allowed Senders)**: Is the sender email/domain in `allowed_senders`?
* **Trigger 2 (Subject Rules)**: Does the subject match `subject_contains` or `subject_starts_with`?
* **Trigger 3 (Keyword Rules)**: Does the body/summary contain any `required_keywords`?
* **GitHub Specific Noise Filtering**:
  * Drops `dependabot[bot]` PRs automatically.
  * Drops background maintenance branches: `chore/*`, `docs/*`, `style/*`, `renovate/*`.
  * Drops redundant `push` events to non-default PR branches (since the `pull_request` event lifecycle already tracks PR activity).

If **ANY** trigger matches, the event is classified as an operational **Signal**. If none match, it is dropped as **Noise** (`status: "ignored"`).

#### **Stage 4: Multi-Phase Correlation Engine (`correlate_signal`)**
Evaluates the incoming signal against active open investigations for the tenant (`status IN ('open', 'investigating')`) using our **Phase 2 Hybrid Scoring Model**:
$$\text{Score} = \Big( 0.40 \cdot \text{EntityScore} + 0.40 \cdot \text{VectorScore} + 0.20 \cdot \text{KeywordScore} \Big) \cdot \text{TimeDecay}$$
* **Branch Entity Priority**: Extracts microservice identifiers directly from branch patterns (`fix/auth-gateway-pod-12-oom` $\rightarrow$ `services: {"auth-gateway-pod-12"}`).
* If a candidate scores $\ge 0.25$, the evidence is attached directly to that existing investigation (`status: "correlated"`).

#### **Stage 5: Incident Worthiness & Storage Routing (`is_incident_worthy`)**
If Stage 4 returns no correlation match:
* **Gmail Incident-Worthy Events**:
  * **Operational System Monitoring Emails**: Emails from monitoring providers (`Datadog`, `Sentry`, `Grafana`, `Kubernetes`, `PagerDuty`, `CloudWatch`, `Prometheus`, `NewRelic`) or containing operational alert prefixes (`[ALERT]`, `[ERROR]`, `[CRITICAL]`, `incident`).
  * **User Configured Triage Rules**: Emails matching user-configured integration settings (`allowed_senders`, `subject_starts_with`, `subject_contains`, `required_keywords`).
  * **Result**: Spawns a new **PostgreSQL `Investigation` container** + attaches Evidence in MongoDB (`status: "created"`).
  * **Personal Email Filtering**: Personal bank transaction alerts (`ICICI`, `CRED`, `SBI`), newsletters (`The Economist`, `Medium`, `Anaconda`, `NVIDIA`), trading digests (`Groww`, `NSE`), and job alerts (`LinkedIn`, `Indeed`, `hirist`) are filtered out from auto-creating investigations and saved directly as **Standalone Evidence in MongoDB** (`investigation_id = null`, `status: "evidence_only"`).
* **GitHub Incident-Worthy Events**:
  * CI Workflow Failures (`workflow_run.failure`, `cancelled`, `timed_out`).
  * Issues labeled `bug`, `P0`, `critical`, or `blocker`.
  * PRs on incident branches (`bug/*`, `hotfix/*`, `bugfix/*`, `incident/*`) containing critical incident keywords (`critical`, `outage`, `error`, `failed`, `leak`, `crash`, `panic`, `fatal`, `p0`, `p1`).
  * **Result**: Spawns a new **PostgreSQL `Investigation` container** + attaches Evidence in MongoDB (`status: "created"`).
* **Routine Signals**:
  * Uncorrelated feature PRs (`feature/*`) or general emails are stored as **Standalone Evidence in MongoDB** (`investigation_id = null`, `status: "evidence_only"`), keeping PostgreSQL 100% clean.

---

## 🫀 5. Deep Dive: The Core Heart — Multi-Phase Correlation Engine

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

## 🔒 6. Authentication, Security & Cookie Architecture

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

## 🎨 7. Frontend Architecture & User Interface Design

The frontend follows a **Linear / Palantir-inspired high-density operational light theme**:

### Key Components:
1. **Attention Deck Dashboard (`/dashboard`)**:
   * Triage view displaying **Threatened Business Targets**, active investigation metrics, and the **Active Signal Stream**.
2. **Gmail Settings Modal (`GmailSettingsModal.tsx`)**:
   * 3-section configuration drawer:
     * **Section 1**: Allowed Senders & Domains + auto-complete suggestions.
     * **Section 2**: Keyword Rules + starter templates (`Database Outages`, `CI/CD Build Failures`, `Security Alerts`).
     * **Section 3**: Subject Rules (`Contains` & `Starts With`).
     * **Live Preview Panel**: Real-time signal matching preview against sample emails.
3. **Interactive Evidence Detail Modal (`EvidenceDetailModal.tsx`)**:
   * Formatted email & telemetry reader dialog.
   * Clicking any item in the Active Signal Stream or Evidence Feed opens full multiline email body payloads, sender avatars, timestamps, and structured metadata tags.

---

## 🧪 8. Database Isolation & Testing Workflow

### 1. Test Isolation:
* Automated testing executes against an isolated MongoDB database (`oip_mongo_test`) configured in `backend/app/core/config.py` when `ENVIRONMENT == "testing"`, keeping production evidence collections 100% intact.

### 2. Deduplication & 1-to-1 Platform Constraints:
* `IntegrationService.create_integration` enforces a 1-to-1 platform constraint per organization. If an integration already exists for `(organization_id, platform)`, it updates credentials in-place instead of creating duplicate database rows.

---

## 🔮 9. Phase 3 Roadmap: Enterprise Scale

* **Asynchronous LLM Signal Clustering**: Background worker tasks utilizing LLMs to summarize multi-evidence investigation timelines into automated root-cause diagnoses.
* **Human Triage Feedback Loop**: Learning correlation weights dynamically based on operator actions (e.g. manually moving or splitting evidence items across investigations).
