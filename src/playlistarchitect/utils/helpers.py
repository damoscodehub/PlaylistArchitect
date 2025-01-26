from datetime import timedelta
import logging

# Configure the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_time_input(time_str):
    """Converts time in hh:mm:ss format to milliseconds using timedelta."""
    try:
        hours, minutes, seconds = map(int, time_str.split(":"))
        td = timedelta(hours=hours, minutes=minutes, seconds=seconds)
        return int(td.total_seconds() * 1000)  # Convert to milliseconds
    except ValueError:
        print("Invalid time format. Please use hh:mm:ss.")
        return None


def get_variation_input(variation_str):
    """Converts variation in minutes to milliseconds."""
    try:
        return int(float(variation_str) * 60 * 1000)  # Support decimals
    except ValueError:
        print("Invalid variation input. Please enter a number.")
        return None


def assign_temporary_ids(playlists):
    for idx, playlist in enumerate(playlists, start=1):
        playlist['id'] = idx
        
            
def get_validated_input(prompt, valid_options=None, input_type=str):
    """
    Prompt the user for input and validate it.
    Args:
        prompt (str): The message to display to the user.
        valid_options (list): A list of acceptable inputs (optional).
        input_type (type): The expected type of input (e.g., int, str).
    Returns:
        The validated user input.
    """
    while True:
        try:
            user_input = input(prompt).strip()
            # Convert input to the desired type
            user_input = input_type(user_input)

            # Check if input is in valid options
            if valid_options and user_input not in valid_options:
                print(f"Invalid option. Please choose from {valid_options}.")
                continue

            return user_input
        except ValueError:
            print(f"Invalid input. Please enter a valid {input_type.__name__}.")
            
            
def menu_navigation(options: dict, prompt="Select an option:"):
    """
    Reusable function to handle menu navigation with flexible keys for back and cancel.
    Args:
        options (dict): A dictionary of menu options where keys can map to constants like CANCEL_OPTION or BACK_OPTION.
        prompt (str): The prompt to display to the user.
    Returns:
        str: The selected key (e.g., "1", "a", BACK_OPTION, or CANCEL_OPTION).
    """
    # Display the menu
    print("\n" + "\n".join([f"{key}. {value}" for key, value in options.items()]))

    # Validate the user's input
    choice = get_validated_input(
        prompt=f"{prompt} ",
        valid_options=options.keys(),  # Validate against dictionary keys
        input_type=str
    )

    return choice  # Return the key directly


def log_and_print(message: str, level: str="info") -> None:
    """
    Logs and prints a message simultaneously.
    Args:
        message (str): The message to log and print.
        level (str): The logging level ("info", "warning", "error", etc.).
    """
    # Log the message at the specified level
    if level == "info":
        logger.info(message)
    elif level == "warning":
        logger.warning(message)
    elif level == "error":
        logger.error(message)
    elif level == "debug":
        logger.debug(message)
    else:
        logger.info(message)  # Default to "info" if level is unrecognized

    # Print the message
    print(message)
