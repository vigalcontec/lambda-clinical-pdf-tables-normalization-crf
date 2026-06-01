# =============================================================================
# Configuration - Clinical PDF Tables Normalization Lambda
# =============================================================================

locals {
  # ─────────────────────────────────────────────────────────────────────────────
  # Project Configuration
  # ─────────────────────────────────────────────────────────────────────────────
  function_name = "clinical-pdf-normalization-crf"  # Lambda function name (without env suffix)
  project_name  = "clinical-rag-foundry"            # Project name for tagging
  company_name  = "vigalcontec"                     # Company name for resource naming

  # ─────────────────────────────────────────────────────────────────────────────
  # AWS Configuration
  # ─────────────────────────────────────────────────────────────────────────────
  aws_region = "eu-west-1"

  # ─────────────────────────────────────────────────────────────────────────────
  # Lambda Configuration
  # ─────────────────────────────────────────────────────────────────────────────
  timeout            = 120   # Lambda timeout in seconds (Claude API calls may take time)
  memory_size        = 512   # Lambda memory in MB
  log_level          = "INFO"
  log_retention_days = 30

  # ─────────────────────────────────────────────────────────────────────────────
  # Bedrock Configuration
  # ─────────────────────────────────────────────────────────────────────────────
  bedrock_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"

  # ─────────────────────────────────────────────────────────────────────────────
  # Computed Values (DO NOT MODIFY)
  # ─────────────────────────────────────────────────────────────────────────────
  account_id   = data.aws_caller_identity.current.account_id
  full_name    = "${local.function_name}-${var.environment}"
  state_bucket = "tfstate-${local.company_name}-${var.environment}-${local.account_id}"

  # Common tags
  common_tags = {
    Project     = local.project_name
    Function    = local.function_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
