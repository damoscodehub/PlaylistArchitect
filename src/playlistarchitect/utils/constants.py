# constants.py
from enum import Enum

class Option(Enum):
    CANCEL = "Cancel"
    BACK = "Back"

class Prompt(Enum):
    SELECT = "Select an option:"
    
class Message(Enum):
    INVALID_INPUT = "Invalid input. Please try again."
    INVALID_INPUT_YN = "Invalid input. Please enter 'y' or 'n'."
    INVALID_INPUT_ID = "Invalid input. Please enter numeric playlist IDs."
    INVALID_INPUT_TIME = "Invalid time format. Please enter a valid time in HH:MM format."