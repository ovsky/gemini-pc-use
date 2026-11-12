"""Central logging configuration for the desktop agent."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

LOG_FILENAME = "computer-use.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """Configure console and file logging.

    Logs go to both stdout (which the GUI reads in real time) and a rotating
    file. Calling this function more than once does not duplicate handlers.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        if getattr(handler, "_gemini_pc_use", False):
            root_logger.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_FILENAME,
        maxBytes=2 * 1024 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler._gemini_pc_use = True  # type: ignore[attr-defined]
    root_logger.addHandler(file_handler)

    # Make sure Unicode characters in logs do not crash a redirected pipe.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler._gemini_pc_use = True  # type: ignore[attr-defined]
    root_logger.addHandler(stream_handler)

    root_logger.info("=" * 30 + f" NEW RUN STARTED: {datetime.now()} " + "=" * 30)
    return root_logger
