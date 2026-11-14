#!/usr/bin/env bash
# Build and deploy everything to Azure (run from anywhere; needs az login, docker, node, terraform).
#
#   deploy/deploy.sh            # plan and ask before each apply
#   deploy/deploy.sh destroy    # delete all resources of this project
#
# Steps: 1. the registry (Terraform), 2. the API image (Docker -> registry), 3. the dashboard build,
#        4. everything else (Terraform: container app, storage website, config.json).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TF="$HERE/terraform"
cd "$TF"

terraform init -input=false >/dev/null

if [[ "${1:-}" == "destroy" ]]; then
  terraform destroy -var "image_tag=unused"
  exit 0
fi

# a new tag per deploy: the commit, plus a timestamp when there are uncommitted changes
TAG="$(git -C "$HERE" rev-parse --short HEAD)"
if [[ -n "$(git -C "$HERE" status --porcelain)" ]]; then TAG="$TAG-$(date +%Y%m%d%H%M%S)"; fi
echo "== image tag: $TAG"

echo "== 1/4 container registry"
terraform apply -var "image_tag=$TAG" -target=azurerm_container_registry.main
ACR_NAME="$(terraform output -raw acr_name)"
ACR="$(terraform output -raw acr_login_server)"

echo "== 2/4 SARIMAX API image -> $ACR"
"$HERE/sarimax_api/stage.sh" >/dev/null
az acr login --name "$ACR_NAME"
# Container Apps run on linux/amd64; build for it also on an Apple-silicon Mac
docker buildx build --platform linux/amd64 -t "$ACR/sarimax-api:$TAG" --push "$HERE/sarimax_api"

echo "== 3/4 dashboard build"
(cd "$HERE/dashboard" && npm ci --silent && npm run build --silent)

echo "== 4/4 everything else"
terraform apply -var "image_tag=$TAG"

echo
terraform output
