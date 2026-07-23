# Technical Architecture & System Specification: Operational Intelligence Platform (OIP)

This document provides a line-by-line technical specification of the **Operational Intelligence Platform (OIP)** architecture. It is designed to serve as an exhaustive reference for system architects, detailing the **Evidence Correlation Engine**, **Filter Enforcement Pipelines**, **AI Forensics & Diagnosis Engine**, **Polyglot Database Schemas**, and **Closed-Loop Operational Action Controllers**.

---

## 1. High-Level System Architecture & Event Pipeline

The platform uses an event-driven, polyglot persistence architecture. Incoming telemetry signals (webhooks from GitHub, Slack, Jira, and polling from Gmail) are validated, filtered, correlated, stored across dual databases (PostgreSQL + MongoDB), and analyzed by an LLM-powered incident diagnosis engine.

```mermaid
graph TD
    A[Telemetry Ingest: GitHub / Slack / Gmail / Jira] --> B[Ingest Filter Enforcer]
    B -- Ignored if untracked --> C[Reject: status=ignored]
    B -- Validated --> D[IngestService.correlate_and_process]
    
    D --> E[Keyword Extraction Engine]
    E --> F[Query Active SQL Investigations]
    
    F -- Keyword Match Found --> G[Attach to Existing SQL Investigation]
    F -- No Match Found --> H[Heuristic Severity Classifier]
    H --> I[Instantiate New SQL Investigation Container]
    
    G --> J[Store Document in MongoDB 'evidence' Collection]
    I --> J
    
    J --> K[AI Diagnosis Trigger: POST /investigations/{id}/diagnose]
    K --> L[Compile Chronological Evidence Timeline from MongoDB]
    L --> M[AsyncOpenAI GPT-4o Engine]
    M --> N[Save Diagnosis to PostgreSQL & Update suggestion_action]
    
    N --> O[Closed-Loop Action: Share to Slack / Escalate to Jira]
```

---

## 2. Polyglot Database Schemas & Data Layer

### 2.1. PostgreSQL Relational Model (SQLAlchemy 2.0 Async)

#### `organizations` & `memberships` & `users`
*   **Tenant Scoping**: All tenant models inherit or reference `organization_id: Mapped[uuid.UUID]`.
*   **Security Dependencies**: `ActiveOrganizationDep` parses `X-Organization-ID` header, querying `Membership` to enforce strict multi-tenant boundary isolation.

#### `integrations`
Stores integration connections, encrypted secret credentials, and unencrypted configuration parameters.
```python
class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # 'github', 'slack', 'gmail', 'jira'
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet Symmetric Encryption
    config: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)  # Unencrypted JSONB filtering rules
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

#### `investigations`
Primary incident container table.
```python
class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)  # 'critical', 'high', 'medium', 'low'
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)  # 'open', 'investigating', 'resolved'
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    suggestion_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

#### `diagnoses`
Persists LLM-generated forensic reports for audit trail analysis.
```python
class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    triggered_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    report_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### 2.2. MongoDB Unstructured Evidence Collection (`evidence`)

Stores high-throughput telemetry signals attached to specific `investigation_id` UUID strings:
```json
{
  "_id": "uuid-string-primary-key",
  "investigation_id": "investigation-uuid-string",
  "type": "slack | github | gmail | jira | alert",
  "summary": "String title or commit message summary",
  "author_name": "Author / Bot Username",
  "source_url": "HTTPS deep link to commit / message / ticket",
  "metadata": {
    "channel_id": "C12345",
    "commit_sha": "a8b32c",
    "repository": "org/repo",
    "raw_headers": {}
  },
  "created_at": "ISODate timestamp (UTC)"
}
```

---

## 3. DEEP DIVE: Evidence Matching & Correlation Engine (`IngestService`)

The **Correlation & Matching Engine** (`app/ingest/services.py`) processes all incoming platform payloads. It executes in 5 sequential stages:

```
[Raw Ingest Payload]
         │
         ▼
 1. Filter Enforcer ──(Untracked Repo / Channel)──► [REJECT: status="ignored"]
         │
         ▼ (Passed)
 2. Payload Parser & Normalizer
         │
         ▼
 3. Tokenizer & Stop-Word Keyword Extractor
         │
         ▼
 4. Active Investigation Intersect Query
         │
         ├───────────────────────────────┐
         ▼ (Match Found)                 ▼ (No Match Found)
 5a. Route Evidence to Existing   5b. Heuristic Severity Classifier
     Investigation Container            │
                                        ▼
                                  Instantiate New SQL Investigation
                                        │
                                        ▼
                                  Route Evidence to New Container
