# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-28

### Added

- **Table Normalization with Claude AI** - Uses AWS Bedrock to normalize Textract output
- **Smart Table Type Detection** - Automatically detects efficacy, adverse events, dosing tables
- **Professional Clinical Prompts** - Expert prompts for accurate medical data normalization
- **JSONL Output with Adaptive Schema** - Writes normalized data to S3 as JSON Lines with versioned, evolvable schema
- **DynamoDB Integration** - Updates job tracking with normalized data
- **Error Handling** - Graceful handling of Textract failures and Claude errors

### Features

- **Bedrock Integration** (`src/handler/utils/bedrock.py`)
  - `invoke_claude()` - Direct Claude model invocation
  - `normalize_table_with_claude()` - Table-specific normalization

- **DynamoDB Tracking** (`src/handler/utils/dynamodb.py`)
  - `update_table_with_normalized_data()` - Store normalized data
  - `increment_tables_normalized()` - Track progress
  - `increment_normalization_failed()` - Track failures
  - `update_job_status_if_complete()` - Mark job complete when all tables processed

- **Clinical Prompts** (`src/handler/prompts.py`)
  - System prompt for clinical data specialist
  - Specialized prompts for efficacy, adverse events, dosing tables
  - JSON output format specification

### Infrastructure

| Resource | Description |
|----------|-------------|
| Lambda Function | 120s timeout, 512MB memory for Claude API calls |
| IAM Role | Bedrock InvokeModel, DynamoDB UpdateItem/GetItem/PutItem |
| Environment Variables | DYNAMODB_TABLE_NAME, BEDROCK_MODEL_ID |

### SSM Dependencies

| Parameter | Source |
|-----------|--------|
| DynamoDB Table Name | `/{env}/clinical-rag-foundry/dynamodb/clinical-pdf-jobs-crf/table_name` |
| DynamoDB Table ARN | `/{env}/clinical-rag-foundry/dynamodb/clinical-pdf-jobs-crf/table_arn` |

### Event Format

**Input (from Textract Lambda):**
```json
{
  "status": "SUCCESS",
  "s3_bucket": "bucket-name",
  "s3_key": "path/to/document.pdf",
  "product_name": "keytruda",
  "table_name": "Table 6: Efficacy results...",
  "table_number": 6,
  "pages_processed": [32],
  "table": {
    "rows": [["Header1", "Header2"], ["Value1", "Value2"]],
    "row_count": 2,
    "column_count": 2,
    "confidence": 98.5
  },
  "events_s3_key": "path/to/events.json"
}
```

**Output:**
```json
{
  "status": "SUCCESS",
  "product_name": "keytruda",
  "table_name": "Table 6: Efficacy results...",
  "table_number": 6,
  "page": 32,
  "table_type_detected": "efficacy",
  "normalized_data": {...},
  "normalization_status": "NORMALIZED"
}
```
