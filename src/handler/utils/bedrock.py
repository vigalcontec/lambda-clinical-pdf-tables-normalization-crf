"""AWS Bedrock utility functions for foundation model integration."""

import json
from functools import lru_cache
from typing import Any

import boto3
from aws_lambda_powertools import Logger, Tracer

from handler.config import get_settings

logger = Logger()
tracer = Tracer()


@lru_cache
def _get_bedrock_client() -> Any:
    """Get cached Bedrock runtime client."""
    settings = get_settings()
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def _build_claude_request(
    prompt: str,
    system_prompt: str | None,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    """Build request body for Claude models."""
    messages = [{"role": "user", "content": prompt}]
    request_body: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system_prompt:
        request_body["system"] = system_prompt
    return request_body


def _build_nova_request(
    prompt: str,
    system_prompt: str | None,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    """Build request body for Amazon Nova models.

    Reference: https://docs.aws.amazon.com/nova/latest/userguide/using-invoke-api.html
    """
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    request_body: dict[str, Any] = {
        "schemaVersion": "messages-v1",
        "messages": messages,
        "inferenceConfig": {
            "maxTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system_prompt:
        request_body["system"] = [{"text": system_prompt}]
    return request_body


def _parse_claude_response(response_body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Parse response from Claude models."""
    output_text = response_body["content"][0]["text"]
    usage = {
        "input_tokens": response_body.get("usage", {}).get("input_tokens"),
        "output_tokens": response_body.get("usage", {}).get("output_tokens"),
    }
    return output_text, usage


def _parse_nova_response(response_body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Parse response from Amazon Nova models."""
    output_text = response_body["output"]["message"]["content"][0]["text"]
    usage = {
        "input_tokens": response_body.get("usage", {}).get("inputTokens"),
        "output_tokens": response_body.get("usage", {}).get("outputTokens"),
    }
    return output_text, usage


@tracer.capture_method
def invoke_model(
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> str:
    """Invoke foundation model via AWS Bedrock.

    Supports both Claude and Amazon Nova models with automatic format detection.

    Args:
        prompt: The user prompt to send to the model
        system_prompt: Optional system prompt for context
        max_tokens: Maximum tokens in response (default 4096)
        temperature: Temperature for response randomness (default 0.0 for deterministic)

    Returns:
        The text response from the model
    """
    settings = get_settings()
    client = _get_bedrock_client()
    model_id = settings.bedrock_model_id

    # Determine model type and build appropriate request
    # Handle both direct (amazon.nova-*) and cross-region (eu.amazon.nova-*) model IDs
    is_nova = "amazon.nova" in model_id

    if is_nova:
        request_body = _build_nova_request(prompt, system_prompt, max_tokens, temperature)
    else:
        request_body = _build_claude_request(prompt, system_prompt, max_tokens, temperature)

    logger.info(
        "Invoking Bedrock model",
        extra={
            "model_id": model_id,
            "model_type": "nova" if is_nova else "claude",
            "prompt_length": len(prompt),
            "max_tokens": max_tokens,
        },
    )

    response = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body),
    )

    response_body = json.loads(response["body"].read())

    # Parse response based on model type
    if is_nova:
        output_text, usage = _parse_nova_response(response_body)
    else:
        output_text, usage = _parse_claude_response(response_body)

    logger.info(
        "Model response received",
        extra={
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "response_length": len(output_text),
        },
    )

    return str(output_text)


# Alias for backward compatibility
invoke_claude = invoke_model


@tracer.capture_method
def normalize_table_with_claude(
    table_data: dict[str, Any],
    table_name: str,
    product_name: str,
    system_prompt: str,
) -> dict[str, Any]:
    """Normalize table data using Claude AI.

    Args:
        table_data: Raw table data from Textract (rows, row_count, column_count, confidence)
        table_name: Name/title of the table
        product_name: Product name for context
        system_prompt: System prompt with normalization instructions

    Returns:
        Normalized table data as a structured dictionary
    """
    # Build the user prompt with table context
    user_prompt = f"""## Table Information
- **Product**: {product_name}
- **Table Title**: {table_name}
- **Rows**: {table_data.get('row_count', 0)}
- **Columns**: {table_data.get('column_count', 0)}

## Raw Table Data (from Textract OCR)
```json
{json.dumps(table_data.get('rows', []), indent=2, ensure_ascii=False)}
```

Please normalize this clinical table data according to the instructions provided."""

    response_text = invoke_claude(
        prompt=user_prompt,
        system_prompt=system_prompt,
        max_tokens=8192,
        temperature=0.0,
    )

    # Parse the JSON response from Claude
    try:
        # Try to extract JSON from the response
        # Claude may wrap it in markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        else:
            json_str = response_text.strip()

        normalized_data: dict[str, Any] = json.loads(json_str)
        logger.info("Successfully parsed normalized table data")
        return normalized_data

    except json.JSONDecodeError as e:
        logger.warning(
            "Failed to parse Claude response as JSON",
            extra={"error": str(e), "response_preview": response_text[:500]},
        )
        # Return the raw response wrapped in a structure
        return {
            "raw_response": response_text,
            "parse_error": str(e),
            "normalized": False,
        }
