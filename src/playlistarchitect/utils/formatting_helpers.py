def format_duration(milliseconds):
    """Convert a duration in milliseconds to the format hh:mm:ss."""
    seconds = milliseconds // 1000
    minutes = seconds // 60
    hours = minutes // 60
    return f"{hours:02}:{minutes % 60:02}:{seconds % 60:02}"


def truncate(text, length):
    """Truncate text to the specified length, adding '...' if necessary."""
    return text if len(text) <= length else text[:length - 3] + "..."
