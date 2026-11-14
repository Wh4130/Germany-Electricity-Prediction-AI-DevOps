# The dashboard: a static website in a storage account (Static Web Apps are not available in the regions that
# Azure for Students allows). The built files are uploaded as blobs into the special "$web" container.

resource "azurerm_storage_account" "dashboard" {
  name                     = substr("${local.flat}web", 0, 24)
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

resource "azurerm_storage_account_static_website" "dashboard" {
  storage_account_id = azurerm_storage_account.dashboard.id
  index_document     = "index.html"
  error_404_document = "index.html"
}

locals {
  dashboard_origin = trimsuffix(azurerm_storage_account.dashboard.primary_web_endpoint, "/")
  # the "$web" container is created by the static website, so its ID is built from the account's
  web_container_id = "${azurerm_storage_account.dashboard.id}/blobServices/default/containers/$web"

  # every built file except config.json (written below with the API URLs)
  dashboard_files = setsubtract(fileset(var.dashboard_dist, "**"), ["config.json"])

  content_types = {
    html  = "text/html; charset=utf-8"
    js    = "text/javascript; charset=utf-8"
    css   = "text/css; charset=utf-8"
    json  = "application/json"
    csv   = "text/csv; charset=utf-8"
    svg   = "image/svg+xml"
    png   = "image/png"
    ico   = "image/x-icon"
    txt   = "text/plain; charset=utf-8"
    woff2 = "font/woff2"
  }
}

resource "azurerm_storage_blob" "dashboard" {
  for_each = local.dashboard_files

  name                 = each.value
  storage_container_id = local.web_container_id
  type                 = "Block"
  source               = "${var.dashboard_dist}/${each.value}"
  content_md5          = filemd5("${var.dashboard_dist}/${each.value}") # re-upload when the file changes
  content_type         = lookup(local.content_types, lower(regex("[^.]+$", each.value)), "application/octet-stream")

  depends_on = [azurerm_storage_account_static_website.dashboard] # creates the $web container
}

# the dashboard's model list, pointing at the deployed APIs
resource "azurerm_storage_blob" "config" {
  name                 = "config.json"
  storage_container_id = local.web_container_id
  type                 = "Block"
  content_type         = "application/json"
  source_content = jsonencode({
    models = [
      { id = "sarimax", label = "SARIMAX", url = "https://${azurerm_container_app.api["sarimax-api"].ingress[0].fqdn}" },
    ]
    featureSource = "sarimax"
  })

  depends_on = [azurerm_storage_account_static_website.dashboard]
}
