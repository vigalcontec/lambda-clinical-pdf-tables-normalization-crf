"""SSM Parameter Store utilities (example for reading parameters at runtime)."""

from functools import lru_cache

import boto3
from aws_lambda_powertools import Logger

logger = Logger()


@lru_cache(maxsize=32)
def get_parameter(name: str, decrypt: bool = True) -> str:
    """
    Get a parameter from SSM Parameter Store.

    Args:
        name: Parameter name (e.g., "/dev/my-app/database-url")
        decrypt: Whether to decrypt SecureString parameters

    Returns:
        Parameter value
    """
    ssm = boto3.client("ssm")
    response = ssm.get_parameter(Name=name, WithDecryption=decrypt)
    return str(response["Parameter"]["Value"])


def get_parameters_by_path(path: str, decrypt: bool = True) -> dict[str, str]:
    """
    Get all parameters under a path from SSM Parameter Store.

    Args:
        path: Parameter path prefix (e.g., "/dev/my-app/")
        decrypt: Whether to decrypt SecureString parameters

    Returns:
        Dictionary of parameter names to values
    """
    ssm = boto3.client("ssm")
    paginator = ssm.get_paginator("get_parameters_by_path")

    params: dict[str, str] = {}
    for page in paginator.paginate(Path=path, WithDecryption=decrypt, Recursive=True):
        for param in page["Parameters"]:
            # Extract just the parameter name (last part of path)
            name = param["Name"].split("/")[-1]
            params[name] = param["Value"]

    logger.info(f"Loaded {len(params)} parameters from {path}")
    return params
