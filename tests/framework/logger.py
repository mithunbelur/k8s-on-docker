"""
Centralized logging configuration for the test framework.
"""

import logging
import os
from typing import Optional

# Global logger instance
_logger: Optional[logging.Logger] = None

def get_logger(name: str = "Traffic Director") -> logging.Logger:
    """Get the centralized logger instance."""
    global _logger
    
    if _logger is None:
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.INFO)

        # Remove all existing handlers to avoid duplicate/missing logs
        if _logger.hasHandlers():
            _logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        _logger.addHandler(console_handler)
        
        # File handler if log file is specified
        log_file = os.environ.get('TEST_LOG_FILE')
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            _logger.addHandler(file_handler)
            _logger.info(f"Logging to file: {log_file}")
        else:
            # No log file specified, only console output
            _logger.addHandler(console_handler)
            _logger.info("No log file specified, logging to console only.")
        
        # Set debug level if enabled
        debug_enabled = os.environ.get('TEST_DEBUG', '').lower() in ['true', '1', 'yes']
        if debug_enabled:
            _logger.setLevel(logging.DEBUG)
            console_handler.setLevel(logging.DEBUG)
            if log_file:
                file_handler.setLevel(logging.DEBUG)
    
    return _logger
