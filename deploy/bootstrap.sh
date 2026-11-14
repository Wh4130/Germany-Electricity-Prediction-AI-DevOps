#!/usr/bin/env bash
# =====================================================================================================================
# One-time setup that Terraform and the CD workflow need before they can run ("bootstrap").
#
# Why not Terraform? Chicken and egg:
#   - Terraform keeps its state in an Azure storage account, so that account must exist before Terraform runs.
#   - The CD workflow logs in to Azure as a service principal, so that identity must exist before CD runs.
# These are made once, by hand, by someone with Owner rights on the subscription. Everything else (registry,
# Container Apps, dashboard storage, ...) is managed by Terraform in deploy/terraform.
#
# Order for a new subscription:
#   1. deploy/bootstrap.sh state     resource providers + Terraform state storage
#   2. deploy/deploy.sh              first deployment from your machine (creates rg-loadforecast)
#   3. deploy/bootstrap.sh github    identity for GitHub Actions (OIDC), its roles, GitHub environment + variables
#   4. from then on: merge to master -> CI -> approve -> CD deploys
#
# Every step checks whether its object exists first, so running the script again changes nothing.
#
# Needs: az (logged in: az login), gh (logged in: gh auth login) for the github phase.
# Settings: environment variables below; the defaults are this project's values.
# =====================================================================================================================
set -euo pipefail

# ---------------------------------------------------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------------------------------------------------
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-$(az account show --query id -o tsv)}"
LOCATION="${LOCATION:-swedencentral}"          # Azure for Students allows only a few regions (see variables.tf)
PROJECT="${PROJECT:-loadforecast}"

APP_RG="${APP_RG:-rg-$PROJECT}"                  # made by Terraform (azurerm_resource_group.main)
STATE_RG="${STATE_RG:-rg-$PROJECT-tfstate}"
# globally unique, 3-24 lowercase letters / digits; must equal storage_account_name in terraform/versions.tf
STATE_ACCOUNT="${STATE_ACCOUNT:-loadforecastvllqbtf}"
STATE_CONTAINER="${STATE_CONTAINER:-tfstate}"

GITHUB_REPO="${GITHUB_REPO:-Wh4130/Germany-Electricity-Prediction-AI-DevOps}"
GITHUB_ENV="${GITHUB_ENV:-production}"           # the GitHub environment the CD job runs in
GITHUB_BRANCH="${GITHUB_BRANCH:-master}"         # the only branch allowed to deploy
SP_NAME="${SP_NAME:-github-$PROJECT-cd}"

# the resource providers the Terraform configuration uses (azurerm 5.x no longer registers them itself)
PROVIDERS=(Microsoft.App Microsoft.ContainerRegistry Microsoft.ManagedIdentity Microsoft.OperationalInsights
           Microsoft.Storage)

ACRPULL_ROLE_ID="7f951dda-4ed3-4680-a7ca-43fe172d538d"   # built-in role "AcrPull" (the same ID in every tenant)

# ---------------------------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------------------------
log() { printf '\n== %s\n' "$*"; }
ok() { printf '   ok: %s\n' "$*"; }

# az prints Python warnings on stderr with some installations; keep the output readable
az() { command az "$@" 2> >(grep -v -E 'SyntaxWarning|excludedActions' >&2); }

# assign a role unless the same principal already has it on the same scope
# usage: ensure_role <principal object id> <principal type> <role name> <scope> [condition]
ensure_role() {
  local principal="$1" type="$2" role="$3" scope="$4" condition="${5:-}"
  local existing
  existing=$(az role assignment list --assignee "$principal" --role "$role" --scope "$scope" --query "length(@)" -o tsv)
  if [[ "$existing" != "0" ]]; then
    ok "$role already on ${scope##*/}"
    return
  fi
  local extra=()
  if [[ -n "$condition" ]]; then extra=(--condition "$condition" --condition-version 2.0); fi
  az role assignment create --assignee-object-id "$principal" --assignee-principal-type "$type" \
    --role "$role" --scope "$scope" ${extra[@]+"${extra[@]}"} -o none   # (empty-array safe on macOS bash 3.2)
  ok "$role assigned on ${scope##*/}"
}

az account set --subscription "$SUBSCRIPTION_ID"

