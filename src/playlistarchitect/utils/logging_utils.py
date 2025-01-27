import logging
import logging.config
import os
import json
from typing import Dict, Callable, Set

# Allowed logging levels and their corresponding functions
ALLOWED_LOG_LEVELS: Set[str] = {"info", "warning", "error", "debug"}


def setup_logging(config_file: str = "logging_config.json") -> None:
    """
    Set up logging using a configuration file.
    Args:
        config_file (str): The path to the logging configuration file.
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Load the logging configuration
    try:
        with open(config_file, "r") as file:
            config = json.load(file)
        logging.config.dictConfig(config)
        logging.getLogger(__name__).info("Logging configured successfully.")
    except Exception as e:
        print(f"Failed to load logging configuration: {e}")
        logging.basicConfig(level=logging.INFO)  # Fallback to basic config