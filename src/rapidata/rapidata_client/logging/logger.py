"""
Provides centralized logging configuration for the Rapidata Python SDK.
It sets up a logger instance that is used throughout the SDK to provide
consistent logging behavior and formatting.

The logger is configured with sensible defaults but can be customized using the
`configure_logger` function to adjust log levels, output destinations, and formatting.

Example:
    Basic usage with default configuration:
    ```python
    from rapidata import logger
    
    logger.info("This is an info message")
    logger.error("This is an error message")
    ```
    
    Custom configuration:
    ```python
    from rapidata import configure_logger
    
    # Configure with DEBUG level and file output
    configure_logger(
        level="DEBUG",
        log_file="/path/to/logs/rapidata.log"
    )
    ```
"""
import logging
import os
from typing import Optional

# Create module-level logger
logger = logging.getLogger("rapidata")

def configure_logger(
    level: str = "WARNING",
    log_file: Optional[str] = None,
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
) -> None:
    """
    Configure the logger with custom settings.
    
    This function allows you to customize the logging behavior for the entire SDK.
    You can set the log level, specify a file for log output, and customize the log message format.
    
    Note:
        This function removes any existing handlers before adding new ones,
        so it's safe to call multiple times to reconfigure logging.
    
    Args:
        level: The logging level to set. Must be one of:\n
            - "DEBUG": Detailed information for diagnosing problems
            - "INFO": General information about program execution
            - "WARNING": Something unexpected happened (default)
            - "ERROR": A serious problem occurred
            - "CRITICAL": A very serious error occurred
            
        log_file: Optional path to a file where logs should be written.
            If provided, logs will be written to both console and file.
            The directory will be created if it doesn't exist.
            
        format_string: Custom format string for log messages.
            Uses Python logging format specifications.
            Default includes timestamp, logger name, level, and message.
    
    Example:
        Configure for development with debug logging:
        ```python
        configure_logger(level="DEBUG")
        ```
        
        Configure for production with file logging:
        ```python
        configure_logger(
            level="INFO",
            log_file="/var/log/rapidata/app.log"
        )
        ```
        
        Configure with custom format:
        ```python
        configure_logger(
            level="INFO",
            format_string="[%(levelname)s] %(message)s"
        )
        ```
    """
    # Map string levels to logging constants for validation and conversion
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO, 
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    numeric_level = level_map.get(level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Remove existing handlers if any
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

configure_logger()
