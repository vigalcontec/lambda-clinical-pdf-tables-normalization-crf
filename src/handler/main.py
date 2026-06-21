"""AWS Lambda Handler - Clinical PDF Tables Normalization.

This Lambda function normalizes table data extracted by Textract using Claude AI.
It receives the Textract output from the previous step in the Step Function,
uses Claude to normalize/flatten the data, and updates DynamoDB with the results.
"""

from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from handler.config import get_settings
from handler.prompts import get_system_prompt
from handler.utils import (
    increment_normalization_failed,
    increment_tables_normalized,
    normalize_table_with_claude,
    record_table_status,
    update_job_status_if_complete,
    update_table_with_normalized_data,
    write_jsonl_to_s3,
)

logger = Logger()
tracer = Tracer()


def _extract_job_id_from_events_key(events_s3_key: str | None) -> str | None:
    """Extract job_id from the events S3 key.

    The events file path is used to derive a unique job identifier.
    """
    if not events_s3_key:
        return None

    # Extract directory path (everything before the filename)
    parts = events_s3_key.rsplit("/", 1)
    if len(parts) == 2:
        import hashlib

        return hashlib.sha256(parts[0].encode()).hexdigest()
    return None


def _detect_table_type(table_name: str) -> str | None:
    """Detect table type from table name for prompt selection.

    Args:
        table_name: The table title/name

    Returns:
        Table type hint or None
    """
    table_name_lower = table_name.lower()

    # Efficacy indicators
    if any(
        term in table_name_lower
        for term in [
            "efficacy",
            "response",
            "survival",
            "pfs",
            "os ",
            "orr",
            "dfs",
            "hazard",
            "endpoint",
        ]
    ):
        return "efficacy"

    # Adverse events indicators
    if any(
        term in table_name_lower
        for term in [
            "adverse",
            "safety",
            "toxicity",
            "side effect",
            "reaction",
            "tolerability",
        ]
    ):
        return "adverse_events"

    # Dosing indicators
    if any(
        term in table_name_lower
        for term in ["dose", "dosing", "dosage", "administration", "modification", "adjustment"]
    ):
        return "dosing"

    return None


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], _context: LambdaContext) -> dict[str, Any]:
    """Lambda handler for table data normalization using Claude AI.

    Expected event payload from Textract Lambda (via Step Function):
        {
            "status": "SUCCESS",
            "s3_bucket": "bucket-name",
            "s3_key": "path/to/document.pdf",
            "product_name": "keytruda",
            "table_name": "Table 6: Efficacy results...",
            "table_number": 6,
            "pages_processed": [32],
            "table_index_on_page": 0,
            "tables_found_on_page": 2,
            "table": {
                "rows": [["Header1", "Header2"], ["Value1", "Value2"]],
                "row_count": 2,
                "column_count": 2,
                "confidence": 98.5
            },
            "events_s3_key": "path/to/events.json"
        }

    Returns:
        {
            "status": "SUCCESS",
            "s3_bucket": "bucket-name",
            "s3_key": "path/to/document.pdf",
            "product_name": "keytruda",
            "table_name": "Table 6: Efficacy results...",
            "table_number": 6,
            "page": 32,
            "normalized_data": {...},
            "normalization_status": "NORMALIZED"
        }
    """
    settings = get_settings()
    logger.info("Starting table normalization", extra={"environment": settings.environment})

    # Get job_id from event (passed from Locator Lambda) or extract from path as fallback
    job_id = event.get("job_id")
    if not job_id:
        events_s3_key = event.get("events_s3_key")
        job_id = _extract_job_id_from_events_key(events_s3_key)
    dynamodb_table = settings.dynamodb_table_name

    # Check if previous step failed
    if event.get("status") == "FAILED":
        logger.warning("Skipping normalization - Textract step failed")
        if job_id and dynamodb_table:
            increment_normalization_failed(
                dynamodb_table, job_id, event.get("error", "Textract extraction failed")
            )
            update_job_status_if_complete(dynamodb_table, job_id)
        return {
            "status": "SKIPPED",
            "reason": "Textract extraction failed",
            "original_error": event.get("error"),
            **{k: event.get(k) for k in ["s3_bucket", "s3_key", "product_name", "table_name", "table_number"]},
        }

    try:
        # Extract event data
        bucket = event.get("s3_bucket")
        key = event.get("s3_key")
        product_name = event.get("product_name", "")
        table_name = event.get("table_name", "")
        table_number = event.get("table_number")
        table_data = event.get("table")
        pages_processed = event.get("pages_processed", [])
        page = pages_processed[0] if pages_processed else event.get("page", 0)
        formulations = event.get("formulations", [])
        formulation_key = event.get("formulation_key", "")

        if not table_data:
            logger.warning("No table data to normalize")
            return {
                "status": "SKIPPED",
                "reason": "No table data provided",
                "s3_bucket": bucket,
                "s3_key": key,
                "product_name": product_name,
                "table_name": table_name,
                "table_number": table_number,
                "page": page,
            }

        logger.info(
            "Normalizing table",
            extra={
                "product_name": product_name,
                "table_name": table_name,
                "table_number": table_number,
                "page": page,
                "row_count": table_data.get("row_count"),
                "column_count": table_data.get("column_count"),
            },
        )

        # Detect table type and get appropriate prompt
        table_type = _detect_table_type(table_name)
        system_prompt = get_system_prompt(table_type)

        # Normalize table using Claude
        normalized_data = normalize_table_with_claude(
            table_data=table_data,
            table_name=table_name,
            product_name=product_name,
            system_prompt=system_prompt,
        )

        # Check if normalization was successful
        normalization_status = "NORMALIZED"
        if normalized_data.get("normalized") is False:
            normalization_status = "NORMALIZATION_FAILED"
            logger.warning(
                "Table normalization produced unparseable output",
                extra={"parse_error": normalized_data.get("parse_error")},
            )

        # Update DynamoDB with normalized data
        if job_id and dynamodb_table:
            try:
                update_table_with_normalized_data(
                    table_name=dynamodb_table,
                    job_id=job_id,
                    table_number=table_number or 0,
                    page=page,
                    normalized_data=normalized_data,
                    status=normalization_status,
                )
                increment_tables_normalized(dynamodb_table, job_id)
                update_job_status_if_complete(dynamodb_table, job_id)
            except Exception as db_error:
                logger.warning(
                    "Failed to update DynamoDB",
                    extra={"error": str(db_error), "job_id": job_id},
                )

        # Write JSONL to S3 (business layer) with adaptive schema
        output_uri = None
        if settings.business_bucket_name and normalization_status == "NORMALIZED":
            try:
                output_uri = write_jsonl_to_s3(
                    normalized_data=normalized_data,
                    job_id=job_id or "unknown",
                    product_name=product_name,
                    table_name=table_name,
                    table_number=table_number or 0,
                    page=page,
                    s3_key=key or "",
                    bucket=settings.business_bucket_name,
                    output_prefix=settings.output_prefix,
                    formulations=formulations,
                    formulation_key=formulation_key,
                )
            except Exception as s3_error:
                logger.warning(
                    "Failed to write JSONL to S3",
                    extra={"error": str(s3_error)},
                )

        # Record table status for incremental reprocessing
        if job_id and dynamodb_table:
            try:
                record_table_status(
                    table_name=dynamodb_table,
                    job_id=job_id,
                    table_number=table_number or 0,
                    page=page,
                    status="SUCCESS",
                    output_uri=output_uri,
                )
            except Exception as db_error:
                logger.warning(
                    "Failed to record table status",
                    extra={"error": str(db_error), "job_id": job_id},
                )

        logger.info(
            "Table normalization completed",
            extra={
                "normalization_status": normalization_status,
                "table_type_detected": table_type,
                "output_uri": output_uri,
            },
        )

        return {
            "status": "SUCCESS",
            "job_id": job_id,
            "s3_bucket": bucket,
            "s3_key": key,
            "product_name": product_name,
            "table_name": table_name,
            "table_number": table_number,
            "page": page,
            "formulations": formulations,
            "formulation_key": formulation_key,
            "table_type_detected": table_type,
            "normalized_data": normalized_data,
            "normalization_status": normalization_status,
            "output_uri": output_uri,
        }

    except Exception as e:
        logger.exception("Error normalizing table")

        # Get page for error tracking
        pages_processed = event.get("pages_processed", [])
        error_page = pages_processed[0] if pages_processed else event.get("page", 0)
        error_table_number = event.get("table_number", 0)

        # Update DynamoDB: increment failed counter and record table status
        if job_id and dynamodb_table:
            try:
                increment_normalization_failed(dynamodb_table, job_id, str(e))
                record_table_status(
                    table_name=dynamodb_table,
                    job_id=job_id,
                    table_number=error_table_number or 0,
                    page=error_page,
                    status="FAILED",
                    error_message=str(e),
                )
                update_job_status_if_complete(dynamodb_table, job_id)
            except Exception as db_error:
                logger.warning(
                    "Failed to update DynamoDB on error",
                    extra={"error": str(db_error), "job_id": job_id},
                )

        return {
            "status": "FAILED",
            "job_id": job_id,
            "error": str(e),
            "s3_bucket": event.get("s3_bucket"),
            "s3_key": event.get("s3_key"),
            "product_name": event.get("product_name"),
            "table_name": event.get("table_name"),
            "table_number": event.get("table_number"),
            "page": error_page,
        }
