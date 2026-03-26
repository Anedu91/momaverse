#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Use exported env vars from deploy.sh, or set defaults for standalone use
: "${DOCKER_REPO:=us-central1-docker.pkg.dev/momaverse/momaverse-docker}"
: "${PIPELINE_JOB:=momaverse-pipeline}"
: "${REGION:=us-central1}"

PIPELINE_DIR="$PROJECT_ROOT/pipeline"

if [[ ! -f "$PIPELINE_DIR/Dockerfile" ]]; then
  echo "Error: pipeline Dockerfile not found at $PIPELINE_DIR/Dockerfile" >&2
  exit 1
fi

GIT_SHA="$(git rev-parse --short HEAD)"
IMAGE="${DOCKER_REPO}/pipeline:${GIT_SHA}"
IMAGE_LATEST="${DOCKER_REPO}/pipeline:latest"

echo "=== Configuring Docker Auth ==="
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo ""
echo "=== Building Pipeline Image ==="
echo "  Image: ${IMAGE}"
echo "  (This may take a few minutes due to Playwright/Chromium)"
docker build --platform linux/amd64 \
  -t "${IMAGE}" \
  -t "${IMAGE_LATEST}" \
  "$PIPELINE_DIR"

echo ""
echo "=== Pushing Pipeline Image ==="
docker push "${IMAGE}"
docker push "${IMAGE_LATEST}"

echo ""
echo "=== Updating Cloud Run Job ==="
gcloud run jobs update "${PIPELINE_JOB}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --quiet

echo ""
echo "=== Pipeline deployment complete ==="
