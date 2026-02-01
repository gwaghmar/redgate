"""Centralized logging configuration for SQL Compare Tool."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "sql_compare_tool", log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger instance.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        log_dir: Directory to store log files
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # File handler with rotation by date
    log_file = log_path / f"sql_compare_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler for errors and warnings
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    
    # Detailed format for file logs
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Simpler format for console
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger instance.
    
    Args:
        name: Logger name (typically __name__ from calling module)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
