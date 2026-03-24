"""
Structured logging setup for PimPam.

Call ``setup_logging()`` once at application startup (inside the lifespan
context manager) before any other initialisation runs.

Every module obtains its own logger via::

    import logging
    logger = logging.getLogger("pimpam.<module>")
"""
import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configure the ``pimpam`` logger hierarchy."""
    level = logging.DEBUG if settings.environment == "development" else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger("pimpam")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False
