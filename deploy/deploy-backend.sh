#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Use exported env vars from deploy.sh, or set defaults for standalone use
: "${DOCKER_REPO:=us-central1-docker.pkg.dev/momaverse/momaverse-docker}"
: "${BACKEND_SERVICE:=momaverse-backend}"
: "${REGION:=us-central1}"

BACKEND_DIR="$PROJECT_ROOT/backend"

if [[ ! -f "$BACKEND_DIR/Dockerfile" ]]; then
  echo "Error: backend Dockerfile not found at $BACKEND_DIR/Dockerfile" >&2
  exit 1
fi

GIT_SHA="$(git rev-parse --short HEAD)"
IMAGE="${DOCKER_REPO}/backend:${GIT_SHA}"
IMAGE_LATEST="${DOCKER_REPO}/backend:latest"

echo "=== Configuring Docker Auth ==="
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo ""
echo "=== Building Backend Image ==="
echo "  Image: ${IMAGE}"
docker build --platform linux/amd64 \
  -t "${IMAGE}" \
  -t "${IMAGE_LATEST}" \
  "$BACKEND_DIR"

echo ""
echo "=== Pushing Backend Image ==="
docker push "${IMAGE}"
docker push "${IMAGE_LATEST}"

echo ""
echo "=== Updating Cloud Run Service ==="
gcloud run deploy "${BACKEND_SERVICE}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --quiet

echo ""
SERVICE_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
  --region="${REGION}" \
  --format='value(status.url)')
echo "=== Backend deployed: ${SERVICE_URL} ==="
