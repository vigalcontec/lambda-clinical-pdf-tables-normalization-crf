"""AWS Bedrock utility functions for Claude AI integration."""

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


@tracer.capture_method
def invoke_claude(
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> str:
    """Invoke Claude model via AWS Bedrock.

    Args:
        prompt: The user prompt to send to Claude
        system_prompt: Optional system prompt for context
        max_tokens: Maximum tokens in response (default 4096)
        temperature: Temperature for response randomness (default 0.0 for deterministic)

    Returns:
        The text response from Claude
    """
    settings = get_settings()
    client = _get_bedrock_client()

    messages = [{"role": "user", "content": prompt}]

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }

    if system_prompt:
        request_body["system"] = system_prompt

    logger.info(
        "Invoking Claude model",
        extra={
            "model_id": settings.bedrock_model_id,
            "prompt_length": len(prompt),
            "max_tokens": max_tokens,
        },
    )

    response = client.invoke_model(
        modelId=settings.bedrock_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body),
    )

    response_body = json.loads(response["body"].read())
    output_text = response_body["content"][0]["text"]

    logger.info(
        "Claude response received",
        extra={
            "input_tokens": response_body.get("usage", {}).get("input_tokens"),
            "output_tokens": response_body.get("usage", {}).get("output_tokens"),
            "response_length": len(output_text),
        },
    )

    return str(output_text)


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
