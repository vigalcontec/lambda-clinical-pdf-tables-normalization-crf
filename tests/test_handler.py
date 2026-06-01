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
