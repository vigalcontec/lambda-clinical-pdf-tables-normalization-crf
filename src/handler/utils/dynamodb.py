"""DynamoDB utility functions for updating normalized table data."""

from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()


@lru_cache
def _get_dynamodb_resource() -> Any:
    """Get cached DynamoDB resource."""
    return boto3.resource("dynamodb")


@tracer.capture_method
def update_table_with_normalized_data(
    table_name: str,
    job_id: str,
    table_number: int,
    page: int,
    normalized_data: dict[str, Any],
    status: str = "NORMALIZED",
) -> None:
    """Update a table record with normalized data.

    Args:
        table_name: DynamoDB table name
        job_id: Job identifier
        table_number: Table number in the document
        page: Page number where table was found
        normalized_data: Normalized table data from Claude
        status: New status (default NORMALIZED)
    """
    if not table_name:
        logger.warning("DynamoDB table name not configured, skipping update")
        return

    table = _get_dynamodb_resource().Table(table_name)
    now = datetime.now(UTC).isoformat()

    logger.info(
        "Updating table record with normalized data",
        extra={
            "job_id": job_id,
            "table_number": table_number,
            "page": page,
        },
    )

    table.update_item(
        Key={"PK": f"JOB#{job_id}", "SK": f"TABLE#{table_number}#PAGE#{page}"},
        UpdateExpression="SET normalized_data = :data, #status = :status, normalized_at = :now, updated_at = :now",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":data": normalized_data,
            ":status": status,
            ":now": now,
        },
    )


@tracer.capture_method
def increment_tables_normalized(
    table_name: str,
    job_id: str,
) -> None:
    """Increment tables_normalized counter for a job.

    Args:
        table_name: DynamoDB table name
        job_id: Job identifier
    """
    if not table_name:
        logger.warning("DynamoDB table name not configured, skipping update")
        return

    table = _get_dynamodb_resource().Table(table_name)
    now = datetime.now(UTC).isoformat()

    logger.info("Incrementing tables_normalized", extra={"job_id": job_id})

    # Use ADD to increment, with a default of 0 if the attribute doesn't exist
    table.update_item(
        Key={"PK": f"JOB#{job_id}", "SK": "METADATA"},
        UpdateExpression="SET tables_normalized = if_not_exists(tables_normalized, :zero) + :inc, updated_at = :now",
        ExpressionAttributeValues={
            ":inc": 1,
            ":zero": 0,
            ":now": now,
        },
    )


@tracer.capture_method
def increment_normalization_failed(
    table_name: str,
    job_id: str,
    error_message: str | None = None,
) -> None:
    """Increment normalization_failed counter for a job.

    Args:
        table_name: DynamoDB table name
        job_id: Job identifier
        error_message: Optional error message to store
    """
    if not table_name:
        logger.warning("DynamoDB table name not configured, skipping update")
        return

    table = _get_dynamodb_resource().Table(table_name)
    now = datetime.now(UTC).isoformat()

    update_expr = "SET normalization_failed = if_not_exists(normalization_failed, :zero) + :inc, updated_at = :now"
    expr_values: dict[str, Any] = {
        ":inc": 1,
        ":zero": 0,
        ":now": now,
    }

    if error_message:
        update_expr += ", last_normalization_error = :error"
        expr_values[":error"] = error_message

    logger.info("Incrementing normalization_failed", extra={"job_id": job_id})
    table.update_item(
        Key={"PK": f"JOB#{job_id}", "SK": "METADATA"},
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expr_values,
    )


@tracer.capture_method
def update_job_status_if_complete(
    table_name: str,
    job_id: str,
) -> bool:
    """Check if all tables are normalized and update job status if complete.

    Args:
        table_name: DynamoDB table name
        job_id: Job identifier

    Returns:
        True if job is complete, False otherwise
    """
    if not table_name:
        logger.warning("DynamoDB table name not configured, skipping check")
        return False

    table = _get_dynamodb_resource().Table(table_name)

    # Get current job metadata
    response = table.get_item(Key={"PK": f"JOB#{job_id}", "SK": "METADATA"})
    item = response.get("Item")

    if not item:
        logger.warning("Job metadata not found", extra={"job_id": job_id})
        return False

    total_tables = item.get("textract_events_count", 0)
    tables_normalized = item.get("tables_normalized", 0)
    normalization_failed = item.get("normalization_failed", 0)

    # Check if all tables have been processed
    if tables_normalized + normalization_failed >= total_tables:
        now = datetime.now(UTC).isoformat()
        new_status = "COMPLETED" if normalization_failed == 0 else "COMPLETED_WITH_ERRORS"

        logger.info(
            "Job normalization complete",
            extra={
                "job_id": job_id,
                "total_tables": total_tables,
                "tables_normalized": tables_normalized,
                "normalization_failed": normalization_failed,
                "new_status": new_status,
            },
        )

        table.update_item(
            Key={"PK": f"JOB#{job_id}", "SK": "METADATA"},
            UpdateExpression="SET #status = :status, completed_at = :now, updated_at = :now, GSI1PK = :gsi1pk, GSI1SK = :gsi1sk",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": new_status,
                ":now": now,
                ":gsi1pk": f"STATUS#{new_status}",
                ":gsi1sk": now,
            },
        )
        return True

    return False
