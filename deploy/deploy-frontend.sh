#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Use exported env vars from deploy.sh, or set defaults for standalone use
: "${BACKEND_SERVICE:=momaverse-backend}"
: "${REGION:=us-central1}"
: "${FRONTEND_BUCKET:=gs://momaverse-frontend}"

cd "$PROJECT_ROOT"

if [[ ! -f "package.json" ]]; then
  echo "Error: package.json not found at $PROJECT_ROOT" >&2
  exit 1
fi

echo "=== Installing Dependencies ==="
npm ci --ignore-scripts

echo ""
echo "=== Fetching Backend URL ==="
BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
  --region="${REGION}" \
  --format='value(status.url)')
echo "  Backend URL: ${BACKEND_URL}"

echo ""
echo "=== Building Frontend ==="
API_BASE_URL="${BACKEND_URL}" npm run build

DIST_DIR="$PROJECT_ROOT/dist"
if [[ ! -d "$DIST_DIR" ]]; then
  echo "Error: build output directory not found at $DIST_DIR" >&2
  exit 1
fi

echo ""
echo "=== Syncing to GCS Bucket ==="
gcloud storage rsync "$DIST_DIR" "${FRONTEND_BUCKET}" \
  --recursive \
  --delete-unmatched-destination-objects

echo ""
echo "=== Setting Cache Headers ==="

# HTML files: no-cache so users always get the latest
for html_file in index.html about.html; do
  if gcloud storage objects describe "${FRONTEND_BUCKET}/${html_file}" >/dev/null 2>&1; then
    gcloud storage objects update "${FRONTEND_BUCKET}/${html_file}" \
      --cache-control="no-cache"
    echo "  ${html_file}: no-cache"
  fi
done

# Hashed JS and CSS assets: immutable long-lived cache
for ext in js css; do
  gcloud storage objects update "${FRONTEND_BUCKET}/**/*.${ext}" \
    --cache-control="public, max-age=31536000, immutable" 2>/dev/null || true
  gcloud storage objects update "${FRONTEND_BUCKET}/*.${ext}" \
    --cache-control="public, max-age=31536000, immutable" 2>/dev/null || true
  echo "  *.${ext}: public, max-age=31536000, immutable"
done

echo ""
echo "=== Frontend deployment complete ==="
