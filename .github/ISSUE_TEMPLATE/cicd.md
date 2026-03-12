---
name: "CI/CD Task"
about: "Infrastructure, automation, and DevOps task"
title: "[CI/CD]: "
labels: ["track:cicd"]
---

## CI/CD Task

### Objective
<!-- REQUIRED: What should be automated or configured? Be specific.
Example: "Set up a GitHub Actions workflow that runs pytest on every PR targeting main"
-->

### Current State
<!-- REQUIRED: What exists today?
- Is there any existing automation for this?
- What manual steps does this replace?
- Any existing workflows in .github/workflows/?
-->

### Implementation Plan
<!-- REQUIRED: Step-by-step plan for the implementing agent -->
1.
2.
3.

### Environment & Services
<!-- REQUIRED: What infrastructure/services are involved?
- GitHub Actions / other CI provider
- Docker / container registry
- Deployment target (FTP, cloud, VPS)
- Secrets/env vars needed (name only, never values)
-->

### Files to Create/Modify
<!-- List the specific files this task will touch -->
- [ ] `.github/workflows/...`
- [ ] `Dockerfile` / `docker-compose.yml`
- [ ] Other:

### Trigger Conditions
<!-- When should this automation run? -->
- [ ] On push to main
- [ ] On pull request
- [ ] On schedule (cron)
- [ ] Manual dispatch
- [ ] Other:

### Dependencies
- Depends on: #
- Blocks: #

### Acceptance Criteria
<!-- REQUIRED: How do we know this works? -->
- [ ] Workflow runs successfully on trigger
- [ ] Failure cases are handled (notifications, status checks)
- [ ] Secrets are stored securely (never in code)
- [ ] Documentation updated if needed

### Tech Stack Reference
<!-- DO NOT EDIT: Standard context for the implementing agent -->
- **Frontend build**: esbuild (see build.js)
- **Backend**: FastAPI with uv (backend/pyproject.toml)
- **Pipeline**: Python scripts (pipeline/)
- **Database**: PostgreSQL
- **Testing**: Playwright (e2e), pytest (backend/pipeline)
- **Linting**: ruff, mypy (Python), pre-commit hooks
