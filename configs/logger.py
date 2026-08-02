"""
configs/logger.py — Central logging configuration for ArchFox.

Every module should do:
    from configs.logger import get_logger
    logger = get_logger(__name__)

Call setup_logging() ONCE at application startup (in test_run.py or main.py).
The log file lives at the root of ArchFox: archfox.log
It is CLEARED on every run so you always see a fresh log.
"""
import logging
import os
import sys

# Root of the ArchFox project (one level up from this file)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_FILE = os.path.join(_PROJECT_ROOT, "archfox.log")

LOG_FORMAT  = "[%(asctime)s] %(levelname)-5s  %(name)s — %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging():
    """
    Configure the root logger once.
    - archfox.log  (root of project) → DEBUG level, cleared on every run
    - Console (stdout)               → INFO level
    """
    global _configured
    if _configured:
        return
    _configured = True

    # File handler — mode='w' clears the file at the start of every run
    file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # Console handler — only INFO and above to keep terminal readable
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    handlers = []
    # If pytest is running, avoid attaching handlers that will clash with its stream capturing
    if "pytest" not in sys.modules:
        handlers = [file_handler, console_handler]

    # Root logger — captures ALL loggers in the project
    logging.basicConfig(level=logging.DEBUG, handlers=handlers)

    # Silence noisy third-party libraries (keep our own project logs visible)
    for noisy in ("httpx", "httpcore", "neo4j", "neo4j.notifications",
                  "sentence_transformers", "huggingface_hub", "openai",
                  "openai._base_client", "git", "git.cmd",
                  "chromadb", "chromadb.config"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger. Always use __name__ as the argument:
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)
