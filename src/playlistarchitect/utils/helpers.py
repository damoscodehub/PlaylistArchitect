from playlistarchitect.utils.constants import Prompt

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
                      
def menu_navigation(options: dict, prompt=Prompt.SELECT.value):
    """
    Reusable function to handle menu navigation with flexible keys for back and cancel.
    Args:
        options (dict): A dictionary of menu options where keys can map to constants like Option.CANCEL.value or Option.BACK.value.
        prompt (str): The prompt to display to the user.
    Returns:
        str: The selected key (e.g., "1", "a", Option.BACK.value, or Option.CANCEL.value).
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