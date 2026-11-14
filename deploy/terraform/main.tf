# The model APIs: a container registry for the images and one Azure Container App per model.
#
# Syntax in short: `resource "<type>" "<local name>" { ... }` declares one cloud object. Other blocks refer to
# its attributes as <type>.<local name>.<attribute>, e.g. azurerm_resource_group.main.name. Terraform builds
# the dependency graph from these references and creates the objects in the right order.

# a short random suffix: registry and storage account names must be unique in all of Azure
resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  name = "${var.project}-${random_string.suffix.result}" # e.g. loadforecast-a1b2c
  flat = "${var.project}${random_string.suffix.result}"  # for names without hyphens
  tags = { project = var.project, managed_by = "terraform" }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project}"
  location = var.location
  tags     = local.tags
}

# --------------------------------------------------------------------------
# Container registry: holds the Docker images of the APIs (pushed by deploy.sh)
# --------------------------------------------------------------------------

resource "azurerm_container_registry" "main" {
  name                = local.flat
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false # no shared password; the apps pull with a managed identity
  tags                = local.tags
}

# an identity for the container apps, allowed to pull from the registry (no secrets anywhere)
resource "azurerm_user_assigned_identity" "pull" {
  name                = "id-${local.name}-pull"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.pull.principal_id
}

# --------------------------------------------------------------------------
# Container Apps: serverless containers that scale to zero
# --------------------------------------------------------------------------

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.name}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${local.name}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  logs_destination           = "log-analytics"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags

  # serverless (pay per use); Azure adds this profile anyway, so it is declared to avoid a diff on every plan
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

# `for_each` makes one container app per entry of var.apps; each.key is the name, each.value the settings
resource "azurerm_container_app" "api" {
  for_each = var.apps

  name                         = each.key
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.pull.id]
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = azurerm_user_assigned_identity.pull.id
  }

  ingress {
    external_enabled = true # a public HTTPS URL
    target_port      = each.value.port
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = 1

    # scale out from zero on HTTP traffic (Azure's default rule, declared so plans stay clean); scale back to
    # zero after 5 minutes without requests
    http_scale_rule {
      name                = "http-scaler"
      concurrent_requests = "10"
    }
    cooldown_period_in_seconds  = 300
    polling_interval_in_seconds = 30

    container {
      name   = "api"
      image  = "${azurerm_container_registry.main.login_server}/${each.value.image}:${var.image_tag}"
      cpu    = each.value.cpu
      memory = each.value.memory

      # only the dashboard may call the API from a browser
      env {
        name  = "ALLOWED_ORIGINS"
        value = local.dashboard_origin
      }
    }
  }

  # the identity has to be allowed to pull before the first revision starts
  depends_on = [azurerm_role_assignment.acr_pull]
}
