"""Request / response logging middleware.

Attaches a unique ``request_id`` to every incoming request, logs the
method, path, response status code, and duration in milliseconds, and
returns the ``X-Request-ID`` header so that callers can correlate
client-side traces with server logs.
"""

import time
import uuid

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every HTTP request with a unique request ID.

    Features:
        * Generates a UUID-4 ``request_id`` for every request.
        * Uses ``loguru.contextualize`` so that *all* log lines emitted
          during request processing include the ``request_id``.
        * Records wall-clock duration and final HTTP status code.
        * Adds ``X-Request-ID`` to the response headers.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request with logging and request ID injection.

        Args:
            request: The incoming Starlette request.
            call_next: Callable to pass the request to the next handler.

        Returns:
            The response, enriched with the ``X-Request-ID`` header.
        """
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Bind request_id to every log line emitted during this request.
        with logger.contextualize(request_id=request_id):
            logger.info(
                "Request started: {method} {path}",
                method=request.method,
                path=request.url.path,
            )

            try:
                response: Response = await call_next(request)
            except Exception:
                # Let the exception propagate (FastAPI handlers will catch
                # it), but make sure we log the failure.
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    "Request failed: {method} {path} after {duration:.2f}ms",
                    method=request.method,
                    path=request.url.path,
                    duration=duration_ms,
                )
                raise

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "Request completed: {method} {path} → {status} in {duration:.2f}ms",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration=duration_ms,
            )

            response.headers["X-Request-ID"] = request_id
            return response
