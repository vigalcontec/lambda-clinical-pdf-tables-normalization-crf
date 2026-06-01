# Clinical PDF Tables Normalization Lambda

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://www.python.org/)
[![Poetry](https://img.shields.io/badge/Poetry-1.8%2B-60A5FA?logo=poetry)](https://python-poetry.org/)
[![Docker](https://img.shields.io/badge/Docker-ECR-2496ED?logo=docker)](https://aws.amazon.com/ecr/)
[![Terraform](https://img.shields.io/badge/Terraform-1.10%2B-7B42BC?logo=terraform)](https://www.terraform.io/)

AWS Lambda function that normalizes clinical PDF table data using Claude AI (via AWS Bedrock). This Lambda is part of the Clinical RAG Foundry pipeline and runs after the Textract extraction step.

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Event Flow](#event-flow)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Testing](#testing)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Step Functions Distributed Map                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────────┐     ┌────────────────────┐  │
│  │   Textract   │────▶│  Normalization   │────▶│     DynamoDB       │  │
│  │    Lambda    │     │     Lambda       │     │   (Job Tracking)   │  │
│  └──────────────┘     └──────────────────┘     └────────────────────┘  │
│         │                      │                                        │
│         │                      │                                        │
│         ▼                      ▼                                        │
│   Raw Table Data         Claude AI (Bedrock)                           │
│   (rows, columns)        Normalizes & Structures                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Features

- ✅ **Claude AI Integration** - Uses AWS Bedrock to normalize table data
- ✅ **Smart Table Type Detection** - Detects efficacy, adverse events, dosing tables
- ✅ **Professional Prompts** - Clinical data specialist prompts for accurate normalization
- ✅ **DynamoDB Tracking** - Updates job status and stores normalized data
- ✅ **Error Handling** - Graceful handling of Textract failures and Claude errors
- ✅ **Structured Logging** - AWS Lambda Powertools for observability
- ✅ **Multi-environment** - dev, qa, prod support

---

## Repository Structure

```
aws-lambda-python-template/
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD pipeline
├── src/
│   └── handler/
│       ├── __init__.py
│       ├── main.py                 # Lambda entry point
│       ├── config.py               # Configuration management
│       └── utils/
│           ├── __init__.py
│           └── ssm.py              # SSM parameter utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   └── test_handler.py             # Unit tests
├── terraform/
│   ├── config.tf                   # ⭐ PROJECT CONFIG (edit this!)
│   ├── main.tf                     # Lambda + ECR resources
│   ├── variables.tf                # Runtime variables (env, image_tag)
│   ├── outputs.tf                  # Output values
│   ├── iam.tf                      # IAM role and policies
│   ├── backend.tf                  # S3 backend (uses -backend-config)
│   ├── ssm_imports.tf              # Datalake SSM parameters
│   └── ssm_exports.tf              # Lambda SSM exports
├── Dockerfile                      # Lambda container image
├── pyproject.toml                  # Poetry configuration
├── poetry.lock                     # Locked dependencies
├── docker-compose.yml              # Local development
├── Makefile                        # Development commands
├── CHANGELOG.md
└── README.md
```

---

## Prerequisites

- **Python 3.12+**
- **Poetry 1.8+**
- **Docker**
- **AWS CLI v2**
- **Terraform 1.10+**

### Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

---

## Quick Start

### 1. Create New Repository from Template

```bash
# Clone template
git clone https://github.com/vigalcontec/aws-lambda-python-template.git my-lambda-function
cd my-lambda-function

# Remove template git history
rm -rf .git
git init
```

### 2. Configure Your Project

Edit `terraform/config.tf`:

```hcl
locals {
  function_name = "my-data-processor"   # Your function name
  project_name  = "my-project"          # Your project name
  company_name  = "vigalcontec"         # Your company name
  
  # Lambda settings
  timeout     = 30
  memory_size = 256
}
```

Update `pyproject.toml`:

```toml
[tool.poetry]
name = "my-data-processor"
```

### 3. Install Dependencies

```bash
poetry install
```

### 4. Generate Lock File (Required for Docker)

The `poetry.lock` file must exist before building the Docker image:

```bash
poetry lock
```

> **Important:** Commit `poetry.lock` to your repository. The Docker build will fail without it.

### 5. Configure GitHub Secrets

Add the following secrets to your GitHub repository (`Settings > Secrets and variables > Actions`):

| Secret | Description |
|--------|-------------|
| `AWS_ROLE_ARN_DEV` | ARN of the GitHub Actions IAM role for dev |
| `AWS_ROLE_ARN_QA` | ARN of the GitHub Actions IAM role for qa |
| `AWS_ROLE_ARN_PROD` | ARN of the GitHub Actions IAM role for prod |

> **Note:** These roles are created by the `aws-bootstrap-tfstate-oidc` repository.

### 6. Enable CI/CD Workflows

The workflow triggers are **commented out by default** to prevent automatic runs during setup.

Edit `.github/workflows/deploy.yml` and uncomment the triggers:

```yaml
on:
  workflow_dispatch:
    # ... (keep this for manual runs)
  
  # UNCOMMENT THESE LINES:
  push:
    branches: [main, develop, "feature/*", "release/*"]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'Dockerfile'
      - 'pyproject.toml'
      - 'poetry.lock'
      - 'terraform/**'
      - '.github/workflows/deploy.yml'
  pull_request:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'Dockerfile'
      - 'pyproject.toml'
      - 'terraform/**'
```

### 7. Run Locally

```bash
# Using Docker
make docker-run

# Or using Poetry
make run-local
```

---

## Local Development

### Install Dependencies

```bash
poetry install --with dev
```

### Run Tests

```bash
make test
```

### Format Code

```bash
make format
```

### Lint Code

```bash
make lint
```

### Build Docker Image

```bash
make docker-build
```

---

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ENVIRONMENT` | Environment name (dev/qa/prod) | Yes |
| `AWS_REGION` | AWS region | Yes |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | No |

### Datalake Configuration (Auto-injected)

Terraform reads SSM parameters at deploy time and injects them as Lambda environment variables:

| Environment Variable | Source SSM Parameter |
|---------------------|----------------------|
| `RAW_BUCKET_NAME` | `/{env}/datalake/raw/bucket_name` |
| `RAW_BUCKET_ARN` | `/{env}/datalake/raw/bucket_arn` |
| `RAW_KMS_KEY_ARN` | `/{env}/datalake/raw/kms_key_arn` |
| `STAGING_BUCKET_NAME` | `/{env}/datalake/staging/bucket_name` |
| `STAGING_BUCKET_ARN` | `/{env}/datalake/staging/bucket_arn` |
| `STAGING_KMS_KEY_ARN` | `/{env}/datalake/staging/kms_key_arn` |
| `BUSINESS_BUCKET_NAME` | `/{env}/datalake/business/bucket_name` |
| `BUSINESS_BUCKET_ARN` | `/{env}/datalake/business/bucket_arn` |
| `BUSINESS_KMS_KEY_ARN` | `/{env}/datalake/business/kms_key_arn` |

> **Note:** Lambda does NOT call SSM at runtime. Terraform reads SSM during deployment and passes values as environment variables for better cold start performance.

---

## Deployment

### GitHub Actions (Recommended)

After enabling CI/CD triggers (Step 6), push to branch triggers automatic deployment:

| Branch | Environment |
|--------|-------------|
| `main` | prod |
| `release/*` | qa |
| `develop`, `feature/*` | dev |

**No GitHub Variables needed!** Configuration is read from `terraform/config.tf`.

### Manual Deploy/Destroy

Use `workflow_dispatch` to manually trigger actions:

1. Go to **Actions** → **Build & Deploy Lambda**
2. Click **Run workflow**
3. Select:
   - **Environment:** dev, qa, or prod
   - **Action:** `deploy` or `destroy`
   - **Skip tests:** optionally skip test step

| Action | Description |
|--------|-------------|
| `deploy` | Build image, push to ECR, deploy Lambda |
| `destroy` | Terraform destroy + delete ECR repository |

### Manual Deployment

```bash
# Build and push Docker image
make docker-push ENV=dev

# Deploy infrastructure
cd terraform
terraform init \
  -backend-config="bucket=tfstate-vigalcontec-dev-123456789012" \
  -backend-config="key=lambda/my-lambda-function/terraform.tfstate" \
  -backend-config="region=eu-west-1" \
  -backend-config="encrypt=true"

terraform apply -var="environment=dev"
```

---

## Testing

### Unit Tests

```bash
make test
```

### Coverage Report

```bash
make coverage
```

### Integration Tests (requires AWS credentials)

```bash
make test-integration
```

---

## Datalake Integration

This template is designed to work with the `aws-datalake-layers` infrastructure. Terraform reads bucket names and KMS keys from SSM Parameter Store at deploy time and injects them as environment variables.

### Using Datalake Config in Code

```python
from handler.utils.ssm import get_datalake_config

# Reads from environment variables (no SSM call at runtime)
config = get_datalake_config()
print(config.raw_bucket_name)
print(config.raw_kms_key_arn)
```

### Benefits

- **Faster cold starts** - No SSM API calls during Lambda initialization
- **Simpler IAM** - Lambda doesn't need SSM read permissions at runtime
- **Easier testing** - Just set environment variables in tests

---

## License

MIT
