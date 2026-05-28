"""Pytest fixtures and configuration."""

import os

# Disable X-Ray tracing before importing any modules
os.environ["POWERTOOLS_TRACE_DISABLED"] = "true"

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
        },
    ):
        yield


@pytest.fixture
def lambda_event() -> dict[str, Any]:
    """Sample Lambda event."""
    return {"key1": "value1", "key2": "value2"}


@pytest.fixture
def lambda_context() -> Any:
    """Mock Lambda context."""

    class MockContext:
        function_name = "test-function"
        memory_limit_in_mb = 256
        invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789012:function:test"
        aws_request_id = "test-request-id"

    return MockContext()
