# Multi-stage production-grade Dockerfile

# Stage 1: Build dependency wheelhouse
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Create dummy README so pip doesn't complain about missing package files if referenced
RUN touch README.md

# Install build dependencies to create wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r <(pip install pip-tools && pip-compile pyproject.toml --stdout)

# Stage 2: Final runner image
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Create application directories
RUN mkdir -p /app/app /app/alembic /app/docs

# Copy configuration and migration files
COPY pyproject.toml alembic.ini /app/
COPY alembic /app/alembic
COPY app /app/app

# Non-root user execution for security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10000 -g appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
