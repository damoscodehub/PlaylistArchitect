import logging
import logging.config
import os
import json

logger = logging.getLogger(__name__)

def setup_logging(config_file: str = "logging_config.json") -> None:
    """
    Set up logging using a configuration file.
    Args:
        config_file (str): The name of the logging configuration file (default: "logging_config.json").
    """
    def setup_fallback_logging():
        """Configure basic logging as a fallback when main configuration fails."""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        logger.warning("Using fallback logging configuration")

    # Step 1: Resolve the config_file path
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", config_file
        )
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Logging configuration file not found: {config_path}")
    except Exception as e:
        print(f"Error resolving logging configuration file: {e}")
        setup_fallback_logging()
        logger.error(f"Failed to resolve logging configuration file: {e}")
        return

    # Step 2: Ensure the logs directory exists and is writable
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    try:
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        if not os.access(logs_dir, os.W_OK):
            raise PermissionError(f"The application does not have write permissions for the '{logs_dir}' directory.")
    except Exception as e:
        print(f"Error setting up logging directory: {e}")
        setup_fallback_logging()
        logger.error(f"Failed to initialize logging directory: {e}")
        return

    # Step 3: Configure logging
    try:
        with open(config_path, "r") as file:
            config = json.load(file)
        logging.config.dictConfig(config)
        logger.debug("Logging system initialized")  # Changed to debug level
    except Exception as e:
        print(f"Failed to load logging configuration: {e}")
        setup_fallback_logging()
        logger.error(f"Failed to load logging configuration: {e}")