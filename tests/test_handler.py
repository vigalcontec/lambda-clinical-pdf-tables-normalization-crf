"""Tests for Lambda handler."""

from typing import Any
from unittest.mock import MagicMock, patch

from handler.config import Settings, get_settings


class TestHandler:
    """Tests for main handler function."""

    @patch("handler.main.normalize_table_with_claude")
    @patch("handler.main.update_table_with_normalized_data")
    @patch("handler.main.increment_tables_normalized")
    @patch("handler.main.update_job_status_if_complete")
    def test_handler_success(
        self,
        mock_update_status: MagicMock,
        mock_increment: MagicMock,
        mock_update_table: MagicMock,
        mock_normalize: MagicMock,
        lambda_event: dict[str, Any],
        lambda_context: Any,
        normalized_table_response: dict[str, Any],
    ) -> None:
        """Test successful handler execution."""
        get_settings.cache_clear()
        mock_normalize.return_value = normalized_table_response

        from handler.main import handler

        result = handler(lambda_event, lambda_context)

        assert result["status"] == "SUCCESS"
        assert result["product_name"] == "keytruda"
        assert result["table_number"] == 7
        assert result["normalization_status"] == "NORMALIZED"
        assert result["normalized_data"] == normalized_table_response
        mock_normalize.assert_called_once()

    @patch("handler.main.increment_normalization_failed")
    @patch("handler.main.update_job_status_if_complete")
    def test_handler_skips_failed_textract(
        self,
        mock_update_status: MagicMock,
        mock_increment_failed: MagicMock,
        lambda_event_failed: dict[str, Any],
        lambda_context: Any,
    ) -> None:
        """Test handler skips normalization when Textract failed."""
        get_settings.cache_clear()

        from handler.main import handler

        result = handler(lambda_event_failed, lambda_context)

        assert result["status"] == "SKIPPED"
        assert result["reason"] == "Textract extraction failed"

    def test_handler_skips_no_table_data(self, lambda_context: Any) -> None:
        """Test handler skips when no table data provided."""
        get_settings.cache_clear()

        from handler.main import handler

        event = {
            "status": "SUCCESS",
            "s3_bucket": "bucket",
            "s3_key": "key.pdf",
            "product_name": "test",
            "table_name": "Table 1",
            "table_number": 1,
            # No "table" key
        }

        result = handler(event, lambda_context)

        assert result["status"] == "SKIPPED"
        assert result["reason"] == "No table data provided"


