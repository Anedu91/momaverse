# Momaverse Backend

FastAPI backend for the Momaverse project.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Install

```bash
cd backend
uv sync
```

## Configure

Copy the example env file and edit as needed:

```bash
cp .env.example .env
```

## Pre-commit Hooks

Install the pre-commit hooks so ruff (linter + formatter) and mypy (type checker) run on every commit:

```bash
cd backend
uv run pre-commit install
```

To verify everything passes:

```bash
uv run pre-commit run --all-files
```

## Run

### API server

```bash
# Development (auto-reload on file changes)
uv run fastapi dev api/main.py

# Production
uv run fastapi run api/main.py
```

The API will be available at http://127.0.0.1:8000

- Swagger docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### Celery worker

The backend uses Celery for async tasks (geocoding, event processing). It requires a running Redis instance as the message broker.

```bash
# Start Redis (if not already running)
docker run -d --name redis -p 6379:6379 redis:7

# Start the Celery worker
uv run celery -A api.celery_app worker --loglevel=info
```

By default the worker connects to `redis://localhost:6379/0`. Override this by setting `REDIS_URL` in your `.env` file.

## Project Structure

```
backend/
├── api/
│   ├── __init__.py      # Package marker (required by fastapi dev)
│   ├── main.py          # FastAPI app, CORS, health endpoint
│   ├── config.py        # Settings via pydantic-settings
│   ├── database.py      # SQLAlchemy engine, session, Base
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   └── routers/         # API route modules
├── pipeline/            # Data pipeline modules
├── pyproject.toml       # Project config and dependencies
├── uv.lock              # Locked dependencies
├── .env                 # Local environment variables (gitignored)
└── .env.example         # Environment template
```