# =====================================================================================================================
# Phase 1: before the first deployment
# =====================================================================================================================
bootstrap_state() {
  # -- 1.1 Resource providers ------------------------------------------------------------------------------------------
  # A subscription has to "register" a service (e.g. Container Apps = Microsoft.App) once before it can be used.
  # Free; needs rights on the whole subscription, which is why it is here and not in Terraform / CD.
  log "1.1 resource providers"
  for p in "${PROVIDERS[@]}"; do
    state=$(az provider show -n "$p" --query registrationState -o tsv)
    if [[ "$state" == "Registered" ]]; then ok "$p"; else az provider register -n "$p" --wait -o none; ok "$p registered"; fi
  done

  # -- 1.2 Storage for the Terraform state -----------------------------------------------------------------------------
  # Its own resource group, so that `terraform destroy` of the app can never delete its own state.
  log "1.2 Terraform state storage: $STATE_RG / $STATE_ACCOUNT / $STATE_CONTAINER"
  az group create -n "$STATE_RG" -l "$LOCATION" --tags project="$PROJECT" purpose=terraform-state -o none
  ok "resource group $STATE_RG"

  if [[ -z "$(az storage account list -g "$STATE_RG" --query "[?name=='$STATE_ACCOUNT'].name" -o tsv)" ]]; then
    az storage account create -n "$STATE_ACCOUNT" -g "$STATE_RG" -l "$LOCATION" \
      --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 --allow-blob-public-access false -o none
  fi
  ok "storage account $STATE_ACCOUNT"

  # blob versioning: every write of the state keeps the old version, so a broken state can be rolled back
  az storage account blob-service-properties update --account-name "$STATE_ACCOUNT" -g "$STATE_RG" \
    --enable-versioning true -o none
  ok "blob versioning on"

  # Terraform logs in to the state with Azure AD (use_azuread_auth = true in versions.tf), not with the storage
  # key, so the person running Terraform needs a data role on the account. Owner alone is not enough for data.
  local state_id me
  state_id=$(az storage account show -n "$STATE_ACCOUNT" -g "$STATE_RG" --query id -o tsv)
  me=$(az ad signed-in-user show --query id -o tsv)
  ensure_role "$me" User "Storage Blob Data Contributor" "$state_id"

  # a new role can take a minute to apply; retry the container creation until it works
  for i in $(seq 1 12); do
    if az storage container create -n "$STATE_CONTAINER" --account-name "$STATE_ACCOUNT" --auth-mode login -o none 2>/dev/null; then
      break
    fi
    sleep 10
  done
  ok "container $STATE_CONTAINER"

  log "done. Next: deploy/deploy.sh (first deployment), then deploy/bootstrap.sh github"
}

