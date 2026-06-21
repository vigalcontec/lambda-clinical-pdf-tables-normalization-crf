.PHONY: install test lint format docker-build docker-run docker-push clean help

# Variables
PYTHON_VERSION := 3.12
ENV ?= dev
IMAGE_NAME ?= my-lambda-function
AWS_REGION ?= eu-west-1

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─────────────────────────────────────────────────────────────────────────────
# Development
# ─────────────────────────────────────────────────────────────────────────────

install: ## Install dependencies
	poetry install --with dev

update: ## Update dependencies
	poetry update

# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────

test: ## Run tests
	poetry run pytest

test-verbose: ## Run tests with verbose output
	poetry run pytest -v --tb=long

coverage: ## Run tests with coverage report (80% minimum)
	poetry run pytest --cov=src --cov-report=html --cov-report=term --cov-fail-under=80
	@echo "Coverage report: htmlcov/index.html"

# ─────────────────────────────────────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────────────────────────────────────

lint: ## Run linter
	poetry run ruff check src tests

lint-fix: ## Fix linting issues
	poetry run ruff check --fix src tests

format: ## Format code
	poetry run ruff format src tests

type-check: ## Run type checker
	poetry run mypy src

check: lint type-check test ## Run all checks

# ─────────────────────────────────────────────────────────────────────────────
# Docker
# ─────────────────────────────────────────────────────────────────────────────

docker-build: ## Build Docker image
	docker build -t $(IMAGE_NAME):latest .

docker-run: docker-build ## Run Lambda locally with Docker
	docker run --rm -p 9000:8080 \
		-e ENVIRONMENT=$(ENV) \
		-e AWS_REGION=$(AWS_REGION) \
		$(IMAGE_NAME):latest

docker-test: ## Test Lambda locally (requires docker-run in another terminal)
	curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
		-d '{"key1": "value1", "key2": "value2"}'

docker-push: ## Build and push to ECR
	@echo "Getting AWS account ID..."
	$(eval AWS_ACCOUNT := $(shell aws sts get-caller-identity --query Account --output text))
	$(eval ECR_REPO := $(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com/$(IMAGE_NAME)-$(ENV))
	
	@echo "Logging in to ECR..."
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com
	
	@echo "Building image..."
	docker build -t $(ECR_REPO):latest .
	
	@echo "Pushing to ECR..."
	docker push $(ECR_REPO):latest

# ─────────────────────────────────────────────────────────────────────────────
# Local Development
# ─────────────────────────────────────────────────────────────────────────────

run-local: ## Run handler locally with a single test event
	poetry run python scripts/test_single_event.py

local-test: ## Run local test with Textract output file
	poetry run python scripts/local_test.py --textract-output $(TEXTRACT_OUTPUT)

local-test-dry: ## Run local test without S3/DynamoDB writes
	poetry run python scripts/local_test.py --dry-run

local-test-help: ## Show local test script help
	poetry run python scripts/local_test.py --help

# ─────────────────────────────────────────────────────────────────────────────
# Terraform
# ─────────────────────────────────────────────────────────────────────────────

tf-init: ## Initialize Terraform
	cd terraform && terraform init

tf-plan: ## Plan Terraform changes
	cd terraform && terraform plan -var="environment=$(ENV)"

tf-apply: ## Apply Terraform changes
	cd terraform && terraform apply -var="environment=$(ENV)"

tf-destroy: ## Destroy Terraform resources
	cd terraform && terraform destroy -var="environment=$(ENV)"

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

clean: ## Clean build artifacts
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
