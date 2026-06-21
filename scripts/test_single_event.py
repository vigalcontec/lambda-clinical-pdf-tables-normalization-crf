#!/usr/bin/env python
"""Quick test script for a single normalization event.

This is a simplified script for rapid testing. Edit the EVENT dict below
to test different tables. The event should match the output from the Textract lambda.

Usage:
    poetry run python scripts/test_single_event.py
"""

import json
import os
import sys
from pathlib import Path

# Set environment BEFORE any imports that use boto3
os.environ.setdefault("AWS_REGION", "eu-west-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-1")
os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("POWERTOOLS_SERVICE_NAME", "clinical-pdf-normalization-local")
os.environ.setdefault("POWERTOOLS_TRACE_DISABLED", "true")
os.environ.setdefault("DYNAMODB_TABLE_NAME", "clinical-pdf-jobs-crf-dev")
os.environ.setdefault("BEDROCK_MODEL_ID", "eu.amazon.nova-pro-v1:0")
os.environ.setdefault("BUSINESS_BUCKET_NAME", "datalake-business-vigalcontec-dev-002332700133")
os.environ.setdefault("OUTPUT_PREFIX", "crf/clinical_tables")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ============================================================================
# CONFIGURE YOUR TEST EVENT HERE
# This should match the output from the Textract lambda
# ============================================================================
EVENT = {
    "status": "SUCCESS",
    "job_id": "73a98bcaed2e5b347266ff9f037099270b545348fdf729a2479eedc3e06fd319",
    "s3_bucket": "datalake-raw-vigalcontec-dev-002332700133",
    "s3_key": "crf/clinical_pdfs/ibrance/20260603164300/ibrance-epar-product-information_en.pdf",
    "product_name": "ibrance",
    "table_name": "Table 5: Laboratory abnormalities observed in pooled dataset from 3 randomised studies",
    "table_number": 5,
    "pages_processed": [11],
    "table_index_on_page": 1,
    "tables_found_on_page": 2,
    "table": {
        "title": "Table 5: Laboratory abnormalities observed in pooled dataset from 3 randomised studies",
        "rows": [
            ["Laboratory abnormality", "IBRANCE plus letrozole (N=444)", "", "Placebo plus letrozole (N=222)", ""],
            ["", "All grades %", "Grade 3 %", "All grades %", "Grade 3 %"],
            ["WBC decreased", "97.4", "41.8", "26.2", "0.2"],
            ["Neutrophils decreased", "95.2", "56.8", "17.1", "0.6"],
            ["Anaemia", "78.2", "5.4", "42.2", "1.4"],
            ["Platelets decreased", "62.8", "1.6", "10.0", "0.5"]
        ],
        "row_count": 6,
        "column_count": 5,
        "confidence": 99.5
    },
    "formulation_key": "28e423a2c598",
    "formulations": [
        "IBRANCE 75 mg hard capsules",
        "IBRANCE 100 mg hard capsules",
        "IBRANCE 125 mg hard capsules"
    ]
}
# ============================================================================


class MockContext:
    """Mock Lambda context."""
    function_name = "normalization-local-test"
    memory_limit_in_mb = 512
    invoked_function_arn = "arn:aws:lambda:eu-west-1:123456789:function:local"
    aws_request_id = "local-request"

    def get_remaining_time_in_millis(self) -> int:
        return 300000


def main() -> None:
    """Run the test."""
    print("=" * 70)
    print("NORMALIZATION LAMBDA LOCAL TEST")
    print("=" * 70)
    print(f"Product:     {EVENT['product_name']}")
    print(f"Table:       {EVENT['table_name']}")
    print(f"Table #:     {EVENT['table_number']}")
    print(f"Page:        {EVENT.get('pages_processed', [EVENT.get('page')])[0]}")
    print(f"Input Status: {EVENT['status']}")
    if EVENT.get("table"):
        print(f"Rows:        {EVENT['table'].get('row_count')}")
        print(f"Columns:     {EVENT['table'].get('column_count')}")
    print("=" * 70)

    from handler.main import handler

    print("\nCalling handler (this will invoke Claude AI)...\n")

    result = handler(EVENT, MockContext())

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    print(f"Status: {result['status']}")
    print(f"Normalization Status: {result.get('normalization_status', 'N/A')}")
    print(f"Table Type Detected: {result.get('table_type_detected', 'N/A')}")
    print(f"Output URI: {result.get('output_uri', 'N/A')}")

    if result["status"] == "SUCCESS":
        normalized = result.get("normalized_data", {})
        if normalized:
            print(f"\nNormalized Table Type: {normalized.get('table_type', 'N/A')}")
            print(f"Headers: {len(normalized.get('headers', []))}")
            print(f"Rows: {len(normalized.get('rows', []))}")
            print(f"Footnotes: {len(normalized.get('footnotes', []))}")

            # Show metadata
            metadata = normalized.get("metadata", {})
            if metadata:
                print(f"\nMetadata:")
                for key, value in metadata.items():
                    print(f"  {key}: {value}")

            # Show first few rows
            rows = normalized.get("rows", [])
            if rows:
                print("\nFirst 3 normalized rows:")
                for i, row in enumerate(rows[:3]):
                    row_type = row.get("row_type", "unknown")
                    cells = row.get("cells", [])
                    cell_values = [c.get("value", "")[:30] for c in cells[:3]]
                    print(f"  [{row_type}]: {cell_values}")
                if len(rows) > 3:
                    print(f"  ... ({len(rows) - 3} more rows)")
    else:
        print(f"Error: {result.get('error', result.get('reason', 'Unknown'))}")

    print("=" * 70)

    # Save full result
    output_dir = Path(__file__).parent.parent / "output_example"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "local_test_result.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nFull result saved to: {output_file}")


if __name__ == "__main__":
    main()
