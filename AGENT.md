# Agent Development Workflow & Conventions

This document defines the permanent development workflow, coding standards, and architectural rules for AI agents operating in this repository.

---

## 1. Project Goal

This project is an **Operational Intelligence Platform (OIP)**. The objective is to build a high-fidelity, realistic SaaS product, not a technology showcase. 
*   Always prefer simpler, standard software architectures over complex ones.
*   Avoid unnecessary components, microservices, or external network dependencies unless absolutely required.

---

## 2. Source of Truth

The agent **must always consult**:
*   [backend/docs/BACKEND_PLAN.md](file:///Users/adhisharavind/Desktop/Service-Assistant/backend/docs/BACKEND_PLAN.md)

before starting or implementing any backend feature.
*   **No Arbitrary Implementation:** Never invent new phases or implement features out of order.
*   **Sequence Integrity:** Never skip phases. Never implement future phases before the current phase is 100% complete unless explicitly instructed by the user.

---

## 3. Development Workflow

For every feature or task, follow this exact workflow:

1.  **Read and Sync:** Read [backend/docs/BACKEND_PLAN.md](file:///Users/adhisharavind/Desktop/Service-Assistant/backend/docs/BACKEND_PLAN.md) to locate the active task/phase.
2.  **Branching:** Create a new feature branch.
    *   **Naming Convention:** `feature/<name>`
    *   *Examples:* `feature/auth`, `feature/organizations`, `feature/investigations`, `feature/evidence`
3.  **One Iteration, One Phase:** Never implement multiple phases in one iteration. Each pull request should complete exactly one coherent feature so that it is independently reviewable and deployable.
    *   *Examples of coherent features:* Organization Module, Membership Module, Investigation Module, Evidence Module, Integration Module.
4.  **Implementation:** Implement the code within the specific files, adhering to existing patterns.
5.  **Validation:** Run all relevant validation checks (tests, linter, formatting, build, db migrations).
    *   *Examples:* `pytest`, linting rules, schema validations.
6.  **Fix Failures:** Fix any errors found during validation.
7.  **Update Documentation:** Update the respective documentation files if changes occurred:
    *   Update progress checks inside [backend/docs/BACKEND_PLAN.md](file:///Users/adhisharavind/Desktop/Service-Assistant/backend/docs/BACKEND_PLAN.md).
    *   Update [backend/docs/API_REFERENCE.md](file:///Users/adhisharavind/Desktop/Service-Assistant/backend/docs/API_REFERENCE.md) (if APIs or routes were changed).
    *   Update [backend/docs/ARCHITECTURE.md](file:///Users/adhisharavind/Desktop/Service-Assistant/backend/docs/ARCHITECTURE.md) (if DB tables, models, or layouts changed).
8.  **Commit:** Commit your changes using **Conventional Commits** (e.g., `feat(auth): add email validation check`).
9.  **Push:** Push the feature branch to the remote repository.
10. **Pull Request:** Create a Pull Request.

> [!IMPORTANT]
> **Never merge branches directly into `main`.** The human developer will review your Pull Request and merge it manually.


---

## 4. Coding Standards

*   **Logic Isolation:** Keep business logic inside service files (e.g., `services.py`). Do not pollute route controllers with DB queries or domain logic.
*   **Thin Controllers:** Keep API routers/endpoints thin. They should focus on request parameters parsing, schema validations, and calling service layer operations.
*   **Strong Typing:** Keep all Pydantic schemas, Python variables, and function signatures strongly typed.
*   **Module Isolation:** Keep modules decoupled. Avoid circular imports and tightly coupled models.
*   **No Duplicated Logic:** Reuse existing helper functions and classes.
*   **Production Code:** No placeholders, mock values, or dummy responses in target files unless explicitly requested.
*   **Clean Codebase:** Do not add `TODO` comments unless explicitly instructed.

---

## 5. Architecture Rules

Do not introduce new technologies or infrastructure layers simply because they are popular. 

Before proposing any of the following:
*   **Event Streams / Message Brokers:** Kafka, RabbitMQ
*   **Databases:** MongoDB, Redis, Elasticsearch
*   **Job Queues:** Celery
*   **Agent Orchestration:** LangGraph, CrewAI

You must explain:
1.  What specific architectural problem it solves.
2.  Why the existing database or server structures (e.g., PostgreSQL JSONB, FastAPI BackgroundTasks) are insufficient.
3.  Why this technology is the best choice compared to lightweight alternatives.

> [!CAUTION]
> **Do not implement or add dependencies for these technologies without explicit human developer approval.**

---

## 6. Documentation Rules

*   **No Temporary Files:** Do not create temporary scratch markdown files in the documentation directories.
*   **Keep it Minimal:** Keep descriptions dense and functional.
*   **Single Roadmap:** [backend/docs/BACKEND_PLAN.md](file:///Users/adhisharavind/Desktop/Service-Assistant/backend/docs/BACKEND_PLAN.md) is the only active backend roadmap. No other backend plans or roadmaps should exist.

---

## 7. Definition of Done

A backend feature is marked as complete **only when**:
1.  Implementation is fully finished (no placeholders).
2.  All unit and integration tests pass successfully.
3.  Documentation matches the current codebase state.
4.  Checklists inside [backend/docs/BACKEND_PLAN.md](file:///Users/adhisharavind/Desktop/Service-Assistant/backend/docs/BACKEND_PLAN.md) are checked and the completion % is updated.
5.  All files are committed using Conventional Commits.
6.  The feature branch is pushed to origin.
7.  A Pull Request is opened for review.

---

## 8. General Philosophy

*   **Priorities:** Correctness > Maintainability > Readability > Incremental delivery.
*   **Minimize Overengineering:** Always choose the smallest, simplest, and cleanest implementation that fully satisfies the current product requirements.