```

### Stage 1: Integration Filter Enforcement
Before processing payload text, `IngestService.correlate_and_process` checks integration `config` rules stored in PostgreSQL:
* **GitHub**: Validates `raw_payload.repository.full_name` against `integration.config.get("tracked_repos", [])`. If not found ➔ Returns `{"status": "ignored", "reason": "Repository not tracked"}`.
* **Slack**: Validates `raw_payload.event.channel` against `integration.config.get("channel_id")`. If mismatch ➔ Returns `{"status": "ignored", "reason": "Channel mismatch"}`.
* **Gmail**: Polled messages are filtered by `integration.config.get("search_query")`.

### Stage 2: Payload Parsing & Normalization
`IngestService.parse_webhook_payload` extracts standardized fields (`type`, `summary`, `author_name`, `source_url`, `metadata`) regardless of origin:
```python
if platform == "slack":
    event = payload.get("event", {})
    text = event.get("text", "")
    summary = f"Slack Alert: {text[:100]}..." if len(text) > 100 else f"Slack Alert: {text}"
    author_name = event.get("user")
elif platform == "github":
    commit = payload.get("head_commit", {})
    msg = commit.get("message", "")
    summary = f"GitHub Commit: {msg[:100]}..."
    author_name = commit.get("author", {}).get("username")
    source_url = commit.get("url")
elif platform == "jira":
    issue = payload.get("issue", {})
    key = issue.get("key", "JIRA-KEY")
    summary = f"Jira Issue {key}: {issue.get('fields', {}).get('summary')}"
elif platform == "gmail":
    email = payload.get("email", {})
    summary = f"Gmail Alert: {email.get('subject')}"
```

### Stage 3: Tokenization & Keyword Extraction Algorithm
`IngestService.extract_keywords(text)` extracts unique semantic tokens while filtering out common English and domain stop-words:
```python
def extract_keywords(text: str) -> set[str]:
    if not text:
        return set()
    # Match all words with length >= 3
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    stop_words = {
        "the", "and", "for", "from", "with", "this", "that", "alert", 
        "error", "sentry", "github", "slack", "jira", "gmail", "message", 
        "commit", "issue", "incident", "outage", "broken", "failed"
    }
    return {word for word in words if word not in stop_words}
```

### Stage 4: Set Intersection Matching against Active Tenant Investigations
1. Queries PostgreSQL for active investigations matching the organization:
   ```python
   statement = select(Investigation).where(
       Investigation.organization_id == integration.organization_id,
       Investigation.status.in_(["open", "investigating"])
   )
   active_investigations = (await db.execute(statement)).scalars().all()
   ```
2. Compares token set intersection:
   ```python
   incoming_keywords = extract_keywords(parsed["summary"])
   matched_investigation = None

   for inv in active_investigations:
       inv_keywords = extract_keywords(inv.title)
       overlap = inv_keywords.intersection(incoming_keywords)
       if len(overlap) > 0:
           matched_investigation = inv
           break
   ```

### Stage 5: Routing & Auto-Instantiation Logic
* **If `matched_investigation` exists**:
  Appends evidence directly to MongoDB under `matched_investigation.id`.
  Returns `{"status": "correlated", "investigation_id": matched_investigation.id}`.
* **If NO match exists**:
  1. Executes **Heuristic Severity Classification**:
     ```python
     severity = "medium"
     lower_summary = parsed["summary"].lower()
     if "critical" in lower_summary or "outage" in lower_summary or "severity 1" in lower_summary:
         severity = "critical"
     elif "error" in lower_summary or "failed" in lower_summary or "spiked" in lower_summary or "leak" in lower_summary:
         severity = "high"
     ```
  2. Instantiates a new PostgreSQL `Investigation` container:
     ```python
     new_inv = Investigation(
         organization_id=integration.organization_id,
         title=parsed["summary"],
         description=f"Auto-created from incoming {integration.platform} webhook payload.",
         severity=severity,
         status="open"
     )
     db.add(new_inv)
     await db.commit()
     ```
  3. Inserts the initial evidence log into MongoDB attached to `new_inv.id`.
  4. Returns `{"status": "created", "investigation_id": new_inv.id}`.

---

## 4. DEEP DIVE: AI Forensic Diagnosis Engine (`DiagnosisService`)

Triggered via `POST /api/v1/investigations/{id}/diagnose`, the AI Diagnosis Engine synthesizes cross-platform evidence feeds into structured root-cause analysis.

### Step 1: MongoDB Chronological Timeline Compilation
Queries MongoDB for all evidence linked to the investigation ID, sorted ascending by `created_at`:
```python
evidence_list = await EvidenceService.list_investigation_evidence(mongo_db, investigation.id)

