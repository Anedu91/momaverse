#!/usr/bin/env bash
#
# One-time bootstrap: creates Workload Identity Federation resources
# so GitHub Actions can authenticate to GCP.
#
# Run this ONCE before setting up CI/CD workflows.
# After this, all infrastructure changes go through GitHub Actions.
#
# Usage: ./bootstrap-wif.sh

set -euo pipefail

PROJECT_ID="momaverse"
POOL_ID="momaverse-github-pool"
PROVIDER_ID="github"
SA_NAME="momaverse-cicd"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
REPO="Anedu91/momaverse"

echo "=== Enabling required APIs ==="
gcloud services enable iam.googleapis.com --project="${PROJECT_ID}"
gcloud services enable iamcredentials.googleapis.com --project="${PROJECT_ID}"

echo "=== Creating CI/CD service account ==="
gcloud iam service-accounts create "${SA_NAME}" \
  --project="${PROJECT_ID}" \
  --display-name="Momaverse CI/CD (GitHub Actions)"

echo "=== Creating Workload Identity Pool ==="
gcloud iam workload-identity-pools create "${POOL_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions Pool" \
  --description="OIDC federation for GitHub Actions"

echo "=== Creating OIDC Provider (restricted to ${REPO}) ==="
gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" \
  --display-name="GitHub" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository == '${REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

echo "=== Getting project number ==="
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")

echo "=== Allowing GitHub pool to impersonate CI/CD SA ==="
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}"

echo "=== Granting CI/CD SA permissions ==="
# Push Docker images to Artifact Registry
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/artifactregistry.writer"

# Deploy Cloud Run services and jobs
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"

# Act as backend/pipeline service accounts when deploying
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

# Upload frontend to GCS (scoped to frontend bucket in GCP console if needed)
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

echo ""
echo "=== Done! ==="
echo ""
echo "Workload Identity Provider:"
echo "  projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
echo ""
echo "Service Account:"
echo "  ${SA_EMAIL}"
echo ""
echo "Add these GitHub Secrets (Settings → Secrets → Actions):"
echo "  GCP_PROJECT_ID = ${PROJECT_ID}"
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER = projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
