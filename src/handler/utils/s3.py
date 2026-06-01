"""S3 utility functions for writing JSON Lines files with adaptive schema."""

import json
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer

from handler.config import get_settings

logger = Logger()
tracer = Tracer()

# Schema version for backward compatibility
SCHEMA_VERSION = "1.0"


@lru_cache
def _get_s3_client() -> Any:
    """Get cached S3 client."""
    settings = get_settings()
    return boto3.client("s3", region_name=settings.aws_region)


def _parse_numeric_value(value: str | None) -> float | None:
    """Try to parse a numeric value from string.

    Handles percentages, ranges, and special formats.
    """
    if not value:
        return None

    # Remove common non-numeric characters
    cleaned = value.strip().replace(",", ".").replace(" ", "")

    # Handle percentages
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]

    # Handle ranges (take first value)
    if "-" in cleaned and not cleaned.startswith("-"):
        cleaned = cleaned.split("-")[0]

    # Handle inequalities
    for prefix in ["<", ">", "≤", "≥", "<=", ">="]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break

    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_confidence_interval(cell: dict[str, Any]) -> dict[str, Any] | None:
    """Extract confidence interval from normalized cell value."""
    normalized = cell.get("normalized_value", {})
    if isinstance(normalized, dict) and "ci_lower" in normalized and "ci_upper" in normalized:
        return {
            "lower": normalized.get("ci_lower"),
            "upper": normalized.get("ci_upper"),
            "level": normalized.get("ci_level", 95),
        }
    return None


