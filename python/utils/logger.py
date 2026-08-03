"""
IndoLens - Structured Logging Module
Provides logging levels: INFO, SUCCESS, WARNING, ERROR.
Writes logs to python/outputs/logs/recognition.log.
"""

import os
import logging
from datetime import datetime
from typing import Optional

# Define SUCCESS custom log level (between INFO and WARNING)
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")

def success(self, message, *args, **kws):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kws)

logging.Logger.success = success

_logger: Optional[logging.Logger] = None

def initialize_logger(log_file: str = "python/outputs/logs/recognition.log") -> logging.Logger:
    """Initialize file and console logging handler."""
    global _logger
    if _logger is not None:
        return _logger

    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)

    _logger = logging.getLogger("IndoLens")
    _logger.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    _logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)

    return _logger

def get_logger() -> logging.Logger:
    """Get active logger instance or initialize default."""
    global _logger
    if _logger is None:
        return initialize_logger()
    return _logger

def log_info(message: str) -> None:
    """Log INFO level message."""
    get_logger().info(message)

def log_success(message: str) -> None:
    """Log SUCCESS level message."""
    get_logger().success(message)

def log_warning(message: str) -> None:
    """Log WARNING level message."""
    get_logger().warning(message)

def log_error(message: str) -> None:
    """Log ERROR level message."""
    get_logger().error(message)

def log_execution(func_name: str, elapsed_time_sec: float) -> None:
    """Log function execution time."""
    get_logger().info(f"Execution [{func_name}] completed in {elapsed_time_sec:.4f}s")
