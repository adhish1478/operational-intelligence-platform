# Operational Intelligence Platform - Backend Plan

This document outlines the architectural road map and plan for implementing the production-grade backend for the **Operational Intelligence Platform (OIP)**.

---

## 1. Objectives & Guidelines
* **Staff Engineer Role:** Act as the architect. Establish the structure, write interfaces, configurations, and documentation. Do *not* write complete business logic implementations.
* **Domain-Driven Scaffold:** Organize components around functional domains (e.g., `auth`, `users`) rather than technical layers.
* **Production-Grade Auth:** Ensure robust user onboarding, secure password hashing, role pre-allocation, tenant pre-allocation, and refresh token security.

---

## 2. Technical Stack
* **FastAPI:** High-performance async web framework for API endpoints.
* **PostgreSQL:** Primary relational database for transactional consistency and robust relational modeling.
* **SQLAlchemy 2.0:** Object Relational Mapper using modern, fully-typed 2.0 syntax (select statements, async session execution).
* **Alembic:** Database migration tool for version-controlling schema changes.
* **Pydantic v2:** Fast data validation and settings management.
* **Docker:** Standardized deployment and local development containers.

---

## 3. Phased Implementation Plan

### Phase 1: Authentication & Scaffolding (Current Phase)
* [x] Design backend directory structure and explain folder responsibilities.
* [x] Write configuration files (`pyproject.toml`, `docker-compose.yml`, `.env.example`, `Makefile`).
* [x] Formulate `BACKEND_PLAN.md` and `AUTH_DESIGN.md`.
* [ ] Initialize database connection layer (`db/session.py`) and Alembic migrations.
* [ ] Define `User` model with fields prepared for multi-tenancy and RBAC.
* [ ] Define Pydantic request/response schemas.
* [ ] Define JWT access/refresh token utility interfaces.
* [ ] Create router stubs for register, login, refresh, me, and logout.

### Phase 2: Core Domain Models & Scaffolding (Future)
* [ ] Introduce `Organization` entity (multi-tenancy preparation).
* [ ] Introduce `Role` and `Permission` entities (RBAC preparation).
* [ ] Implement migration schemas to link Users with Organizations.

### Phase 3: Operational Intelligence Modules (Future)
* [ ] Introduce `Investigation` domain (Attention Deck alerts).
* [ ] Introduce `Evidence` domain (aggregating Slack, Jira, GitHub integration data).
* [ ] Introduce `Integration` configuration and connection manager.
* [ ] Introduce `Report` generator.

### Phase 4: Event-Driven & Scalability Components (Future)
* [ ] Integrate Redis for caching and session invalidation.
* [ ] Integrate MongoDB for unstructured evidence payload storage.
* [ ] Integrate RabbitMQ/Kafka for asynchronous queue processing.
* [ ] Equip platform with agentic workflows.
