# =============================================================================
# AWS Lambda Python Container Image
# =============================================================================
# Multi-stage build for optimized image size

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies with Poetry
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install Poetry
ENV POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install production dependencies only
RUN poetry install --only main --no-root

# Copy source code
COPY src/ ./src/

# Install the package
RUN poetry install --only main

# -----------------------------------------------------------------------------
# Stage 2: Runtime - AWS Lambda base image
# -----------------------------------------------------------------------------
FROM public.ecr.aws/lambda/python:3.12

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages ${LAMBDA_TASK_ROOT}

# Copy application code
COPY --from=builder /app/src/handler ${LAMBDA_TASK_ROOT}/handler

# Set the handler
CMD ["handler.main.handler"]
