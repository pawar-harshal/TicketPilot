"""
Thin wrapper around Python's built-in logging module.

Again, no custom logging package -- this just configures the stdlib
logging module once (level + format, from config.ini) and hands back
a named logger per module, the same way logging.getLogger(__name__)
is normally used.

This stays a foundational, low-level module (like ConfigReader) rather
than depending on Configuration.py -- Configuration.py is a higher-level
module and nothing foundational should import it, to avoid any risk of
a circular import between the two.
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler

from ticketpilot_das.utils import ConfigReader

IS_CONFIGURED = False

# Sibling of data/ (same level as ticketpilot_das/data/prompts, see
# Configuration.SYSTEM_PROMPT_PATH for the same _PACKAGE_ROOT pattern) --
# created on first use, not checked into the repo, so a fresh clone starts
# with no logs/ folder until the app actually runs once.
_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(_PACKAGE_ROOT, "logs")
LOG_FILE_PATH = os.path.join(LOG_DIR, "ticketpilot.log")


def configure_once() -> None:
    global IS_CONFIGURED
    if IS_CONFIGURED:
        return

    try:
        level_name = ConfigReader.get_section("GENERAL")["logging_level"]
    except (KeyError, FileNotFoundError):
        level_name = "INFO"
    level = getattr(logging, level_name.upper(), logging.INFO)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    root = logging.getLogger("ticketpilot_das")
    root.setLevel(level)

    # File output ONLY -- no terminal/stdout handler anymore. A new logs/
    # folder alongside data/, one log file that rotates at midnight and
    # keeps 14 days of history (ticketpilot.log, ticketpilot.log.2026-11-01,
    # ...), so a single file doesn't grow forever and old days are still
    # around to look back at after a crash or a long demo session.
    os.makedirs(LOG_DIR, exist_ok=True)
    file_handler = TimedRotatingFileHandler(
        LOG_FILE_PATH, when="midnight", backupCount=14, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    root.propagate = False

    # uvicorn runs its OWN loggers ("uvicorn", "uvicorn.error",
    # "uvicorn.access") with their own default console handler -- that's
    # what prints the "INFO:     127.0.0.1:... "GET ..." 200 OK" lines,
    # completely separate from the ticketpilot_das logger configured
    # above. Silencing our own handler alone would leave those still
    # printing to the terminal. Strip their default handlers and point
    # them at the SAME file instead, so every line -- ours and uvicorn's
    # request/startup logs -- ends up in one place with nothing left on
    # stdout.
    # IMPORTANT: a logger with no level of its own (NOTSET) climbs the
    # hierarchy for an *effective* level -- and since log_config=None stops
    # uvicorn from ever setting one, these three loggers would fall back to
    # the Python default of WARNING. Their request/startup lines are logged
    # at INFO, so without an explicit setLevel() here every one of them is
    # silently swallowed before it even reaches the handler -- confirmed by
    # a real test: a login POST reached the server and got a real response,
    # but nothing about it showed up in the log file at all.
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.addHandler(file_handler)
        uvicorn_logger.propagate = False
        uvicorn_logger.setLevel(level)

    IS_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_once()
    return logging.getLogger(f"ticketpilot_das.{name}")
