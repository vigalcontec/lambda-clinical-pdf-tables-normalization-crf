"""Pytest fixtures and configuration."""

import os

# Set AWS region before importing any modules that use boto3
os.environ["AWS_DEFAULT_REGION"] = "eu-west-1"
os.environ["AWS_REGION"] = "eu-west-1"

# Disable X-Ray tracing before importing any modules
os.environ["POWERTOOLS_TRACE_DISABLED"] = "true"

# Set DynamoDB and Bedrock config for tests
os.environ["DYNAMODB_TABLE_NAME"] = "test-clinical-pdf-jobs"
os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-3-5-sonnet-20241022-v2:0"

# Set S3 config for tests
os.environ["BUSINESS_BUCKET_NAME"] = "test-business-bucket"
os.environ["OUTPUT_PREFIX"] = "crf/clinical_tables"

from collections.abc import Generator  # noqa: E402
from typing import Any  # noqa: E402
from unittest.mock import patch  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def env_vars() -> Generator[None, None, None]:
    """Set environment variables for tests."""
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "dev",
            "AWS_REGION": "eu-west-1",
            "LOG_LEVEL": "INFO",
            "DYNAMODB_TABLE_NAME": "test-clinical-pdf-jobs",
            "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "BUSINESS_BUCKET_NAME": "test-business-bucket",
            "OUTPUT_PREFIX": "crf/clinical_tables",
        },
    ):
        yield


@pytest.fixture
def lambda_event() -> dict[str, Any]:
    """Sample Lambda event from Textract Lambda."""
    return {
        "status": "SUCCESS",
        "s3_bucket": "test-bucket",
        "s3_key": "crf/clinical_pdfs/keytruda/20260522164300/keytruda-epar.pdf",
        "product_name": "keytruda",
        "table_name": "Table 7: Efficacy results by BRAF mutation status in KEYNOTE-006",
        "table_number": 7,
        "pages_processed": [32],
        "table_index_on_page": 1,
        "tables_found_on_page": 2,
        "table": {
            "rows": [
                ["Endpoint", "Pembrolizumab", "Ipilimumab"],
                ["ORR", "33.7%", "11.9%"],
                ["PFS (months)", "5.5", "2.8"],
            ],
            "row_count": 3,
            "column_count": 3,
            "confidence": 98.5,
        },
        "events_s3_key": "crf/clinical_pdfs/keytruda/20260522164300/keytruda-epar_events.json",
    }


@pytest.fixture
def lambda_event_failed() -> dict[str, Any]:
    """Sample Lambda event when Textract failed."""
    return {
        "status": "FAILED",
        "error": "Textract extraction failed",
        "s3_bucket": "test-bucket",
        "s3_key": "crf/clinical_pdfs/keytruda/20260522164300/keytruda-epar.pdf",
        "product_name": "keytruda",
        "table_name": "Table 7: Efficacy results",
        "table_number": 7,
    }


@pytest.fixture
def lambda_context() -> Any:
    """Mock Lambda context."""

    class MockContext:
        function_name = "test-function"
        memory_limit_in_mb = 512
        invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789012:function:test"
        aws_request_id = "test-request-id"

    return MockContext()


@pytest.fixture
def normalized_table_response() -> dict[str, Any]:
    """Sample normalized table response from Claude."""
    return {
        "table_type": "efficacy_results",
        "headers": [
            {"name": "Endpoint", "level": 0, "span": 1},
            {"name": "Pembrolizumab", "level": 0, "span": 1},
            {"name": "Ipilimumab", "level": 0, "span": 1},
        ],
        "rows": [
            {
                "row_type": "data",
                "cells": [
                    {"value": "ORR", "column_index": 0},
                    {"value": "33.7%", "normalized_value": {"value": 33.7, "unit": "%"}, "column_index": 1},
                    {"value": "11.9%", "normalized_value": {"value": 11.9, "unit": "%"}, "column_index": 2},
                ],
            },
            {
                "row_type": "data",
                "cells": [
                    {"value": "PFS (months)", "column_index": 0},
                    {"value": "5.5", "normalized_value": {"value": 5.5, "unit": "months"}, "column_index": 1},
                    {"value": "2.8", "normalized_value": {"value": 2.8, "unit": "months"}, "column_index": 2},
                ],
            },
        ],
        "metadata": {
            "treatment_arms": ["Pembrolizumab", "Ipilimumab"],
            "endpoints": ["ORR", "PFS"],
        },
    }
