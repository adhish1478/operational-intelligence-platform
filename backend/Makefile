.PHONY: help install db-start db-stop db-shell migrate-generate migrate-apply migrate-rollback run test lint format

# Default action
help:
	@echo "OIP Backend Development Tooling:"
	@echo "  install          - Setup local virtual environment and install packages"
	@echo "  db-start         - Start local PostgreSQL via Docker Compose"
	@echo "  db-stop          - Shut down local PostgreSQL container"
	@echo "  db-shell         - Access the Postgres interactive shell inside Docker"
	@echo "  migrate-generate - Create a new Alembic migration stub. Usage: make migrate-generate msg=\"migration_message\""
	@echo "  migrate-apply    - Apply all pending database migrations"
	@echo "  migrate-rollback - Rollback the last applied database migration"
	@echo "  run              - Start the Uvicorn web server locally"
	@echo "  test             - Run backend test suite via Pytest"
	@echo "  lint             - Check code quality issues via Ruff"
	@echo "  format           - Format python code automatically via Ruff"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e .

db-start:
	docker compose up -d db

db-stop:
	docker compose down

db-shell:
	docker compose exec db psql -U postgres -d oip_db

migrate-generate:
	docker compose run --rm web alembic revision --autogenerate -m "$(msg)"

migrate-apply:
	docker compose run --rm web alembic upgrade head

migrate-rollback:
	docker compose run --rm web alembic downgrade -1

run:
	docker compose up --build web

test:
	docker compose run --rm web pytest

lint:
	docker compose run --rm web ruff check app tests

format:
	docker compose run --rm web ruff format app tests
