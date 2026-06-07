# =============================================================================
# AWS Lambda with ECR Container Image
# =============================================================================

terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = local.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# ECR Repository (created by CI/CD via AWS CLI, referenced here)
# -----------------------------------------------------------------------------
data "aws_ecr_repository" "lambda" {
  name = local.full_name
}

# Lifecycle policy for the ECR repository
resource "aws_ecr_lifecycle_policy" "lambda" {
  repository = data.aws_ecr_repository.lambda.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------
resource "aws_lambda_function" "main" {
  function_name = local.full_name
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.lambda.repository_url}:${var.image_tag}"

  timeout                        = local.timeout
  memory_size                    = local.memory_size
  
  environment {
    variables = {
      ENVIRONMENT                  = var.environment
      LOG_LEVEL                    = local.log_level
      POWERTOOLS_SERVICE_NAME      = local.function_name
      POWERTOOLS_METRICS_NAMESPACE = local.project_name

      # Datalake configuration (from SSM via Terraform)
      RAW_BUCKET_NAME      = local.datalake.raw.bucket_name
      RAW_BUCKET_ARN       = local.datalake.raw.bucket_arn
      RAW_KMS_KEY_ARN      = local.datalake.raw.kms_key_arn
      STAGING_BUCKET_NAME  = local.datalake.staging.bucket_name
      STAGING_BUCKET_ARN   = local.datalake.staging.bucket_arn
      STAGING_KMS_KEY_ARN  = local.datalake.staging.kms_key_arn
      BUSINESS_BUCKET_NAME = local.datalake.business.bucket_name
      BUSINESS_BUCKET_ARN  = local.datalake.business.bucket_arn
      BUSINESS_KMS_KEY_ARN = local.datalake.business.kms_key_arn

      # DynamoDB configuration (from SSM via Terraform)
      DYNAMODB_TABLE_NAME = local.dynamodb.clinical_pdf_jobs.table_name

      # Bedrock configuration
      BEDROCK_MODEL_ID = local.bedrock_model_id
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = {
    Name = local.full_name
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda
  ]
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.full_name}"
  retention_in_days = local.log_retention_days

  tags = {
    Name = local.full_name
  }
}

# -----------------------------------------------------------------------------
# Lambda Permission (for triggers - customize as needed)
# -----------------------------------------------------------------------------
# Example: S3 trigger
# resource "aws_lambda_permission" "s3" {
#   statement_id  = "AllowS3Invoke"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.main.function_name
#   principal     = "s3.amazonaws.com"
#   source_arn    = local.datalake.raw.bucket_arn
# }
