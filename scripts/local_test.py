#!/usr/bin/env python
"""Local test script for the Normalization Lambda handler.

This script allows testing the Lambda function locally with a single event.
It can load events from a JSON file (Textract output) or use inline JSON.

Usage:
    # Test with default event
    poetry run python scripts/local_test.py

    # Test with Textract output file
    poetry run python scripts/local_test.py --textract-output path/to/textract_result.json

    # Test with inline event
    poetry run python scripts/local_test.py --inline '{...}'

    # Skip DynamoDB and S3 writes (dry run)
    poetry run python scripts/local_test.py --dry-run
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Set AWS region BEFORE any boto3 imports happen
os.environ.setdefault("AWS_REGION", "eu-west-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-1")

# Add src to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def load_textract_output(file_path: str) -> dict[str, Any]:
    """Load Textract output from a JSON file.

    Args:
        file_path: Path to the Textract output JSON file

    Returns:
        Event dictionary formatted for normalization lambda
    """
    with open(file_path) as f:
        data = json.load(f)

    # If it's a list, take the first item
    if isinstance(data, list):
        data = data[0]

    return data


def create_mock_context() -> Any:
    """Create a mock Lambda context for local testing."""

    class MockContext:
        function_name = "clinical-pdf-normalization-local"
        memory_limit_in_mb = 512
        invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789:function:local-test"
        aws_request_id = "local-test-request-id"

        def get_remaining_time_in_millis(self) -> int:
            return 300000  # 5 minutes

    return MockContext()


def setup_environment(dry_run: bool = False) -> None:
    """Set up environment variables for local testing."""
    # Load from .env file if it exists
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

    # Set defaults for local testing
    os.environ.setdefault("ENVIRONMENT", "dev")
    os.environ.setdefault("AWS_REGION", "eu-west-1")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")
    os.environ.setdefault("POWERTOOLS_SERVICE_NAME", "clinical-pdf-normalization-local")
    os.environ.setdefault("POWERTOOLS_TRACE_DISABLED", "true")
    os.environ.setdefault("DYNAMODB_TABLE_NAME", "clinical-pdf-jobs-crf-dev")
    os.environ.setdefault("BEDROCK_MODEL_ID", "eu.amazon.nova-pro-v1:0")
    os.environ.setdefault("BUSINESS_BUCKET_NAME", "datalake-business-vigalcontec-dev-002332700133")
    os.environ.setdefault("OUTPUT_PREFIX", "crf/clinical_tables")

    if dry_run:
        # Disable S3 and DynamoDB writes
        os.environ["BUSINESS_BUCKET_NAME"] = ""
        os.environ["DYNAMODB_TABLE_NAME"] = ""


def get_default_event() -> dict[str, Any]:
    """Return a default test event."""
    return {
        "status": "SUCCESS",
        "job_id": "local-test-job",
        "s3_bucket": "datalake-raw-vigalcontec-dev-002332700133",
        "s3_key": "crf/clinical_pdfs/ibrance/20260603164300/ibrance-epar-product-information_en.pdf",
        "product_name": "ibrance",
        "table_name": "Table 5: Laboratory abnormalities observed in pooled dataset from 3 randomised studies",
        "table_number": 5,
        "pages_processed": [11],
        "table_index_on_page": 1,
        "tables_found_on_page": 2,
        "table": {
            "title": "Table 5: Laboratory abnormalities",
            "rows": [
                ["Laboratory abnormality", "IBRANCE + letrozole", "", "Placebo + letrozole", ""],
                ["", "All grades %", "Grade 3 %", "All grades %", "Grade 3 %"],
                ["WBC decreased", "97.4", "41.8", "26.2", "0.2"],
                ["Neutrophils decreased", "95.2", "56.8", "17.1", "0.6"],
                ["Anaemia", "78.2", "5.4", "42.2", "1.4"],
            ],
            "row_count": 5,
            "column_count": 5,
            "confidence": 99.5
        }
    }


def main() -> None:
    """Run the local test."""
    parser = argparse.ArgumentParser(description="Local test for Normalization Lambda")
    parser.add_argument(
        "--textract-output",
        type=str,
        help="Path to Textract output JSON file",
    )
    parser.add_argument(
        "--inline",
        type=str,
        help="Inline JSON event (overrides --textract-output)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip DynamoDB and S3 writes",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (default: output_example/local_test_result.json)",
    )

    args = parser.parse_args()

    # Set up environment
    setup_environment(dry_run=args.dry_run)

    # Load event
    if args.inline:
        event = json.loads(args.inline)
        print("Using inline event")
    elif args.textract_output:
        event = load_textract_output(args.textract_output)
        print(f"Loaded Textract output from {args.textract_output}")
    else:
        # Use default event
        event = get_default_event()
        print("Using default test event")

    # Print event info
    print("\n" + "=" * 60)
    print("EVENT DETAILS:")
    print("=" * 60)
    print(f"  Status: {event.get('status')}")
    print(f"  Product: {event.get('product_name')}")
    print(f"  Table: {event.get('table_name')}")
    print(f"  Table Number: {event.get('table_number')}")
    pages = event.get('pages_processed', [event.get('page')])
    print(f"  Page: {pages[0] if pages else 'N/A'}")
    table = event.get('table', {})
    if table:
        print(f"  Rows: {table.get('row_count')}")
        print(f"  Columns: {table.get('column_count')}")
        print(f"  Confidence: {table.get('confidence')}")
    if args.dry_run:
        print("\n  ** DRY RUN MODE - No S3/DynamoDB writes **")
    print("=" * 60 + "\n")

    # Import handler after environment setup
    from handler.main import handler

    # Create mock context
    context = create_mock_context()

    # Run handler
    print("Running handler (calling Claude AI)...")
    print("-" * 60)

    try:
        result = handler(event, context)

        print("-" * 60)
        print("\nRESULT:")
        print("=" * 60)
        print(f"  Status: {result.get('status')}")
        print(f"  Normalization Status: {result.get('normalization_status', 'N/A')}")
        print(f"  Table Type Detected: {result.get('table_type_detected', 'N/A')}")
        print(f"  Output URI: {result.get('output_uri', 'N/A')}")

        if result.get("status") == "SUCCESS":
            normalized = result.get("normalized_data", {})
            if normalized and normalized.get("normalized") is not False:
                print(f"\n  Normalized Table Type: {normalized.get('table_type', 'N/A')}")
                print(f"  Headers: {len(normalized.get('headers', []))}")
                print(f"  Rows: {len(normalized.get('rows', []))}")

                # Show metadata
                metadata = normalized.get("metadata", {})
                if metadata:
                    print(f"\n  Metadata:")
                    for key, value in list(metadata.items())[:5]:
                        print(f"    {key}: {value}")

                # Show first few rows
                rows = normalized.get("rows", [])
                if rows:
                    print("\n  First 3 normalized rows:")
                    for i, row in enumerate(rows[:3]):
                        row_type = row.get("row_type", "unknown")
                        cells = row.get("cells", [])
                        cell_values = [str(c.get("value", ""))[:25] for c in cells[:3]]
                        print(f"    [{row_type}]: {cell_values}")
                    if len(rows) > 3:
                        print(f"    ... ({len(rows) - 3} more rows)")
            else:
                print(f"\n  Parse Error: {normalized.get('parse_error', 'Unknown')}")
        else:
            print(f"  Error: {result.get('error', result.get('reason', 'Unknown'))}")

        print("=" * 60)

        # Save to file
        output_dir = Path(__file__).parent.parent / "output_example"
        output_dir.mkdir(exist_ok=True)
        output_file = Path(args.output) if args.output else output_dir / "local_test_result.json"

        with open(output_file, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nFull result saved to: {output_file}")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
