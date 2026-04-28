"""Structured logging setup for the payment service."""

import logging
import sys


def configure_logging(debug: bool = False) -> None:
    """Configure root logger with a structured format.

    Uses a simple JSON-like format suitable for log aggregation systems
    (Loki, Datadog, etc.).  In production set debug=False; in development
    set debug=True to get DEBUG-level output.
    """
    level = logging.DEBUG if debug else logging.INFO

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        stream=sys.stdout,
    )

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO if debug else logging.WARNING)
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
