# =============================================================================
# Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------
output "function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.main.function_name
}

output "function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.main.arn
}

output "function_invoke_arn" {
  description = "Lambda function invoke ARN (for API Gateway)"
  value       = aws_lambda_function.main.invoke_arn
}

# -----------------------------------------------------------------------------
# ECR
# -----------------------------------------------------------------------------
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = data.aws_ecr_repository.lambda.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = data.aws_ecr_repository.lambda.arn
}

# -----------------------------------------------------------------------------
# IAM
# -----------------------------------------------------------------------------
output "role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda.arn
}

output "role_name" {
  description = "Lambda execution role name"
  value       = aws_iam_role.lambda.name
}

# -----------------------------------------------------------------------------
# CloudWatch
# -----------------------------------------------------------------------------
output "log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "log_group_arn" {
  description = "CloudWatch log group ARN"
  value       = aws_cloudwatch_log_group.lambda.arn
}

# -----------------------------------------------------------------------------
# Configuration (for reference)
# -----------------------------------------------------------------------------
output "config" {
  description = "Configuration values used"
  value = {
    function_name = local.function_name
    project_name  = local.project_name
    company_name  = local.company_name
    environment   = var.environment
    aws_region    = local.aws_region
    state_bucket  = local.state_bucket
  }
}