class TestConfig:
    """Tests for configuration."""

    def test_get_settings_returns_settings(self) -> None:
        """Test get_settings returns Settings instance."""
        get_settings.cache_clear()
        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_get_settings_cached(self) -> None:
        """Test get_settings returns cached instance."""
        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_settings_default_values(self) -> None:
        """Test Settings has correct default values."""
        get_settings.cache_clear()
        settings = get_settings()

        assert settings.environment == "dev"
        assert settings.aws_region == "eu-west-1"
        assert settings.log_level == "INFO"

    def test_settings_from_env(self) -> None:
        """Test Settings reads from environment variables."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"ENVIRONMENT": "prod", "LOG_LEVEL": "DEBUG"}):
            get_settings.cache_clear()
            settings = get_settings()

            assert settings.environment == "prod"
            assert settings.log_level == "DEBUG"


class TestBedrockUtils:
    """Tests for Bedrock utility functions."""

    def test_build_claude_request(self) -> None:
        """Test _build_claude_request creates correct format."""
        from handler.utils.bedrock import _build_claude_request

        result = _build_claude_request(
            prompt="Test prompt",
            system_prompt="System prompt",
            max_tokens=4096,
            temperature=0.0,
        )

        assert result["anthropic_version"] == "bedrock-2023-05-31"
        assert result["max_tokens"] == 4096
        assert result["temperature"] == 0.0
        assert result["messages"] == [{"role": "user", "content": "Test prompt"}]
        assert result["system"] == "System prompt"

    def test_build_claude_request_no_system_prompt(self) -> None:
        """Test _build_claude_request without system prompt."""
        from handler.utils.bedrock import _build_claude_request

        result = _build_claude_request(
            prompt="Test prompt",
            system_prompt=None,
            max_tokens=1000,
            temperature=0.5,
        )

        assert "system" not in result
        assert result["max_tokens"] == 1000

    def test_build_nova_request(self) -> None:
        """Test _build_nova_request creates correct format with schemaVersion and maxTokens."""
        from handler.utils.bedrock import _build_nova_request

        result = _build_nova_request(
            prompt="Test prompt",
            system_prompt="System prompt",
            max_tokens=4096,
            temperature=0.0,
        )

        assert result["schemaVersion"] == "messages-v1"
        assert "inferenceConfig" in result
        assert result["inferenceConfig"]["maxTokens"] == 4096
        assert result["inferenceConfig"]["temperature"] == 0.0
        assert result["messages"] == [{"role": "user", "content": [{"text": "Test prompt"}]}]
        assert result["system"] == [{"text": "System prompt"}]

    def test_build_nova_request_no_system_prompt(self) -> None:
        """Test _build_nova_request without system prompt."""
        from handler.utils.bedrock import _build_nova_request

        result = _build_nova_request(
            prompt="Test prompt",
            system_prompt=None,
            max_tokens=2000,
            temperature=0.7,
        )

        assert result["schemaVersion"] == "messages-v1"
        assert "system" not in result
        assert result["inferenceConfig"]["maxTokens"] == 2000
        assert result["inferenceConfig"]["temperature"] == 0.7

    @patch("handler.utils.bedrock._get_bedrock_client")
    def test_invoke_claude(self, mock_get_client: MagicMock) -> None:
        """Test invoke_claude calls Bedrock API."""
        from handler.utils.bedrock import invoke_claude

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: b'{"content": [{"text": "Test response"}], "usage": {"input_tokens": 10, "output_tokens": 5}}'
            )
        }

        result = invoke_claude("Test prompt", system_prompt="System prompt")

        assert result == "Test response"
        mock_client.invoke_model.assert_called_once()

    @patch("handler.utils.bedrock._get_bedrock_client")
    def test_invoke_claude_no_system_prompt(self, mock_get_client: MagicMock) -> None:
        """Test invoke_claude without system prompt."""
        from handler.utils.bedrock import invoke_claude

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: b'{"content": [{"text": "Response"}], "usage": {}}'
            )
        }

        result = invoke_claude("Test prompt")

        assert result == "Response"

    @patch("handler.utils.bedrock.get_settings")
    @patch("handler.utils.bedrock._get_bedrock_client")
    def test_invoke_model_with_nova(self, mock_get_client: MagicMock, mock_settings: MagicMock) -> None:
        """Test invoke_model uses Nova format when model ID starts with amazon.nova."""
        from handler.utils.bedrock import invoke_model

        # Configure mock settings for Nova model
        mock_settings.return_value.bedrock_model_id = "eu.amazon.nova-pro-v1:0"

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: b'{"output": {"message": {"content": [{"text": "Nova response"}]}}, "usage": {"inputTokens": 10, "outputTokens": 5}}'
            )
        }

        result = invoke_model("Test prompt", system_prompt="System prompt")

        assert result == "Nova response"
        mock_client.invoke_model.assert_called_once()

    def test_parse_nova_response(self) -> None:
        """Test _parse_nova_response extracts text and usage correctly."""
        from handler.utils.bedrock import _parse_nova_response

        response_body = {
            "output": {"message": {"content": [{"text": "Nova output"}]}},
            "usage": {"inputTokens": 100, "outputTokens": 50},
        }

        text, usage = _parse_nova_response(response_body)

        assert text == "Nova output"
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50

    def test_parse_claude_response(self) -> None:
        """Test _parse_claude_response extracts text and usage correctly."""
        from handler.utils.bedrock import _parse_claude_response

        response_body = {
            "content": [{"text": "Claude output"}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }

        text, usage = _parse_claude_response(response_body)

        assert text == "Claude output"
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50

    @patch("handler.utils.bedrock.invoke_claude")
    def test_normalize_table_with_claude_json_response(
        self, mock_invoke: MagicMock
    ) -> None:
        """Test normalize_table_with_claude parses JSON response."""
        from handler.utils.bedrock import normalize_table_with_claude

        mock_invoke.return_value = '```json\n{"table_type": "efficacy", "rows": []}\n```'

        result = normalize_table_with_claude(
            table_data={"rows": [["A", "B"]], "row_count": 1, "column_count": 2},
            table_name="Table 1",
            product_name="test",
            system_prompt="Normalize this table",
        )

        assert result["table_type"] == "efficacy"
        assert result["rows"] == []

    @patch("handler.utils.bedrock.invoke_claude")
    def test_normalize_table_with_claude_plain_json(
        self, mock_invoke: MagicMock
    ) -> None:
        """Test normalize_table_with_claude parses plain JSON."""
        from handler.utils.bedrock import normalize_table_with_claude

        mock_invoke.return_value = '{"table_type": "safety", "rows": []}'

        result = normalize_table_with_claude(
            table_data={"rows": [], "row_count": 0, "column_count": 0},
            table_name="Table 2",
            product_name="test",
            system_prompt="Normalize",
        )

        assert result["table_type"] == "safety"

    @patch("handler.utils.bedrock.invoke_claude")
    def test_normalize_table_with_claude_code_block(
        self, mock_invoke: MagicMock
    ) -> None:
        """Test normalize_table_with_claude parses code block without json tag."""
        from handler.utils.bedrock import normalize_table_with_claude

        mock_invoke.return_value = '```\n{"table_type": "demographics"}\n```'

        result = normalize_table_with_claude(
            table_data={"rows": [], "row_count": 0, "column_count": 0},
            table_name="Table 3",
            product_name="test",
            system_prompt="Normalize",
        )

        assert result["table_type"] == "demographics"

    @patch("handler.utils.bedrock.invoke_claude")
    def test_normalize_table_with_claude_invalid_json(
        self, mock_invoke: MagicMock
    ) -> None:
        """Test normalize_table_with_claude handles invalid JSON."""
        from handler.utils.bedrock import normalize_table_with_claude

        mock_invoke.return_value = "This is not valid JSON"

        result = normalize_table_with_claude(
            table_data={"rows": [], "row_count": 0, "column_count": 0},
            table_name="Table 4",
            product_name="test",
            system_prompt="Normalize",
        )

        assert result["normalized"] is False
        assert "parse_error" in result
        assert "raw_response" in result


class TestS3Utils:
    """Tests for S3 utility functions."""

    def test_parse_numeric_value_percentage(self) -> None:
        """Test parsing percentage values."""
        from handler.utils.s3 import _parse_numeric_value

        assert _parse_numeric_value("33.7%") == 33.7
        assert _parse_numeric_value("100%") == 100.0

    def test_parse_numeric_value_range(self) -> None:
        """Test parsing range values."""
        from handler.utils.s3 import _parse_numeric_value

        assert _parse_numeric_value("5.5-7.2") == 5.5

    def test_parse_numeric_value_inequality(self) -> None:
        """Test parsing inequality values."""
        from handler.utils.s3 import _parse_numeric_value

        assert _parse_numeric_value("<0.001") == 0.001
        assert _parse_numeric_value(">50") == 50.0
        assert _parse_numeric_value("≤10") == 10.0

    def test_parse_numeric_value_none(self) -> None:
        """Test parsing None or empty values."""
        from handler.utils.s3 import _parse_numeric_value

        assert _parse_numeric_value(None) is None
        assert _parse_numeric_value("") is None
        assert _parse_numeric_value("N/A") is None

    def test_extract_confidence_interval(self) -> None:
        """Test extracting confidence interval."""
        from handler.utils.s3 import _extract_confidence_interval

        cell = {
            "normalized_value": {
                "ci_lower": 1.5,
                "ci_upper": 3.2,
                "ci_level": 95,
            }
        }
        result = _extract_confidence_interval(cell)

        assert result["lower"] == 1.5
        assert result["upper"] == 3.2
        assert result["level"] == 95

    def test_extract_confidence_interval_none(self) -> None:
        """Test extracting confidence interval when not present."""
        from handler.utils.s3 import _extract_confidence_interval

        assert _extract_confidence_interval({}) is None
        assert _extract_confidence_interval({"normalized_value": "string"}) is None

    def test_transform_to_adaptive_schema(
        self, normalized_table_response: dict[str, Any]
    ) -> None:
        """Test transforming normalized data to adaptive schema."""
        from handler.utils.s3 import transform_to_adaptive_schema

        records = transform_to_adaptive_schema(
            normalized_data=normalized_table_response,
            job_id="test-job-123",
            product_name="keytruda",
            table_name="Table 7",
            table_number=7,
            page=32,
            s3_key="test/doc.pdf",
            bucket="test-bucket",
        )

        assert len(records) == 2  # Two data rows
        assert records[0]["source"]["product_name"] == "keytruda"
        assert records[0]["source"]["table_number"] == 7
        assert "clinical_data" in records[0]
        assert "attributes" in records[0]

    def test_transform_to_adaptive_schema_empty(self) -> None:
        """Test transforming empty normalized data."""
        from handler.utils.s3 import transform_to_adaptive_schema

        records = transform_to_adaptive_schema(
            normalized_data={"rows": [], "headers": []},
            job_id="test-job",
            product_name="test",
            table_name="Table 1",
            table_number=1,
            page=1,
            s3_key="test.pdf",
            bucket="bucket",
        )

        assert len(records) == 0

    @patch("handler.utils.s3._get_s3_client")
    def test_write_jsonl_to_s3(
        self,
        mock_get_client: MagicMock,
        normalized_table_response: dict[str, Any],
    ) -> None:
        """Test writing JSONL to S3."""
        from handler.utils.s3 import write_jsonl_to_s3

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = write_jsonl_to_s3(
            normalized_data=normalized_table_response,
            job_id="test-job-123456789",
            product_name="keytruda",
            table_name="Table 7",
            table_number=7,
            page=32,
            s3_key="test/doc.pdf",
            bucket="test-bucket",
        )

        assert result.startswith("s3://test-bucket/")
        assert "keytruda" in result
        assert ".jsonl" in result
        mock_client.put_object.assert_called_once()

    @patch("handler.utils.s3._get_s3_client")
    def test_write_jsonl_to_s3_empty_data(self, mock_get_client: MagicMock) -> None:
        """Test writing JSONL with empty data creates metadata record."""
        from handler.utils.s3 import write_jsonl_to_s3

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        result = write_jsonl_to_s3(
            normalized_data={"rows": [], "headers": []},
            job_id="test-job",
            product_name="test",
            table_name="Table 1",
            table_number=1,
            page=1,
            s3_key="test.pdf",
            bucket="bucket",
        )

        assert result.startswith("s3://bucket/")
        mock_client.put_object.assert_called_once()


class TestDynamoDBUtils:
    """Tests for DynamoDB utility functions."""

    @patch("handler.utils.dynamodb._get_dynamodb_resource")
    def test_update_table_with_normalized_data(self, mock_resource: MagicMock) -> None:
        """Test update_table_with_normalized_data updates DynamoDB."""
        from handler.utils.dynamodb import update_table_with_normalized_data

        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table

        update_table_with_normalized_data(
            table_name="test-table",
            job_id="job-123",
            table_number=7,
            page=32,
            normalized_data={"table_type": "efficacy"},
        )

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        assert call_args.kwargs["Key"] == {"PK": "JOB#job-123", "SK": "TABLE#7#PAGE#32"}

    def test_update_table_with_normalized_data_no_table(self) -> None:
        """Test update_table_with_normalized_data with no table name."""
        from handler.utils.dynamodb import update_table_with_normalized_data

        # Should not raise, just log warning
        update_table_with_normalized_data(
            table_name="",
            job_id="job-123",
            table_number=7,
            page=32,
            normalized_data={},
        )

    @patch("handler.utils.dynamodb._get_dynamodb_resource")
    def test_increment_tables_normalized(self, mock_resource: MagicMock) -> None:
        """Test increment_tables_normalized updates DynamoDB."""
        from handler.utils.dynamodb import increment_tables_normalized

        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table

        increment_tables_normalized("test-table", "job-123")

        mock_table.update_item.assert_called_once()

    def test_increment_tables_normalized_no_table(self) -> None:
        """Test increment_tables_normalized with no table name."""
        from handler.utils.dynamodb import increment_tables_normalized

        # Should not raise
        increment_tables_normalized("", "job-123")

    @patch("handler.utils.dynamodb._get_dynamodb_resource")
    def test_increment_normalization_failed(self, mock_resource: MagicMock) -> None:
        """Test increment_normalization_failed updates DynamoDB."""
        from handler.utils.dynamodb import increment_normalization_failed

        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table

        increment_normalization_failed("test-table", "job-123", "Test error")

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        assert ":error" in call_args.kwargs["ExpressionAttributeValues"]

    def test_increment_normalization_failed_no_table(self) -> None:
        """Test increment_normalization_failed with no table name."""
        from handler.utils.dynamodb import increment_normalization_failed

        # Should not raise
        increment_normalization_failed("", "job-123")

    @patch("handler.utils.dynamodb._get_dynamodb_resource")
    def test_update_job_status_if_complete_true(self, mock_resource: MagicMock) -> None:
        """Test update_job_status_if_complete when job is complete."""
        from handler.utils.dynamodb import update_job_status_if_complete

        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {
                "textract_events_count": 5,
                "tables_normalized": 5,
                "normalization_failed": 0,
            }
        }

        result = update_job_status_if_complete("test-table", "job-123")

        assert result is True
        mock_table.update_item.assert_called_once()

    @patch("handler.utils.dynamodb._get_dynamodb_resource")
    def test_update_job_status_if_complete_with_errors(
        self, mock_resource: MagicMock
    ) -> None:
        """Test update_job_status_if_complete with some failures."""
        from handler.utils.dynamodb import update_job_status_if_complete

        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {
                "textract_events_count": 5,
                "tables_normalized": 3,
                "normalization_failed": 2,
            }
        }

        result = update_job_status_if_complete("test-table", "job-123")

        assert result is True

    @patch("handler.utils.dynamodb._get_dynamodb_resource")
    def test_update_job_status_if_complete_not_done(
        self, mock_resource: MagicMock
    ) -> None:
        """Test update_job_status_if_complete when job is not complete."""
        from handler.utils.dynamodb import update_job_status_if_complete

        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {
                "textract_events_count": 10,
                "tables_normalized": 3,
                "normalization_failed": 0,
            }
        }

        result = update_job_status_if_complete("test-table", "job-123")

        assert result is False
        mock_table.update_item.assert_not_called()

    @patch("handler.utils.dynamodb._get_dynamodb_resource")
    def test_update_job_status_if_complete_no_item(
        self, mock_resource: MagicMock
    ) -> None:
        """Test update_job_status_if_complete when job not found."""
        from handler.utils.dynamodb import update_job_status_if_complete

        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {}

        result = update_job_status_if_complete("test-table", "job-123")

        assert result is False

    def test_update_job_status_if_complete_no_table(self) -> None:
        """Test update_job_status_if_complete with no table name."""
        from handler.utils.dynamodb import update_job_status_if_complete

        result = update_job_status_if_complete("", "job-123")

        assert result is False


class TestSSMUtils:
    """Tests for SSM utilities."""

    @patch("handler.utils.ssm.boto3.client")
    def test_get_parameter(self, mock_boto_client: MagicMock) -> None:
        """Test get_parameter fetches from SSM."""
        from handler.utils.ssm import get_parameter

        # Clear cache
        get_parameter.cache_clear()

        # Setup mock
        mock_ssm = MagicMock()
        mock_boto_client.return_value = mock_ssm
        mock_ssm.get_parameter.return_value = {
            "Parameter": {"Value": "test-value"}
        }

        # Act
        result = get_parameter("/dev/my-app/secret")

        # Assert
        assert result == "test-value"
        mock_ssm.get_parameter.assert_called_once_with(
            Name="/dev/my-app/secret", WithDecryption=True
        )

    @patch("handler.utils.ssm.boto3.client")
    def test_get_parameter_no_decrypt(self, mock_boto_client: MagicMock) -> None:
        """Test get_parameter with decrypt=False."""
        from handler.utils.ssm import get_parameter

        get_parameter.cache_clear()

        mock_ssm = MagicMock()
        mock_boto_client.return_value = mock_ssm
        mock_ssm.get_parameter.return_value = {
            "Parameter": {"Value": "plain-value"}
        }

        result = get_parameter("/dev/my-app/config", decrypt=False)

        assert result == "plain-value"
        mock_ssm.get_parameter.assert_called_once_with(
            Name="/dev/my-app/config", WithDecryption=False
        )

    @patch("handler.utils.ssm.boto3.client")
    def test_get_parameters_by_path(self, mock_boto_client: MagicMock) -> None:
        """Test get_parameters_by_path fetches all parameters under path."""
        from handler.utils.ssm import get_parameters_by_path

        mock_ssm = MagicMock()
        mock_boto_client.return_value = mock_ssm

        # Setup paginator mock
        mock_paginator = MagicMock()
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Parameters": [
                    {"Name": "/dev/my-app/db-host", "Value": "localhost"},
                    {"Name": "/dev/my-app/db-port", "Value": "5432"},
                ]
            }
        ]

        result = get_parameters_by_path("/dev/my-app/")

        assert result == {"db-host": "localhost", "db-port": "5432"}

    @patch("handler.utils.ssm.boto3.client")
    def test_get_parameters_by_path_empty(self, mock_boto_client: MagicMock) -> None:
        """Test get_parameters_by_path with no parameters."""
        from handler.utils.ssm import get_parameters_by_path

        mock_ssm = MagicMock()
        mock_boto_client.return_value = mock_ssm

        mock_paginator = MagicMock()
        mock_ssm.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"Parameters": []}]

        result = get_parameters_by_path("/dev/empty/")

        assert result == {}
