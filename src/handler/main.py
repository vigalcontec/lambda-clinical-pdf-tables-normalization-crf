"""AWS Lambda Handler - Main Entry Point."""

from typing import Any

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from handler.config import get_settings

logger = Logger()
tracer = Tracer()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: dict[str, Any], _context: LambdaContext) -> dict[str, Any]:
    """Lambda handler function."""
    settings = get_settings()

    try:
        logger.info("Processing event", extra={"environment": settings.environment})

        # TODO: Implement your business logic here
        return {
            "statusCode": 200,
            "body": {
                "message": "Success",
                "event": event,
            },
        }

    except Exception as e:
        logger.exception("Error processing event")
        return {
            "statusCode": 500,
            "body": {"error": str(e)},
        }
