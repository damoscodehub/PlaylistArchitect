import logging
import os
from typing import Dict, Callable, Set

# Configure the logger
logger = logging.getLogger(__name__)

# Allowed logging levels and their corresponding functions
ALLOWED_LOG_LEVELS: Set[str] = {"info", "warning", "error", "debug"}
LOGGING_FUNCTIONS: Dict[str, Callable[[str], None]] = {
    "info": lambda msg: logger.info(msg),
    "warning": lambda msg: logger.warning(msg),
    "error": lambda msg: logger.error(msg),
    "debug": lambda msg: logger.debug(msg),
}


def setup_logging(log_file: str = "playlist_architect.log") -> None:
    """
    Set up logging configuration.
    Args:
        log_file (str): The name of the log file to write to.
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,  # Default logging level
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join("logs", log_file)),  # Log to file
            logging.StreamHandler(),  # Log to console
        ]
    )


def log_and_print(message: str, level: str = "info") -> None:
    """
    Logs and prints a message simultaneously.
    Args:
        message (str): The message to log and print.
        level (str): The logging level ("info", "warning", "error", etc.).
    """
    try:
        # Validate the logging level
        if level not in ALLOWED_LOG_LEVELS:
            raise ValueError(f"Invalid logging level: {level}")

        # Log the message
        LOGGING_FUNCTIONS[level](message)

        # Print the message to the console
        print(message)

    except ValueError as e:
        valid_levels = ", ".join(ALLOWED_LOG_LEVELS)
        error_message = f"{str(e)}. Valid levels are: {valid_levels}."
        logger.error(error_message)
        print(f"Error: {error_message}")

    except Exception as e:
        # Handle unexpected exceptions
        logger.error(f"Unexpected error: {str(e)}")
        print(f"Unexpected error: {str(e)}")