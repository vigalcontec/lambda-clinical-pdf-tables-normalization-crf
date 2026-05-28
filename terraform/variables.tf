# =============================================================================
# Variables - Runtime inputs (provided by CI/CD)
# =============================================================================
# Static configuration is in config.tf

variable "environment" {
  description = "Environment name (dev, qa, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "qa", "prod"], var.environment)
    error_message = "Environment must be dev, qa, or prod."
  }
}

variable "image_tag" {
  description = "Docker image tag to deploy (provided by CI/CD)"
  type        = string
  default     = "latest"
}
