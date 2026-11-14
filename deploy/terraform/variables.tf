# Inputs. Values come from terraform.tfvars, from -var on the command line, or from the defaults below.

variable "subscription_id" {
  description = "Azure subscription to deploy into (az account show --query id -o tsv)"
  type        = string
}

variable "location" {
  description = "Azure region; Azure for Students only allows swedencentral, norwayeast, belgiumcentral, polandcentral, switzerlandnorth"
  type        = string
  default     = "swedencentral"
}

variable "project" {
  description = "Prefix of the resource names"
  type        = string
  default     = "loadforecast"
}

# One entry per model API. Adding the tree model later is one more entry here (and its image in the registry).
variable "apps" {
  description = "Model APIs: container app name => image repository, port, CPU and memory"
  type = map(object({
    image  = string
    port   = number
    cpu    = number
    memory = string
  }))
  default = {
    "sarimax-api" = { image = "sarimax-api", port = 8000, cpu = 0.5, memory = "1Gi" }
  }
}

variable "image_tag" {
  description = "Tag of the API images in the registry (set by deploy.sh to the git commit)"
  type        = string
}

variable "min_replicas" {
  description = "0: the APIs scale to zero when idle (free, but the first request waits ~10-20 s); 1: always on"
  type        = number
  default     = 0
}

variable "dashboard_dist" {
  description = "Folder with the built dashboard (npm run build)"
  type        = string
  default     = "../dashboard/dist"
}