timeline = ""
for idx, ev in enumerate(evidence_list, 1):
    timeline += f"{idx}. [{ev.created_at.isoformat()}] Platform: {ev.type} | Author: {ev.author_name} | Summary: {ev.summary}\n"
    if ev.source_url:
        timeline += f"   URL: {ev.source_url}\n"
    timeline += f"   Raw Details: {ev.metadata}\n\n"
```

### Step 2: System Prompt Engineering & Context Injection
```python
system_prompt = (
    "You are Antigravity, an expert Operations Incident Diagnosis Engine.\n"
    "Analyze the provided chronological timeline of evidence logs for an incident investigation.\n"
    "Generate a concise, professional diagnosis report outlining:\n"
    "1. Root cause summary\n"
    "2. Timeline analysis\n"
    "3. Actionable next steps and recommendations.\n"
    "Limit your response to 300 words. Keep it highly operational."
)

user_content = (
    f"Investigation Title: {investigation.title}\n"
    f"Investigation Description: {investigation.description}\n\n"
    f"Chronological Evidence Timeline:\n{timeline}"
)
```

### Step 3: LLM Execution & Graceful Fallback System
Uses `AsyncOpenAI` querying `gpt-4o` with low temperature (`0.2`) for deterministic, operational reports:
```python
if settings.OPENAI_API_KEY:
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        completion = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=500,
            temperature=0.2
        )
        report_summary = completion.choices[0].message.content or ""
    except Exception as e:
        report_summary = f"[AI Engine Exception, fallback report generated]\nRoot Cause: {investigation.title}. Details: {str(e)}"

if not report_summary:
    report_summary = (
        f"--- DIAGNOSIS REPORT FOR: {investigation.title} ---\n"
        f"Root Cause: Multiple system failure alerts detected.\n"
        f"Evidence Summary: Found {len(evidence_list)} logs spanning platforms.\n"
        f"Recommendation: Review error logs and trace resource exhaustion bottlenecks."
    )
```

### Step 4: SQL State Update & Persistence
1. Inserts new `Diagnosis` row in PostgreSQL.
2. Updates `investigation.status = "investigating"`.
3. Sets `investigation.suggestion_action = report_summary`.
4. Commits SQL transaction and returns `DiagnosisRead` payload.

---

## 5. Closed-Loop Operational Escalation Handlers

### 5.1. Share to Slack (`POST /api/v1/investigations/{id}/share-slack`)
1. Validates tenant access & verifies latest `Diagnosis` report exists.
2. Retrieves active `slack` integration for the organization.
3. Decrypts Fernet credentials to extract `access_token`.
4. Reads `channel_id` from `integration.config`.
5. Formats Slack Block / Markdown alert payload:
   ```python
   text_content = (
       f"🚨 *Incident Escalation Alert: {investigation.title}*\n"
       f"Severity: `{investigation.severity.upper()}` | Status: `{investigation.status.upper()}`\n\n"
       f"*AI Diagnosis & Root Cause Summary:*\n"
       f"{latest_diagnosis.report_summary}\n"
   )
   ```
6. Sends HTTP POST to `https://slack.com/api/chat.postMessage`.
7. Returns `{"status": "success", "channel": channel_name}`.

