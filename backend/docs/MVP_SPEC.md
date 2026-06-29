# MVP Product Specification

This document defines the strict Minimum Viable Product (MVP) boundary, database models, and API schemas required to build the core backend service of the **Operational Command Center**.

---

## 1. The Smallest Useful Version of the Product
The smallest useful version of this product is a **collaborative incident triage workspace**. It allows a user to sign up, join or create a team organization, view a unified list of active incidents (Investigations), view chronological details associated with those incidents (Evidence), run a one-click AI analysis (Diagnosis) to summarize the root cause, and resolve the incident.

---

## 2. Required Backend Modules
*   **`auth` (Authentication):** Handles user registration, credentials hashing (bcrypt), login session management, and Refresh Token Rotation (RTR).
*   **`organizations` (Tenancy):** Manages organizations and user memberships to enforce strict data isolation between tenants.
*   **`investigations` (Incident Containers):** Handles creation, listing, updating, and assigning active incident containers.
*   **`evidence` (Incident Context):** Stores and retrieves cross-platform payloads (Slack transcripts, Git diffs, Jira statuses) linked to an investigation.
*   **`diagnosis` (LLM Analysis):** Compiles evidence payloads, executes a single structured prompt to an LLM provider, and records the diagnostic summary.

---

## 3. Optional Backend Modules (Post-MVP)
*   **`integrations` (Marketplace):** Grid configuration endpoints for managing third-party connectors (can be mocked/manually loaded for MVP).
*   **`ingest` (Webhook Ingest Router):** Automatic webhook payload receivers for GitHub, Slack, and Jira (can be simulated via manual POST routes to `/evidence` endpoints in the MVP).
*   **`reports` (Executive Summaries):** Generates scheduled CSV/JSON digests for ops managers.

---

## 4. Required Database Tables
The PostgreSQL database requires exactly **five tables** to support the relational schema. MongoDB is excluded; unstructured JSON payloads are stored using Postgres `JSONB` columns.

### 4.1. `users`
*   `id`: `UUID` (PK, Indexed)
*   `email`: `VARCHAR(255)` (Unique, Indexed, Not Null)
*   `password_hash`: `VARCHAR(255)` (Not Null)
*   `first_name`: `VARCHAR(100)` (Nullable)
*   `last_name`: `VARCHAR(100)` (Nullable)
*   `is_active`: `BOOLEAN` (Default: `true`)
*   `created_at`: `TIMESTAMPTZ` (Default: `now()`)

### 4.2. `organizations`
*   `id`: `UUID` (PK, Indexed)
*   `name`: `VARCHAR(100)` (Not Null)
*   `slug`: `VARCHAR(100)` (Unique, Indexed, Not Null)
*   `created_at`: `TIMESTAMPTZ` (Default: `now()`)

### 4.3. `memberships`
*   `id`: `UUID` (PK, Indexed)
*   `user_id`: `UUID` (FK `users.id`, Cascade Delete)
*   `organization_id`: `UUID` (FK `organizations.id`, Cascade Delete)
*   `role`: `VARCHAR(50)` (Default: `"member"` - owner, admin, member, viewer)
*   `created_at`: `TIMESTAMPTZ` (Default: `now()`)

### 4.4. `investigations`
*   `id`: `UUID` (PK, Indexed)
*   `organization_id`: `UUID` (FK `organizations.id`, Cascade Delete)
*   `title`: `VARCHAR(255)` (Not Null)
*   `description`: `TEXT` (Nullable)
*   `severity`: `VARCHAR(50)` (Not Null - critical, high, medium, low)
*   `status`: `VARCHAR(50)` (Not Null - open, investigating, resolved)
*   `assigned_to_id`: `UUID` (FK `users.id`, Set Null, Nullable)
*   `suggested_action`: `TEXT` (Nullable)
*   `detected_at`: `TIMESTAMPTZ` (Default: `now()`)

### 4.5. `evidence`
*   `id`: `UUID` (PK, Indexed)
*   `investigation_id`: `UUID` (FK `investigations.id`, Cascade Delete)
*   `type`: `VARCHAR(50)` (Not Null - slack, github, jira, email, notion)
*   `summary`: `TEXT` (Not Null)
*   `author_name`: `VARCHAR(100)` (Nullable)
*   `source_url`: `VARCHAR(255)` (Nullable)
*   `metadata`: `JSONB` (Stores raw unstructured payloads like Git diff JSON, Slack threads)
*   `created_at`: `TIMESTAMPTZ` (Default: `now()`)

### 4.6. `diagnoses`
*   `id`: `UUID` (PK, Indexed)
*   `investigation_id`: `UUID` (FK `investigations.id`, Cascade Delete)
*   `triggered_by_id`: `UUID` (FK `users.id`, Set Null, Nullable)
*   `report_summary`: `TEXT` (Not Null)
*   `created_at`: `TIMESTAMPTZ` (Default: `now()`)

---

## 5. Minimum Core API Routes

### 5.1. Authentication Router (`/api/v1/auth`)
*   `POST /register` — Registers a user profile.
*   `POST /login` — Logs in credentials (returns access token, sets HttpOnly refresh cookie).
*   `POST /refresh` — Rotates access token and refresh cookie.
*   `GET /me` — Retrieves current user profile.
*   `POST /logout` — Clears cookies.

### 5.2. Organizations Router (`/api/v1/organizations`)
*   `POST /` — Creates a new Organization (creator is registered as `owner`).
*   `GET /` — Lists all organizations the authenticated user belongs to.
*   `GET /{org_id}/members` — Lists all members inside the organization.
*   `POST /{org_id}/members` — Invites/adds a member to the organization.
*   `PATCH /{org_id}/members/{user_id}` — Updates member role.
*   `DELETE /{org_id}/members/{user_id}` — Removes a member from the organization.


### 5.3. Investigations Router (`/api/v1/investigations`)
*   `GET /` — Lists active investigations (filtered by active tenant ID provided in `X-Organization-ID` header).
*   `POST /` — Manually creates a new investigation.
*   `GET /{id}` — Retrieves detailed investigation record.
*   `PATCH /{id}` — Updates investigation parameters (status, severity, assignee).

### 5.4. Evidence Router (`/api/v1/investigations/{id}/evidence`)
*   `GET /` — Retrieves chronological feed of evidence for the investigation.
*   `POST /` — Appends a new evidence record (simulates incoming integration webhook).

### 5.5. Diagnosis Router (`/api/v1/investigations/{id}/diagnose`)
*   `POST /` — Triggers LLM analysis of compiled evidence, creates a `diagnoses` record, and updates the parent investigation's `suggested_action`.

---

## 6. End-to-End User Workflow (Required Support)

1.  **Account Onboarding:** A user registers a new account, logs in, and creates an organization named `"Aero Corp"` (slug: `"aero-corp"`).
2.  **Incident Creation:** The user manually triggers a POST request simulating a critical incident: `"API Gateway Latency Spike"`, setting severity to `critical` and status to `open`.
3.  **Context Assembly:** The user makes two POST calls to the `/evidence` endpoint, appending:
    *   A Slack thread snippet discussing high memory usage.
    *   A GitHub commit payload modifying the API Gateway container limits.
4.  **Triage & Diagnostics:** The user navigates to the incident viewport and clicks **"Run Diagnosis"**. The backend gathers the Slack thread and GitHub commit context, constructs a single system prompt, requests a structured summary from the LLM, saves the result to the `diagnoses` table, and updates the investigation's `suggested_action` parameter to: `"Revert commit #89ac2 and scale container memory limit to 2GB."`
5.  **Resolution:** The user resolves the investigation.
