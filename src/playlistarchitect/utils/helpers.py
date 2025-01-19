from datetime import timedelta


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
        

def menu_navigation(options, prompt="Select an option:", cancel_text="Cancel", back_text="Back"):
    """
    Reusable function to handle menu navigation.
    Args:
        options (list): A list of menu options to display.
        prompt (str): The prompt to display to the user.
        cancel_text (str): Text to recognize as "Cancel".
        back_text (str): Text to recognize as "Back".
    Returns:
        int or str: The option number (1-based index), "back", or "cancel".
    """
    while True:
        print("\n" + "\n".join([f"{i}. {option}" for i, option in enumerate(options, 1)]))
        choice = input(f"{prompt} ").strip()

        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice)
        elif back_text and choice.lower() in ["b", "back"]:
            return "back"
        elif cancel_text and choice.lower() in ["c", "cancel"]:
            return "cancel"
        else:
            print("Invalid input. Please try again.")