def _build_clinical_data_record(
    row: dict[str, Any],
    headers: list[dict[str, Any]],
    table_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Build clinical_data section from a table row.

    Args:
        row: Row data with cells
        headers: Table headers
        table_metadata: Metadata from normalized table

    Returns:
        Clinical data dictionary
    """
    cells = row.get("cells", [])
    header_names = [h.get("name", f"col_{i}") for i, h in enumerate(headers)]

    # Build a mapping of column name to cell
    cell_map = {}
    for cell in cells:
        col_idx = cell.get("column_index", 0)
        col_name = header_names[col_idx] if col_idx < len(header_names) else f"col_{col_idx}"
        cell_map[col_name] = cell

    # Try to identify key clinical fields from first few columns
    first_cell = cells[0] if cells else {}
    second_cell = cells[1] if len(cells) > 1 else {}
    third_cell = cells[2] if len(cells) > 2 else {}

    clinical_data: dict[str, Any] = {
        "endpoint": first_cell.get("value"),
        "metric": None,
        "value": second_cell.get("value"),
        "value_numeric": _parse_numeric_value(second_cell.get("value")),
        "unit": None,
        "comparator": third_cell.get("value") if len(cells) > 2 else None,
    }

    # Extract confidence interval if present
    for cell in cells:
        ci = _extract_confidence_interval(cell)
        if ci:
            clinical_data["confidence_interval"] = ci
            break

    # Extract p-value if present
    for cell in cells:
        value = cell.get("value", "").lower()
        if "p" in value and ("=" in value or "<" in value or ">" in value):
            clinical_data["p_value"] = cell.get("value")
            break

    # Add population from metadata
    clinical_data["population"] = table_metadata.get("population")

    # Add treatment arms
    treatment_arms = table_metadata.get("treatment_arms", [])
    if treatment_arms:
        clinical_data["treatment_arms"] = treatment_arms

    return clinical_data


def _build_attributes(
    row: dict[str, Any],
    headers: list[dict[str, Any]],
    table_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Build dynamic attributes section from row data.

    This is the flexible part of the schema that can accommodate
    any additional columns or metadata without schema changes.

    Args:
        row: Row data with cells
        headers: Table headers
        table_metadata: Metadata from normalized table

    Returns:
        Attributes dictionary (key-value pairs)
    """
    cells = row.get("cells", [])
    header_names = [h.get("name", f"col_{i}") for i, h in enumerate(headers)]

    attributes: dict[str, Any] = {}

    # Add all cell values beyond the first 3 (which are in clinical_data)
    for i, cell in enumerate(cells[3:], start=3):
        col_name = header_names[i] if i < len(header_names) else f"col_{i}"
        value = cell.get("value")
        if value:
            # Normalize column name to snake_case
            key = col_name.lower().replace(" ", "_").replace("-", "_")
            attributes[key] = value

            # Also add normalized value if present
            if "normalized_value" in cell:
                attributes[f"{key}_normalized"] = cell["normalized_value"]

    # Add any metadata fields as attributes
    for key, value in table_metadata.items():
        if key not in ["treatment_arms", "endpoints", "population"] and value:
            attributes[key] = value

    return attributes


def transform_to_adaptive_schema(
    normalized_data: dict[str, Any],
    job_id: str,
    product_name: str,
    table_name: str,
    table_number: int,
    page: int,
    s3_key: str,
    bucket: str,
) -> list[dict[str, Any]]:
    """Transform normalized table data to adaptive JSON schema.

    Each data row becomes a separate JSON record with:
    - Fixed core fields (source, clinical_data)
    - Dynamic attributes section for schema evolution

    Args:
        normalized_data: Normalized data from Claude
        job_id: Job identifier
        product_name: Product name
        table_name: Table title
        table_number: Table number in document
        page: Page number
        s3_key: Source PDF S3 key
        bucket: Source S3 bucket

    Returns:
        List of JSON records with adaptive schema
    """
    records = []
    now = datetime.now(UTC).isoformat()

    # Extract table-level metadata
    table_type = normalized_data.get("table_type", "unknown")
    headers = normalized_data.get("headers", [])
    table_metadata = normalized_data.get("metadata", {})
    footnotes = normalized_data.get("footnotes", [])

    # Process each data row (skip headers/footers)
    rows = normalized_data.get("rows", [])
    for row_idx, row in enumerate(rows):
        row_type = row.get("row_type", "data")

        # Only process data rows
        if row_type not in ["data", "subheader"]:
            continue

        extraction_id = str(uuid.uuid4())

        record = {
            "version": SCHEMA_VERSION,
            "extraction_id": extraction_id,
            "extracted_at": now,
            # Source information (fixed schema)
            "source": {
                "job_id": job_id,
                "product_name": product_name,
                "document_type": "EPAR",
                "table_name": table_name,
                "table_number": table_number,
                "page": page,
                "row_index": row_idx,
                "s3_uri": f"s3://{bucket}/{s3_key}",
            },
            # Clinical data (semi-fixed schema)
            "clinical_data": _build_clinical_data_record(row, headers, table_metadata),
            # Dynamic attributes (fully flexible)
            "attributes": _build_attributes(row, headers, table_metadata),
            # Metadata for debugging/tracing
            "metadata": {
                "table_type": table_type,
                "row_type": row_type,
                "confidence_score": normalized_data.get("confidence"),
                "normalized_by": "claude-3.5-sonnet",
                "footnotes": footnotes,
            },
        }

        records.append(record)

    return records


@tracer.capture_method
def write_jsonl_to_s3(
    normalized_data: dict[str, Any],
    job_id: str,
    product_name: str,
    table_name: str,
    table_number: int,
    page: int,
    s3_key: str,
    bucket: str,
    output_prefix: str = "crf/clinical_tables",
) -> str:
    """Write normalized table data to S3 as JSON Lines.

    Output path structure:
        s3://{bucket}/{output_prefix}/{product_name}/{date}/
            {job_id}_table{table_number}_page{page}.jsonl

    Args:
        normalized_data: Normalized data from Claude
        job_id: Job identifier
        product_name: Product name
        table_name: Table title
        table_number: Table number in document
        page: Page number
        s3_key: Source PDF S3 key
        bucket: Target S3 bucket (business layer)
        output_prefix: S3 prefix for output files

    Returns:
        S3 URI of the written JSONL file
    """
    s3_client = _get_s3_client()

    # Transform to adaptive schema
    records = transform_to_adaptive_schema(
        normalized_data=normalized_data,
        job_id=job_id,
        product_name=product_name,
        table_name=table_name,
        table_number=table_number,
        page=page,
        s3_key=s3_key,
        bucket=bucket,
    )

    # If no data rows, create a single metadata record
    if not records:
        records = [{
            "version": SCHEMA_VERSION,
            "extraction_id": str(uuid.uuid4()),
            "extracted_at": datetime.now(UTC).isoformat(),
            "source": {
                "job_id": job_id,
                "product_name": product_name,
                "document_type": "EPAR",
                "table_name": table_name,
                "table_number": table_number,
                "page": page,
                "row_index": 0,
                "s3_uri": f"s3://{bucket}/{s3_key}",
            },
            "clinical_data": {},
            "attributes": {},
            "metadata": {
                "table_type": normalized_data.get("table_type", "unknown"),
                "row_type": "empty",
                "normalized_by": "claude-3.5-sonnet",
            },
        }]

    # Convert to JSON Lines format
    jsonl_content = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)

    # Build output key
    safe_product = product_name.lower().replace(" ", "_").replace("/", "_")
    partition_date = datetime.now(UTC).strftime("%Y-%m-%d")

    output_key = (
        f"{output_prefix}/"
        f"{safe_product}/"
        f"{partition_date}/"
        f"{job_id[:16]}_table{table_number}_page{page}.jsonl"
    )

    logger.info(
        "Writing JSONL to S3",
        extra={
            "bucket": bucket,
            "key": output_key,
            "records": len(records),
            "table_type": normalized_data.get("table_type", "unknown"),
        },
    )

    s3_client.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=jsonl_content.encode("utf-8"),
        ContentType="application/x-ndjson",
    )

    s3_uri = f"s3://{bucket}/{output_key}"
    logger.info("JSONL file written", extra={"s3_uri": s3_uri})

    return s3_uri
