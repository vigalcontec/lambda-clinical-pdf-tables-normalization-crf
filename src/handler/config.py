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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
