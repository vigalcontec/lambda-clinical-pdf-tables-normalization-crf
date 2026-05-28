# =============================================================================
# Configuration - Update these values for your project
# =============================================================================

locals {
  # ─────────────────────────────────────────────────────────────────────────────
  # Project Configuration (UPDATE THESE)
  # ─────────────────────────────────────────────────────────────────────────────
  function_name = "my-lambda-function"  # Lambda function name (without env suffix)
  project_name  = "my-project"          # Project name for tagging
  company_name  = "vigalcontec"         # Company name for resource naming

  # ─────────────────────────────────────────────────────────────────────────────
  # AWS Configuration
  # ─────────────────────────────────────────────────────────────────────────────
  aws_region = "eu-west-1"

  # ─────────────────────────────────────────────────────────────────────────────
  # Lambda Configuration
  # ─────────────────────────────────────────────────────────────────────────────
  timeout            = 30    # Lambda timeout in seconds
  memory_size        = 256   # Lambda memory in MB
  log_level          = "INFO"
  log_retention_days = 30

  # ─────────────────────────────────────────────────────────────────────────────
  # Computed Values (DO NOT MODIFY)
  # ─────────────────────────────────────────────────────────────────────────────
  account_id    = data.aws_caller_identity.current.account_id
  full_name     = "${local.function_name}-${var.environment}"
  state_bucket  = "tfstate-${local.company_name}-${var.environment}-${local.account_id}"

  # Common tags
  common_tags = {
    Project     = local.project_name
    Function    = local.function_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
