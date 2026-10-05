"""HTTP middleware for request logging and timing."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger("app.access")

_SKIP_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        extra = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            extra["event"] = "authenticated_request"

        if response.status_code >= 500:
            logger.error(
                "%s %s -> %s (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra=extra,
            )
        elif response.status_code >= 400:
            logger.warning(
                "%s %s -> %s (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra=extra,
            )
        else:
            logger.info(
                "%s %s -> %s (%.1fms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra=extra,
            )
        return response
