#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

INFRA_DIR="$PROJECT_ROOT/infrastructure"

if [[ ! -d "$INFRA_DIR" ]]; then
  echo "Error: infrastructure directory not found at $INFRA_DIR" >&2
  exit 1
fi

cd "$INFRA_DIR"

echo "=== Terraform Init ==="
terraform init -input=false

echo ""
echo "=== Terraform Plan ==="
terraform plan -out=tfplan

echo ""

# Interactive confirmation when running in a terminal
if [ -t 0 ]; then
  read -r -p "Apply this Terraform plan? [y/N] " response
  case "$response" in
    [yY][eE][sS]|[yY])
      ;;
    *)
      echo "Terraform apply cancelled."
      rm -f tfplan
      exit 0
      ;;
  esac
else
  echo "(Non-interactive mode: applying automatically)"
fi

echo "=== Terraform Apply ==="
terraform apply tfplan

rm -f tfplan

echo ""
echo "=== Infrastructure deployment complete ==="
