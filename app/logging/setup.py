"""Loguru-based logging configuration for the OMS application.

Responsibilities:
    1. Remove all default Loguru handlers.
    2. Install a JSON sink for production or a human-readable sink for
       development.
    3. Intercept standard-library loggers (``uvicorn``, ``sqlalchemy``,
       ``fastapi``) and route them through Loguru so every log line has
       a consistent format and includes the Loguru context (e.g.
       ``request_id``).
"""

import logging
import sys

from loguru import logger

from app.core.config import get_settings


class InterceptHandler(logging.Handler):
    """Standard-library logging handler that forwards records to Loguru.

    This handler is installed on the root logger (and on specific
    third-party loggers) so that *all* log output flows through Loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Forward a stdlib ``LogRecord`` to the matching Loguru level.

        Args:
            record: The incoming standard-library log record.
        """
        # Map stdlib level to Loguru level name.
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the caller frame that originated the log call so that
        # Loguru shows the correct file / line number.
        frame = logging.currentframe()
        depth = 0
        while frame is not None:
            filename = frame.f_code.co_filename
            if filename == logging.__file__:
                frame = frame.f_back
                depth += 1
                continue
            break

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


# Names of third-party loggers that we intercept.
_INTERCEPTED_LOGGERS: list[str] = [
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
    "sqlalchemy",
    "sqlalchemy.engine",
    "fastapi",
]


def setup_logging() -> None:
    """Configure Loguru as the application-wide logging backend.

    This function should be called **once** during application startup,
    ideally before any other module emits a log line.

    Behaviour:
        * Removes all existing Loguru handlers.
        * Adds a *stderr* sink with either JSON format (production) or
          human-readable coloured format (development).
        * Replaces the root logger's handlers and all known third-party
          handlers with ``InterceptHandler``.
    """
    settings = get_settings()

    # 1. Remove existing Loguru handlers.
    logger.remove()

    # 2. Determine format / serialisation based on environment.
    if settings.log_format == "json":
        logger.add(
            sys.stderr,
            level=settings.log_level.upper(),
            serialize=True,
            backtrace=True,
            diagnose=not settings.is_production,
            enqueue=True,  # thread-safe
        )
    else:
        logger.add(
            sys.stderr,
            level=settings.log_level.upper(),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "{extra[request_id]} - <level>{message}</level>"
                if False  # request_id is added dynamically via contextualize
                else (
                    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                    "<level>{level: <8}</level> | "
                    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                    "<level>{message}</level>"
                )
            ),
            colorize=True,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )

    # 3. Intercept standard-library loggers.
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.log_level.upper())

    for logger_name in _INTERCEPTED_LOGGERS:
        third_party_logger = logging.getLogger(logger_name)
        third_party_logger.handlers = [InterceptHandler()]
        third_party_logger.propagate = False

    logger.info(
        "Logging configured (level={level}, format={fmt}, env={env})",
        level=settings.log_level,
        fmt=settings.log_format,
        env=settings.app_env,
    )
