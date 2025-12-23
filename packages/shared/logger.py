"""Centralized logging configuration for MailShieldAI services.

This module provides a consistent logging setup across all services (API and workers)
with support for JSON and text formats, configurable log levels, and service context injection.
"""

import logging
import os
import sys
from typing import Optional

from pythonjsonlogger import json as jsonlogger


def setup_logging(
    service_name: str,
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> logging.Logger:
    """Configure logging for a service with consistent format.
    
    Args:
        service_name: Name of the service (e.g., 'api', 'intent-worker')
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). 
                   Defaults to LOG_LEVEL env var or INFO.
        log_format: Format type ('json' or 'text'). 
                    Defaults to LOG_FORMAT env var or 'json'.
    
    Returns:
        Configured root logger instance.
    
    Example:
        >>> from packages.shared.logger import setup_logging
        >>> logger = setup_logging("my-service")
        >>> logger.info("Service started")
    """
    # Determine configuration from arguments or environment variables
    level_str = log_level or os.getenv("LOG_LEVEL", "INFO")
    format_type = log_format or os.getenv("LOG_FORMAT", "json")
    
    # Convert level string to logging constant
    numeric_level = getattr(logging, level_str.upper(), logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers to prevent duplicates
    root_logger.handlers.clear()
    
    # Set log level
    root_logger.setLevel(numeric_level)
    
    # Create console handler (stdout for Cloud Run compatibility)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    
    # Configure formatter based on format type
    if format_type.lower() == "json":
        # JSON formatter with renamed fields for better observability
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            rename_fields={"levelname": "severity", "asctime": "timestamp"},
        )
        # Add service name to all records via filter
        handler.addFilter(ServiceContextFilter(service_name))
    else:
        # Text formatter with severity-first format
        formatter = logging.Formatter(
            fmt=f"%(levelname)s: [%(asctime)s] [{service_name}] %(message)s",
            datefmt="%H:%M:%S",
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Log configuration info
    root_logger.info(
        f"Logging configured for {service_name} (level={level_str.upper()}, format={format_type})"
    )
    
    return root_logger


class ServiceContextFilter(logging.Filter):
    """Logging filter that adds service name to all log records."""
    
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add service_name field to the log record."""
        record.service_name = self.service_name
        return True
