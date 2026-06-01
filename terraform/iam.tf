# =============================================================================
# IAM Role and Policies for Lambda
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda Execution Role
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda" {
  name = "${local.full_name}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.full_name}-lambda"
  })
}

# -----------------------------------------------------------------------------
# Basic Lambda Execution Policy (CloudWatch Logs)
# -----------------------------------------------------------------------------
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# -----------------------------------------------------------------------------
# X-Ray Tracing Policy
# -----------------------------------------------------------------------------
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# -----------------------------------------------------------------------------
# S3 Access to Datalake Buckets
# -----------------------------------------------------------------------------
resource "aws_iam_role_policy" "s3_access" {
  name = "${local.full_name}-s3"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3ReadWrite"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${local.datalake.raw.bucket_arn}",
          "${local.datalake.raw.bucket_arn}/*",
          "${local.datalake.staging.bucket_arn}",
          "${local.datalake.staging.bucket_arn}/*",
          "${local.datalake.business.bucket_arn}",
          "${local.datalake.business.bucket_arn}/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# KMS Access for Datalake Encryption
# -----------------------------------------------------------------------------
resource "aws_iam_role_policy" "kms_access" {
  name = "${local.full_name}-kms"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "KMSDecryptEncrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [
          local.datalake.raw.kms_key_arn,
          local.datalake.staging.kms_key_arn,
          local.datalake.business.kms_key_arn
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Bedrock Access for Claude AI
# -----------------------------------------------------------------------------
resource "aws_iam_role_policy" "bedrock_access" {
  name = "${local.full_name}-bedrock"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockInvokeModel"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${local.aws_region}::foundation-model/${local.bedrock_model_id}",
          "arn:aws:bedrock:${local.aws_region}::foundation-model/anthropic.claude-*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# DynamoDB Access for Job Tracking
# -----------------------------------------------------------------------------
resource "aws_iam_role_policy" "dynamodb_access" {
  name = "${local.full_name}-dynamodb"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DynamoDBUpdateJob"
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:PutItem"
        ]
        Resource = [
          local.dynamodb.clinical_pdf_jobs.table_arn
        ]
      }
    ]
  })
}
