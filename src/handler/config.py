"""Configuration management using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    These are set by Terraform in the Lambda function configuration.
    See terraform/main.tf for the environment variables.
    """

    model_config = SettingsConfigDict(case_sensitive=False)

    # From Terraform environment variables
    environment: str = "dev"
    aws_region: str = "eu-west-1"
    log_level: str = "INFO"

    # DynamoDB configuration (from SSM via Terraform)
    dynamodb_table_name: str = ""

    # Bedrock configuration (v1 is available in eu-west-1, v2 requires cross-region)
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"

    # S3 configuration (from SSM via Terraform)
    business_bucket_name: str = ""
    output_prefix: str = "crf/clinical_tables"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