# =====================================================================================================================
# Phase 2: after the first deployment (needs the resource group $APP_RG that Terraform made)
# =====================================================================================================================
bootstrap_github() {
  local app_rg_id state_id tenant_id
  app_rg_id=$(az group show -n "$APP_RG" --query id -o tsv) ||
    { echo "resource group $APP_RG not found: run deploy/deploy.sh first" >&2; exit 1; }
  state_id=$(az storage account show -n "$STATE_ACCOUNT" -g "$STATE_RG" --query id -o tsv)
  tenant_id=$(az account show --query tenantId -o tsv)

  # -- 2.1 An identity for GitHub Actions --------------------------------------------------------------------------------
  # App registration = the application object in Entra ID; service principal = its instance in this tenant,
  # the thing that gets roles. There is no password or secret: login is by OIDC (2.2).
  log "2.1 identity $SP_NAME"
  local app_id sp_id
  app_id=$(az ad app list --display-name "$SP_NAME" --query "[0].appId" -o tsv)
  if [[ -z "$app_id" ]]; then
    app_id=$(az ad app create --display-name "$SP_NAME" --query appId -o tsv)
  fi
  ok "app registration (client id $app_id)"
  sp_id=$(az ad sp list --filter "appId eq '$app_id'" --query "[0].id" -o tsv)
  if [[ -z "$sp_id" ]]; then
    sp_id=$(az ad sp create --id "$app_id" --query id -o tsv)
  fi
  ok "service principal (object id $sp_id)"

  # -- 2.2 Federated credential: which GitHub token Azure accepts ------------------------------------------------------
  # A job in GitHub Actions can ask GitHub for a short-lived OIDC token. Azure exchanges it for an Azure token
  # only when issuer, subject and audience match exactly. The subject names the repository and the environment,
  # so only jobs in this repo's "production" environment (which needs an approval, master only) can log in;
  # other repos, forks and branches cannot.
  # The start of the subject depends on the repository's OIDC setting: "repo:owner/name", or with immutable
  # subjects "repo:owner@<owner id>/name@<repo id>" (survives a rename or transfer). GitHub tells us which one,
  # so we never guess: a subject that differs by one character is rejected at login (AADSTS700213).
  log "2.2 federated credential"
  local prefix subject cred_name="github-$GITHUB_ENV" current
  prefix=$(gh api "repos/$GITHUB_REPO/actions/oidc/customization/sub" -q '.sub_claim_prefix // empty')
  subject="${prefix:-repo:$GITHUB_REPO}:environment:$GITHUB_ENV"
  current=$(az ad app federated-credential list --id "$app_id" --query "[?name=='$cred_name'].subject | [0]" -o tsv)
  if [[ -z "$current" ]]; then
    az ad app federated-credential create --id "$app_id" -o none --parameters "{
      \"name\": \"$cred_name\",
      \"issuer\": \"https://token.actions.githubusercontent.com\",
      \"subject\": \"$subject\",
      \"audiences\": [\"api://AzureADTokenExchange\"],
      \"description\": \"GitHub Actions jobs of $GITHUB_REPO in the $GITHUB_ENV environment\"
    }"
  elif [[ "$current" != "$subject" ]]; then
    # an existing credential with another subject (older script, repository setting changed): correct it
    az ad app federated-credential update --id "$app_id" --federated-credential-id "$cred_name" -o none --parameters "{
      \"subject\": \"$subject\",
      \"description\": \"GitHub Actions jobs of $GITHUB_REPO in the $GITHUB_ENV environment\"
    }"
    ok "corrected subject (was $current)"
  fi
  ok "trusts $subject"

  # -- 2.3 Roles: what the identity may do (least privilege, nothing on the whole subscription) ------------------------
  log "2.3 roles"
  # create / change / delete the resources of the app
  ensure_role "$sp_id" ServicePrincipal "Contributor" "$app_rg_id"
  # Terraform gives the API's managed identity the AcrPull role, which needs the right to write role assignments.
  # The condition limits that right to the AcrPull role, so the identity cannot make itself or others Owner.
  local condition="((!(ActionMatches{'Microsoft.Authorization/roleAssignments/write'})) OR (@Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {$ACRPULL_ROLE_ID})) AND ((!(ActionMatches{'Microsoft.Authorization/roleAssignments/delete'})) OR (@Resource[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {$ACRPULL_ROLE_ID}))"
  ensure_role "$sp_id" ServicePrincipal "Role Based Access Control Administrator" "$app_rg_id" "$condition"
  # read and write the Terraform state
  ensure_role "$sp_id" ServicePrincipal "Storage Blob Data Contributor" "$state_id"

  # -- 2.4 GitHub: the production environment and its variables --------------------------------------------------------
  log "2.4 GitHub environment $GITHUB_ENV in $GITHUB_REPO"
  local me_id
  me_id=$(gh api user -q .id)
  # required reviewer: the CD job waits until this user approves it in GitHub; deployments only from listed branches
  gh api -X PUT "repos/$GITHUB_REPO/environments/$GITHUB_ENV" --input - >/dev/null <<EOF
{"wait_timer": 0, "prevent_self_review": false,
 "reviewers": [{"type": "User", "id": $me_id}],
 "deployment_branch_policy": {"protected_branches": false, "custom_branch_policies": true}}
EOF
  ok "environment with reviewer $(gh api user -q .login)"
  if [[ -z "$(gh api "repos/$GITHUB_REPO/environments/$GITHUB_ENV/deployment-branch-policies" -q ".branch_policies[] | select(.name == \"$GITHUB_BRANCH\") | .name")" ]]; then
    gh api -X POST "repos/$GITHUB_REPO/environments/$GITHUB_ENV/deployment-branch-policies" \
      -f name="$GITHUB_BRANCH" -f type=branch >/dev/null
  fi
  ok "deploys only from $GITHUB_BRANCH"

  # IDs, not secrets: they say which identity to log in as; the proof is the OIDC token
  gh variable set AZURE_CLIENT_ID --env "$GITHUB_ENV" --repo "$GITHUB_REPO" --body "$app_id"
  gh variable set AZURE_TENANT_ID --env "$GITHUB_ENV" --repo "$GITHUB_REPO" --body "$tenant_id"
  gh variable set AZURE_SUBSCRIPTION_ID --env "$GITHUB_ENV" --repo "$GITHUB_REPO" --body "$SUBSCRIPTION_ID"
  ok "variables AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID"

  log "done. CD (.github/workflows/cd.yml) runs after CI passes on $GITHUB_BRANCH"
}

case "${1:-}" in
  state) bootstrap_state ;;
  github) bootstrap_github ;;
  *)
    echo "usage: $0 state | github   (see the header of this file)" >&2
    exit 1
    ;;
esac
