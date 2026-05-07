"""Exception handlers for the sentiment analysis API."""

import logging

from fastapi import Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class HealthCheckError(Exception):
    def __init__(self, reason: str):
        self.reason = reason


async def health_check_error_handler(_: Request, exc: HealthCheckError):
    return JSONResponse(
        {"status": "unhealthy", "detail": exc.reason},
        status_code=503,
    )


async def log_http_exception(request: Request, exc: StarletteHTTPException):
    logger.warning("%s %s → %d", request.method, request.url.path, exc.status_code)
    return await http_exception_handler(request, exc)


async def log_validation_error(request: Request, exc: RequestValidationError):
    logger.warning("%s %s validation failed: %s", request.method, request.url.path, exc.errors())
    return await request_validation_exception_handler(request, exc)


async def handle_exception(request: Request, exc: Exception):
    logger.exception("%s %s failed: %s", request.method, request.url.path, str(exc))
    return JSONResponse({"detail": "Internal server error"}, status_code=500)
