#!/usr/bin/env bash
# =====================================================================================================================
# Build and deploy everything to Azure. The one place that defines the deployment steps: run by hand from your
# machine, and by GitHub Actions (.github/workflows/cd.yml calls it with --auto-approve).
#
#   deploy/deploy.sh                  # shows each plan and asks before applying (your machine)
#   deploy/deploy.sh --auto-approve   # no questions (CD: the approval happened in GitHub's production environment)
#   deploy/deploy.sh destroy          # delete all resources of this project (asks first)
#
# Needs: az (logged in), docker, node / npm, terraform. Before the first run on a new subscription:
# deploy/bootstrap.sh state (see that file).
#
# Steps:
#   1. the container registry (Terraform, alone: the image needs somewhere to go before the app can use it)
#   2. the API images (SARIMAX, tree): build for linux/amd64 and push them to the registry
#   3. the dashboard: npm build into deploy/dashboard/dist
#   4. everything else (Terraform): container app with the new image, storage website, config.json
# =====================================================================================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/terraform"

APPROVE=()
case "${1:-}" in
  "") ;;
  --auto-approve) APPROVE=(-auto-approve) ;;
  destroy)
    terraform init -input=false >/dev/null
    terraform destroy -var "image_tag=unused"
    exit 0
    ;;
  *)
    echo "usage: $0 [--auto-approve | destroy]" >&2
    exit 1
    ;;
esac

# connect to the state in Azure Storage and download the providers
terraform init -input=false >/dev/null

# a new image tag per deploy: the commit, plus a timestamp when there are uncommitted changes (so a local test
# build never overwrites the image of a commit)
TAG="$(git -C "$HERE" rev-parse --short HEAD)"
if [[ -n "$(git -C "$HERE" status --porcelain)" ]]; then TAG="$TAG-$(date +%Y%m%d%H%M%S)"; fi
echo "== image tag: $TAG"

echo "== 1/4 container registry"
terraform apply -input=false ${APPROVE[@]+"${APPROVE[@]}"} -var "image_tag=$TAG" -target=azurerm_container_registry.main
ACR_NAME="$(terraform output -raw acr_name)"
ACR="$(terraform output -raw acr_login_server)"

echo "== 2/4 API images -> $ACR"
az acr login --name "$ACR_NAME"            # docker login to the registry with the current az identity
# One image per model API: the folder deploy/<name with _>/ is pushed as <name with ->, which is the `image` of the
# app in variables.tf (sarimax_api -> sarimax-api). A new model API is one more name in this list.
for dir in sarimax_api tree_api; do
  image="${dir//_/-}"
  "$HERE/$dir/stage.sh" >/dev/null         # copy model, data and code into the build context
  # Container Apps run on linux/amd64; --platform makes that work on an Apple-silicon Mac too
  docker buildx build --platform linux/amd64 -t "$ACR/$image:$TAG" --push "$HERE/$dir"
done

echo "== 3/4 dashboard build"
(cd "$HERE/dashboard" && npm ci --silent && npm run build --silent)

echo "== 4/4 everything else"
terraform apply -input=false ${APPROVE[@]+"${APPROVE[@]}"} -var "image_tag=$TAG"

echo
terraform output
