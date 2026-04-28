# Multi-stage Dockerfile using uv for dependency management
# Follows the pattern from Rob's Awesome Python Template

# ── Stage 1: uv installer ───────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.5 AS uv

# ── Stage 2: builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install uv binary
COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (better layer caching)
COPY pyproject.toml .python-version ./
COPY src/ ./src/

# Install production dependencies only into /app/.venv
RUN uv sync --no-dev --frozen

# ── Stage 3: production ─────────────────────────────────────────────────────
FROM python:3.12-slim AS production

# Create non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Copy alembic config and migrations
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Put venv on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

# Expose API port
EXPOSE 8000

CMD ["uvicorn", "payment_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
