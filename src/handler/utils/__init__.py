"""Utility modules."""

from handler.utils.bedrock import invoke_claude, normalize_table_with_claude
from handler.utils.dynamodb import (
    increment_normalization_failed,
    increment_tables_normalized,
    update_job_status_if_complete,
    update_table_with_normalized_data,
)
from handler.utils.s3 import write_jsonl_to_s3
from handler.utils.ssm import get_parameter, get_parameters_by_path

__all__ = [
    # SSM
    "get_parameter",
    "get_parameters_by_path",
    # Bedrock
    "invoke_claude",
    "normalize_table_with_claude",
    # DynamoDB
    "update_table_with_normalized_data",
    "increment_tables_normalized",
    "increment_normalization_failed",
    "update_job_status_if_complete",
    # S3
    "write_jsonl_to_s3",
]
