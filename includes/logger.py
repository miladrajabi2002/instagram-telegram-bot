"""Logging configuration."""
import logging
import sys
from pathlib import Path

import coloredlogs

import config

# Create logs directory
log_file = Path(config.LOG_FILE)
log_file.parent.mkdir(parents=True, exist_ok=True)

# Configure root logger
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)


def setup_logger(name: str) -> logging.Logger:
    """Setup logger for a module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Add colored output for console
    coloredlogs.install(
        level=config.LOG_LEVEL,
        logger=logger,
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return logger
