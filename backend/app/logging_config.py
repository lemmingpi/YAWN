"""Logging configuration for Web Notes backend."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import settings


def setup_logging() -> None:
    """Configure logging to write to console and optionally to file."""
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Remove any existing handlers
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = logging.Formatter(
        "%(levelname)s:     %(message)s",
    )

    # Console handler (stdout) - for uvicorn compatibility
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (optional, controlled by LOG_TO_FILE)
    if settings.LOG_TO_FILE:
        # Create logs directory if it doesn't exist
        log_file = Path(settings.LOG_FILE)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # Log initial message
        root_logger.info("=" * 80)
        root_logger.info("Logging configured - writing to both console and file")
        root_logger.info(f"Log file: {settings.LOG_FILE}")
        root_logger.info(f"Log level: {settings.LOG_LEVEL}")
        root_logger.info("=" * 80)
    else:
        # Log to console only
        root_logger.info("Logging configured - console only (file logging disabled)")
        root_logger.info(f"Log level: {settings.LOG_LEVEL}")
        root_logger.info("To enable file logging, set LOG_TO_FILE=True in env")
