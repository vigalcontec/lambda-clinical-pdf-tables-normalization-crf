# =============================================================================
# SSM Parameter Imports - Datalake Configuration
# =============================================================================
# These parameters are created by aws-datalake-layers and used to configure
# Lambda access to datalake buckets and KMS keys

# -----------------------------------------------------------------------------
# Raw Layer
# -----------------------------------------------------------------------------
data "aws_ssm_parameter" "raw_bucket_name" {
  name            = "/${var.environment}/datalake/raw/bucket_name"
  with_decryption = true
}

data "aws_ssm_parameter" "raw_bucket_arn" {
  name            = "/${var.environment}/datalake/raw/bucket_arn"
  with_decryption = true
}

data "aws_ssm_parameter" "raw_kms_key_arn" {
  name            = "/${var.environment}/datalake/raw/kms_key_arn"
  with_decryption = true
}

# -----------------------------------------------------------------------------
# Staging Layer
# -----------------------------------------------------------------------------
data "aws_ssm_parameter" "staging_bucket_name" {
  name            = "/${var.environment}/datalake/staging/bucket_name"
  with_decryption = true
}

data "aws_ssm_parameter" "staging_bucket_arn" {
  name            = "/${var.environment}/datalake/staging/bucket_arn"
  with_decryption = true
}

data "aws_ssm_parameter" "staging_kms_key_arn" {
  name            = "/${var.environment}/datalake/staging/kms_key_arn"
  with_decryption = true
}

# -----------------------------------------------------------------------------
# Business Layer
# -----------------------------------------------------------------------------
data "aws_ssm_parameter" "business_bucket_name" {
  name            = "/${var.environment}/datalake/business/bucket_name"
  with_decryption = true
}

data "aws_ssm_parameter" "business_bucket_arn" {
  name            = "/${var.environment}/datalake/business/bucket_arn"
  with_decryption = true
}

data "aws_ssm_parameter" "business_kms_key_arn" {
  name            = "/${var.environment}/datalake/business/kms_key_arn"
  with_decryption = true
}

# -----------------------------------------------------------------------------
# DynamoDB Configuration (from dynamodb-clinical-pdf-jobs-crf)
# -----------------------------------------------------------------------------
data "aws_ssm_parameter" "dynamodb_table_name" {
  name            = "/${var.environment}/${local.project_name}/dynamodb/clinical-pdf-jobs-crf/table_name"
  with_decryption = true
}

data "aws_ssm_parameter" "dynamodb_table_arn" {
  name            = "/${var.environment}/${local.project_name}/dynamodb/clinical-pdf-jobs-crf/table_arn"
  with_decryption = true
}

# -----------------------------------------------------------------------------
# Local Variables for Easy Access
# -----------------------------------------------------------------------------
locals {
  datalake = {
    raw = {
      bucket_name = data.aws_ssm_parameter.raw_bucket_name.value
      bucket_arn  = data.aws_ssm_parameter.raw_bucket_arn.value
      kms_key_arn = data.aws_ssm_parameter.raw_kms_key_arn.value
    }
    staging = {
      bucket_name = data.aws_ssm_parameter.staging_bucket_name.value
      bucket_arn  = data.aws_ssm_parameter.staging_bucket_arn.value
      kms_key_arn = data.aws_ssm_parameter.staging_kms_key_arn.value
    }
    business = {
      bucket_name = data.aws_ssm_parameter.business_bucket_name.value
      bucket_arn  = data.aws_ssm_parameter.business_bucket_arn.value
      kms_key_arn = data.aws_ssm_parameter.business_kms_key_arn.value
    }
  }

  dynamodb = {
    clinical_pdf_jobs = {
      table_name = data.aws_ssm_parameter.dynamodb_table_name.value
      table_arn  = data.aws_ssm_parameter.dynamodb_table_arn.value
    }
  }
}
