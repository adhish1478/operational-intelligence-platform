# Backend Implementation Plan & Roadmap

This document is the **single source of truth** for all backend development. It details the technical steps, database migrations, logic implementation, testing, and deployment checks required to complete the backend service.

---

## Completion scorecard

*   **Phase 0 - Foundation:** 100%
*   **Phase 1 - Organizations & Multi-Tenancy:** 50%
*   **Phase 2 - Investigations:** 0%
*   **Phase 3 - Evidence:** 0%
*   **Phase 4 - Integrations:** 0%
*   **Phase 5 - Webhook Ingestion:** 0%
*   **Phase 6 - Diagnosis Engine:** 0%
*   **Phase 7 - Reporting:** 0%
*   **Phase 8 - Production Readiness:** 0%

---

## Phase 0 - Foundation (100%)

*   **Goal:** Establish an asynchronous API framework, relational database connection, configuration system, container configuration, and secure session management.
*   **Why it exists:** Provides the core web server, transactional baseline, and baseline security before domain-specific tables and routes are introduced.
*   **Dependencies:** None
*   **Checklist:**
    *   [x] Set up FastAPI web application with CORS middleware and health checks.
    *   [x] Configure environment variables and settings using Pydantic Settings v2.
    *   [x] Set up SQLAlchemy 2.0 asynchronous connection engine and pooling rules.
    *   [x] Scaffold Alembic for version-controlled database migrations.
    *   [x] Implement User database model, indices, and timezone-aware timestamps.
    *   [x] Create Pydantic validation schemas for user registration, login, and tokens.
    *   [x] Program password hashing and verification using `bcrypt`.
    *   [x] Implement secure JWT-based authentication (15m Access Token, 7d HTTP-only Refresh Token).
    *   [x] Implement Refresh Token Rotation (RTR) on `/auth/refresh` requests to secure client sessions.
    *   [x] Set up global API dependency helpers (`DBSessionDep`, `TokenDep`, `CurrentUserDep`).
    *   [x] Configure Dockerfile and docker-compose.yml for local Postgres execution.
    *   [x] Write integration tests (8/8 cases passing) validating the entire auth lifecycle with transactional rollbacks.

---

## Phase 1 - Organizations & Multi-Tenancy (50%)

