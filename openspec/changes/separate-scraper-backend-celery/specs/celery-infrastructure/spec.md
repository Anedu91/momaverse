## ADDED Requirements

### Requirement: Celery app configuration
The system SHALL have a single Celery application defined in `backend/api/celery_app.py` that configures the broker (Redis), result backend, serialization (JSON), and task routing for two queues: `default` and `geocoding`.

#### Scenario: Celery app initializes with Redis broker
- **WHEN** the Celery app is imported
- **THEN** it connects to the Redis broker using the `REDIS_URL` environment variable
- **THEN** it uses JSON serialization for tasks and results
- **THEN** it routes tasks prefixed with `geocode_` to the `geocoding` queue and all others to `default`

#### Scenario: Celery app works without backend running
- **WHEN** the scraper imports the Celery config to publish tasks
- **THEN** it SHALL only need the broker URL and task names — no FastAPI or SQLAlchemy imports required

### Requirement: Shared task name constants
The system SHALL define task name constants in a lightweight module (`backend/api/celery_tasks.py` or similar) that both the scraper and backend can reference without importing the full backend.

#### Scenario: Scraper sends task by name
- **WHEN** the scraper finishes a crawl job
- **THEN** it publishes a task using `celery_app.send_task(PROCESS_CRAWL_JOB, args=[job_id])` without importing the task function itself

### Requirement: Celery worker entrypoint
The system SHALL provide a worker entrypoint that starts the Celery worker consuming from both `default` and `geocoding` queues.

#### Scenario: Worker starts and discovers tasks
- **WHEN** the worker is started via `celery -A backend.api.celery_app worker`
- **THEN** it discovers and registers all task functions from the backend
- **THEN** it consumes from both `default` and `geocoding` queues

#### Scenario: Worker can be started for a single queue
- **WHEN** the worker is started with `celery -A backend.api.celery_app worker -Q geocoding`
- **THEN** it only consumes geocoding tasks, allowing independent scaling

### Requirement: Redis broker dependency
The system SHALL use Redis as the Celery broker. The `REDIS_URL` environment variable MUST be set for both the scraper and backend.

#### Scenario: Missing Redis URL
- **WHEN** `REDIS_URL` is not set
- **THEN** the Celery app SHALL fall back to `redis://localhost:6379/0` for local development

### Requirement: Task retry configuration
The system SHALL configure default retry behavior for all Celery tasks: max 3 retries with exponential backoff (60s, 300s, 900s).

#### Scenario: Task fails transiently
- **WHEN** a task raises a retriable exception (connection error, timeout)
- **THEN** Celery retries the task up to 3 times with exponential backoff
- **THEN** after 3 failures, the task is marked as failed and logged
