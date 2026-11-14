# Which Terraform and which providers (plugins that talk to a cloud API) this configuration needs.
# `terraform init` downloads them into .terraform/ and pins the exact versions in .terraform.lock.hcl.
terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.13" # any 5.x from 5.13 on, not 6.0
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }

  # The state (what Terraform has created) lives in an Azure storage container, so that GitHub Actions and
  # every team member work on the same state. The container is made once by deploy/bootstrap.sh (state):
  # it cannot be managed by the configuration whose state it stores. Login: Azure AD (az login locally,
  # OIDC in GitHub Actions), no storage keys. Backend settings cannot use variables, hence the literals.
  backend "azurerm" {
    resource_group_name  = "rg-loadforecast-tfstate"
    storage_account_name = "loadforecastvllqbtf"
    container_name       = "tfstate"
    key                  = "loadforecast.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
  # The resource providers (Microsoft.App, .ContainerRegistry, .ManagedIdentity, .OperationalInsights,
  # .Storage) are registered once per subscription by deploy/bootstrap.sh. Terraform does not register them,
  # so the GitHub identity needs no rights on the whole subscription.
}