*   **Goal:** Establish tenant isolation boundaries to isolate users, memberships, investigations, and integrations into Organizations.
*   **Why it exists:** Multi-tenancy prevents cross-tenant data leaks. Access controls are scoped strictly to the organization to which a user belongs.
*   **Dependencies:** Phase 0
*   **Checklist:**
    *   [x] Design `Organization` database model (`id`, `name`, `slug`, `created_at`).
    *   [x] Design `Membership` association model (`id`, `user_id`, `organization_id`, `role`, `created_at`).
    *   [x] Link users to memberships in the authentication models.
    *   [x] Write Alembic migration to create organizations and memberships tables.
    *   [ ] Implement database CRUD operations in `organizations/services.py` (get by ID, get by slug, list, create, invite/add member, update role, remove member).
    *   [ ] Implement a global `ActiveOrganizationDep` FastAPI dependency to extract, validate, and inject the current organization tenant boundary using the `X-Organization-ID` header.
    *   [ ] Connect service methods to API route handlers in `organizations/routes.py`.
    *   [ ] Add integration test coverage validating tenant isolation (e.g., User A cannot view Organization B's details).

---

## Phase 2 - Investigations (0%)

*   **Goal:** Build the CRUD functionality for managing active incident containers (Investigations) displayed on the Attention Deck.
*   **Why it exists:** Investigations are the primary workflow entities. Users need APIs to search, list, assign, and transition incident states.
*   **Dependencies:** Phase 1
*   **Checklist:**
    *   [ ] Design `Investigation` database model (`id`, `organization_id`, `title`, `description`, `severity`, `status`, `assigned_to_id`, `suggested_action`, `detected_at`).
    *   [ ] Write Alembic migration creating the investigations table with foreign keys referencing users and organizations.
    *   [ ] Create Pydantic schemas for payload validation and API output representation.
    *   [ ] Implement API routes for `/api/v1/investigations` (list queue, get by ID, create manually, update status/assignee).
    *   [ ] Enforce tenant boundary checks: users can only fetch investigations belonging to their active organization.
    *   [ ] Write integration tests for investigation creation, status transition, and tenant boundary enforcement.

---

## Phase 3 - Evidence (0%)

*   **Goal:** Create database models and APIs allowing users to link external resources (Slack transcripts, Git diffs, Jira links) to active investigations.
*   **Why it exists:** Investigations require diagnostic context. Users must be able to view a chronological feed of evidence.
*   **Dependencies:** Phase 2
*   **Checklist:**
    *   [ ] Design `Evidence` database model (`id`, `investigation_id`, `type`, `summary`, `author_name`, `source_url`, `metadata` [using PostgreSQL `JSONB` for unstructured payloads], `created_at`).
    *   [ ] Write Alembic migration creating the evidence table linked to investigations.
    *   [ ] Create Pydantic schemas for reading and manual creation of evidence.
    *   [ ] Implement endpoint routes: `POST /api/v1/investigations/{id}/evidence` (append evidence) and `GET /api/v1/investigations/{id}/evidence` (retrieve chronological evidence feed).
    *   [ ] Add integration test coverage validating evidence attachment and verification.

---

## Phase 4 - Integrations (0%)

*   **Goal:** Create administrative configurations for connecting Slack workspaces, Jira projects, and GitHub repositories.
*   **Why it exists:** Integrations are the source of incoming evidence. The backend must store credentials/tokens securely.
*   **Dependencies:** Phase 1
*   **Checklist:**
    *   [ ] Design `Integration` database model (`id`, `organization_id`, `platform`, `credentials_encrypted`, `status`, `last_synced_at`).
    *   [ ] Write Alembic migration to create the integrations configuration table.
    *   [ ] Program a secure helper class using cryptography modules (e.g. `cryptography.fernet`) to encrypt/decrypt integration secrets.
    *   [ ] Implement API routes for `/api/v1/integrations` (list connections, create connection, test connection, disconnect).
    *   [ ] Write tests verifying integration credential encryption/decryption cycles and route security.

---

## Phase 5 - Webhook Ingestion (0%)

*   **Goal:** Create public API endpoints capable of receiving alert/commit payloads from Slack, Jira, and GitHub webhooks.
*   **Why it exists:** Webhooks push raw incident contexts into the system automatically. The backend needs to listen to external events and match them to investigations.
*   **Dependencies:** Phase 4
*   **Checklist:**
    *   [ ] Implement public route `/api/v1/ingest/{integration_id}` accepting dynamic JSON payloads.
    *   [ ] Write correlation logic: inspect payload for markers (e.g., email, project name, customer tag) to find active investigations.
    *   [ ] Correlation Logic: If a match is found, append the payload directly as new `Evidence`. If there is a mismatch or no active investigation, create a new `Investigation` and link it.
    *   [ ] Add tests simulating Slack webhook alerts, verifying they create/update investigations correctly.

---

## Phase 6 - Diagnosis Engine (0%)

*   **Goal:** Build a manual "Run Diagnosis" helper utilizing a simple LLM prompt template to analyze evidence.
*   **Why it exists:** Replaces complex agent graphs with a highly reliable, single-prompt diagnostic summary.
*   **Dependencies:** Phase 3
*   **Checklist:**
    *   [ ] Setup basic integration client with a popular LLM provider (e.g., OpenAI or Anthropic SDK).
    *   [ ] Design `Diagnosis` database model (`id`, `investigation_id`, `triggered_by_id`, `report_summary`, `created_at`).
    *   [ ] Write Alembic migration to create the diagnoses table.
    *   [ ] Create route `POST /api/v1/investigations/{id}/diagnose` that pulls all linked evidence, constructs a single system prompt, calls the LLM, saves the result, and updates the investigation's `suggested_action`.
    *   [ ] Add test suite mocking LLM API calls, verifying reports are compiled and saved.

---

## Phase 7 - Reporting (0%)

*   **Goal:** Implement simple Weekly digests of incidents and SLA statuses.
*   **Why it exists:** Operations managers need to summarize weekly performance and SLA breaches for team leadership.
*   **Dependencies:** Phase 2
*   **Checklist:**
    *   [ ] Implement API route `GET /api/v1/reports/digest` that aggregates active/resolved investigation metrics, SLA warnings, and category distributions.
    *   [ ] Add basic CSV/JSON exporter formatting.
    *   [ ] Add tests verifying aggregate calculations are mathematically accurate.

---

## Phase 8 - Production Readiness (0%)

*   **Goal:** Harden security, prepare credentials storage, optimize database, and run system validation checks.
*   **Why it exists:** Transitioning from local development to production hosting requires securing credentials and optimizing databases.
*   **Dependencies:** Phase 7
*   **Checklist:**
    *   [ ] Add a Redis or in-memory blocklist check inside `get_current_user` to invalidate access tokens on logout.
    *   [ ] Refactor settings to support secret injection from environments/vaults.
    *   [ ] Review database indexes on the `users`, `organizations`, `investigations`, and `evidence` tables.
    *   [ ] Run backend security checks via linting and safety scans.
    *   [ ] Execute the final system test suite to verify end-to-end functionality.