### 5.2. Escalate to Jira (`POST /api/v1/investigations/{id}/escalate-jira`)
1. Validates tenant access & verifies latest `Diagnosis` report exists.
2. Retrieves active `jira` integration & decrypts `host_url`, `email`, and `api_token`.
3. Reads first key from `integration.config["tracked_projects"]` (defaults to `"PROD"`).
4. Constructs Atlassian Document Format (ADF) JSON payload:
   ```python
   jira_payload = {
       "fields": {
           "project": {"key": project_key},
           "summary": f"[OIP Alert] {investigation.title}",
           "description": {
               "type": "doc",
               "version": 1,
               "content": [{
                   "type": "paragraph",
                   "content": [{
                       "type": "text",
                       "text": f"Operational incident escalated from OIP.\n\nAI Diagnosis Report:\n{latest_diagnosis.report_summary}"
                   }]
               }]
           },
           "issuetype": {"name": "Task"}
       }
   }
   ```
5. Sends HTTP POST to `{host_url}/rest/api/3/issue` using Basic Auth (`auth=(email, api_token)`).
6. Parses response ticket key (e.g. `PROD-404`).
7. Appends ticket reference (`\n\n[Escalated to Jira ticket: PROD-404]`) to `investigation.suggestion_action` in SQL.
8. Returns `{"status": "success", "key": key, "url": ticket_url}`.

---

## 6. Background Gmail Sync Worker (`gmail_worker.py`)

Runs as a FastAPI lifespan task loop (`asyncio.create_task`):
```python
async def poll_gmail_for_all_integrations(db_factory, mongo_db):
    while True:
        try:
            # Query active Gmail integrations
            async with db_factory() as db:
                integrations = await get_active_gmail_integrations(db)
                for integration in integrations:
                    creds = decrypt_credentials(integration.credentials_encrypted)
                    access_token = creds.get("access_token")
                    refresh_token = creds.get("refresh_token")
                    query = integration.config.get("search_query", "is:unread label:alerts")

                    # Query Google Gmail Users API
                    response = await fetch_gmail_messages(access_token, query)

                    # Handle 401 Unauthorized via Refresh Token
                    if response.status_code == 401 and refresh_token:
                        new_access_token = await refresh_google_token(refresh_token)
                        # Save updated access token back to SQL encrypted credentials
                        integration.credentials_encrypted = encrypt_credentials({
                            "access_token": new_access_token,
                            "refresh_token": refresh_token
                        })
                        await db.commit()
                        response = await fetch_gmail_messages(new_access_token, query)

                    # Route unread emails through IngestService
                    for msg in response.json().get("messages", []):
                        await IngestService.correlate_and_process(db, mongo_db, integration, raw_email_payload)
        except Exception:
            pass
        await asyncio.sleep(60)
```

---

## 7. Comprehensive Test Suite Inventory (`backend/tests/`)

| Test File | Verified Functionality |
| :--- | :--- |
| **`test_auth.py`** | User registration, login token generation, HttpOnly refresh cookie assertion. |
| **`test_ingestion.py`** | Ingest payload normalization, keyword extraction algorithm, set intersection correlation, auto-instantiation of SQL investigations, heuristic severity classification, and tracked repo/channel filter enforcement. |
| **`test_gmail_worker.py`** | Lifespan background task initialization, unread message processing, auto-token refresh on HTTP 401 responses. |
| **`test_jira.py`** | Direct Basic Auth verification (`/rest/api/3/myself`), project settings JSONB config updates. |
| **`test_investigations.py`** | Full investigation CRUD lifecycle, multi-tenant isolation header enforcement, Slack sharing route mocks (`/share-slack`), and Jira ticket escalation route mocks (`/escalate-jira`). |
| **`test_evidence.py`** | MongoDB document persistence, chronological evidence sorting, multi-tenant isolation, and global recent evidence stream query (`/evidence/recent`). |

---

*This specification document represents the exact implementation status of the Operational Intelligence Platform backend and core processing engines.*
