# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-30

### Added

- **Lambda Function Template** - Production-ready Python 3.12 Lambda with Poetry
- **Docker Container Deployment** - Multi-stage Dockerfile for ECR
- **Terraform Infrastructure** - Lambda, IAM roles, CloudWatch Logs, SSM exports
- **GitHub Actions CI/CD** - OIDC authentication, multi-environment support
- **AWS Lambda Powertools** - Logger, Tracer, structured logging
- **SSM Integration** - Read datalake bucket/KMS ARNs from Parameter Store
- **Unit Tests** - pytest with 80% coverage requirement
- **Code Quality** - ruff linter, mypy type checking
- **Makefile** - Common development commands

### CI/CD Features

- **Manual Trigger** - `workflow_dispatch` for deploy/destroy actions
- **Environment Detection** - Automatic env based on branch (main→prod, release/*→qa, *→dev)
- **ECR Management** - Automatic repository creation via AWS CLI
- **Terraform Destroy** - Manual cleanup action to remove all infrastructure

### Template Mode

- Workflow triggers commented out by default
- Step-by-step setup instructions in README
- Configure GitHub secrets and uncomment triggers to enable

### Infrastructure Created

| Resource | Description |
|----------|-------------|
| Lambda Function | Container-based with X-Ray tracing |
| IAM Role | Execution role with S3, KMS, CloudWatch permissions |
| ECR Repository | Created by CI/CD, lifecycle policy managed by Terraform |
| CloudWatch Logs | Log group with 14-day retention |
| SSM Parameters | Function ARN, name, invoke ARN, role ARN exports |
