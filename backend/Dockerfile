# Build stage: install dependencies with uv
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY api/ ./api/
COPY alembic/ ./alembic/
COPY alembic.ini ./

RUN adduser --disabled-password --no-create-home appuser
USER appuser

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && uvicorn api.main:app --host 0.0.0.0 --port 8080 --proxy-headers --forwarded-allow-ips='*'"]
