# Values printed after `terraform apply` (and read with `terraform output -raw <name>`)

output "dashboard_url" {
  value = azurerm_storage_account.dashboard.primary_web_endpoint
}

output "api_urls" {
  value = { for name, app in azurerm_container_app.api : name => "https://${app.ingress[0].fqdn}" }
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}

output "acr_name" {
  value = azurerm_container_registry.main.name
}

output "resource_group" {
  value = azurerm_resource_group.main.name
}
