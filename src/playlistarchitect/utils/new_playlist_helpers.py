import random
import logging
from typing import List, Dict, Optional, Tuple, Any, Callable
from tabulate import tabulate
from playlistarchitect.utils.formatting_helpers import format_duration
from playlistarchitect.utils.helpers import menu_navigation
from playlistarchitect.operations.retrieve_playlists_table import save_playlists_to_file
from playlistarchitect.utils.constants import Message, Prompt

logger = logging.getLogger(__name__)

SELECT_IDS = "Set the comma-separated track blocks in the format 'ID' (to use all the available time) or 'ID-HH:MM' (to use a custom time). 'b' to go back.\n> "

def format_duration_hhmm(seconds):
    """Format seconds to hh:mm format without seconds"""
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}"

def safe_input(prompt, validator=None, error_msg=Message.INVALID_INPUT.value):
    """
    Handle input with validation and error messages
    
    Parameters:
    prompt (str): The prompt to display to the user
    validator (Callable): Function that validates the input, returns True if valid
    error_msg (str): Error message to display if validation fails
    
    Returns:
    str: The validated user input
    """
    while True:
        user_input = input(prompt).strip()
        if user_input.lower() in ['b', 'back', 'c', 'cancel']:
            return user_input
        
        if validator is None or validator(user_input):
            return user_input
        
        print(error_msg)

def validate_time_format(time_str):
    """
    Validate time format is HH:MM or HH:MM:SS
    
    Parameters:
    time_str (str): The time string to validate
    
    Returns:
    bool: True if the format is valid, False otherwise
    """
    if not time_str:
        return False
    
    parts = time_str.split(':')
    if len(parts) not in [2, 3]:
        return False
    
    try:
        # Check if all parts are valid integers
        for part in parts:
            int(part)
        return True
    except ValueError:
        return False

def parse_playlist_selection(input_str, playlists):
    """
    Parse the input string in the format 'ID-hh:mm' or 'ID'.
    Returns a list of tuples (playlist_id, duration_seconds) and a list of invalid IDs.

    Parameters:
    input_str (str): Comma-separated string of playlist IDs with optional durations
    playlists (List[Dict]): List of all playlists

    Returns:
    Tuple[List[Tuple[int, Optional[int]]], List[int]]: List of (playlist_id, duration_seconds) tuples and list of invalid IDs
    """
    selected_playlists = []
    invalid_ids = []
    
    for item in input_str.split(','):
        item = item.strip()
        if not item:
            continue  # Skip empty entries
        
        if '-' in item:
            playlist_id_str, time_str = item.split('-')
        else:
            playlist_id_str, time_str = item, None
        
        try:
            playlist_id = int(playlist_id_str.strip())
            # Check if the playlist ID exists in the playlists
            if not any(p["id"] == playlist_id for p in playlists):
                invalid_ids.append(playlist_id)
                continue
            
            # Parse time if provided
            duration_seconds = None
            if time_str:
                if ':' in time_str:
                    parts = time_str.strip().split(':')
                    if len(parts) == 2:
                        hours, minutes = map(int, parts)
                        duration_seconds = (hours * 3600) + (minutes * 60)
                    else:
                        print(f"Invalid time format for '{item}'. Expected hh:mm. Skipping.")
                        continue
                else:
                    print(f"Invalid time format for '{item}'. Expected hh:mm. Skipping.")
                    continue
            
            selected_playlists.append((playlist_id, duration_seconds))
        except ValueError:
            invalid_ids.append(playlist_id_str)
    
    return selected_playlists, invalid_ids

def calculate_and_display_blocks_totals(selected_blocks):
    """
    Calculate and display the total number of blocks and total playtime.
    Handles singular and plural cases for the number of blocks.
    
    Parameters:
    selected_blocks (List[Dict]): List of selected playlist blocks
    """
    # Calculate total selected blocks and total playtime
    total_blocks = len(selected_blocks)
    total_playtime_seconds = sum(
        block.get("duration_seconds", 0) or 0  # Handle None case
        for block in selected_blocks
    )
    total_playtime_str = format_duration_hhmm(total_playtime_seconds)

    # Handle singular/plural for blocks
    if total_blocks == 1:
        print(f"Total selected: {total_blocks} block, {total_playtime_str} playback time.")
    else:
        print(f"Total selected: {total_blocks} blocks, {total_playtime_str} playback time.")
        
def calculate_available_time(playlist_id, selected_playlist_blocks, playlists):
    """
    Calculate available time for a playlist based on current selections
    
    Parameters:
    playlist_id (int): The playlist ID
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlists (List[Dict]): List of all playlists
    
    Returns:
    int: Available time in seconds
    """
    playlist = next((p for p in playlists if p["id"] == playlist_id), None)
    if not playlist:
        return 0
    
    total_seconds = playlist.get("duration_ms", 0) // 1000
    used_seconds = 0
    
    # Calculate used time for this playlist
    for block in selected_playlist_blocks:
        if block["playlist"]["id"] == playlist_id:
            if block.get("duration_seconds") is None:
                # If any block uses the full playlist, all time is used
                return 0
            else:
                used_seconds += block.get("duration_seconds", 0)
    
    return max(0, total_seconds - used_seconds)

def process_playlist_selection(selected_input, playlists, selected_playlist_blocks):
    """
    Process playlist selection input and add valid selections to blocks.
    
    Parameters:
    selected_input (str): User input with playlist selections
    playlists (List[Dict]): List of all playlists
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    
    Returns:
    List[int]: Indices of newly added blocks
    """
    start_block_index = len(selected_playlist_blocks)
    selected_playlists_with_time, invalid_ids = parse_playlist_selection(selected_input, playlists)  # Fixed: Added playlists argument
    
    if not selected_playlists_with_time:
        print("No valid playlists selected.")
        return []
    
    no_available_time_ids = []
    for playlist_id, duration_seconds in selected_playlists_with_time:
        playlist = next((p for p in playlists if p["id"] == playlist_id), None)
        if playlist:
            # If duration_seconds is None, use available time
            if duration_seconds is None:
                available_seconds = calculate_available_time(playlist_id, selected_playlist_blocks, playlists)
                if available_seconds <= 0:
                    no_available_time_ids.append(playlist_id)
                    continue
                duration_seconds = available_seconds
                
            selected_playlist_blocks.append({
                "playlist": playlist,
                "duration_seconds": duration_seconds
            })
    
    # Notify if any playlists had no available time
    if no_available_time_ids:
        if len(no_available_time_ids) == 1:
            print(f"The playlist with ID {no_available_time_ids[0]} has no available playback time. No further track block was created with it.")
        else:
            id_str = ", ".join(str(id) for id in no_available_time_ids)
            print(f"The playlists with IDs {id_str} have no available playback time. No further track blocks were created with them.")
    
    # Return list of indices of newly added blocks
    return list(range(start_block_index, len(selected_playlist_blocks)))

def display_selected_blocks(selected_playlist_blocks, playlists):
    """
    Display selected blocks with detailed information.
    
    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlists (List[Dict]): List of all playlists
    """
    # Only show the detailed blocks table
    print("\nSelected blocks:")
    blocks_data = []
    for i, block in enumerate(selected_playlist_blocks):
        playlist = block["playlist"]
        duration_seconds = block.get("duration_seconds")
        
        if duration_seconds is None:
            # Show actual total time instead of "Full playlist"
            total_seconds = playlist.get("duration_ms", 0) // 1000
            duration_str = format_duration_hhmm(total_seconds)
        else:
            duration_str = format_duration_hhmm(duration_seconds)
            
        blocks_data.append([
            i+1,
            playlist["id"],
            playlist["user"],
            playlist["name"],
            duration_str
        ])
    
    print()
    print(tabulate(
        blocks_data,
        headers=["Block #", "ID", "User", "Name", "Selected Time"],
        tablefmt="simple"
    ))

    # Display totals using the reusable function
    print()
    calculate_and_display_blocks_totals(selected_playlist_blocks)
    
def validate_playlist_blocks(selected_playlist_blocks, playlists, new_block_indices=None):
    """
    Validate if selected block times exceed available times and
    interactively correct problematic blocks.
    
    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlists (List[Dict]): List of all playlists
    new_block_indices (Optional[List[int]]): Indices of newly added blocks to validate
    
    Returns:
    bool: True if all blocks are valid or have been fixed
    """
    # If new_block_indices is None, validate all blocks
    indices_to_validate = new_block_indices if new_block_indices is not None else range(len(selected_playlist_blocks))
    
    # First, identify problematic blocks
    problematic_blocks = []
    for i in indices_to_validate:
        block = selected_playlist_blocks[i]
        playlist_id = block["playlist"]["id"]
        duration_seconds = block.get("duration_seconds")
        
        # Skip blocks with None duration (full playlist)
        if duration_seconds is None:
            continue
        
        # Calculate available time excluding this block's contribution
        temp_blocks = selected_playlist_blocks.copy()
        temp_blocks.pop(i)
        available_seconds = calculate_available_time(playlist_id, temp_blocks, playlists)
        
        if duration_seconds > available_seconds:
            problematic_blocks.append((i, block, available_seconds))
    
    # If no problematic blocks, return True
    if not problematic_blocks:
        return True
    
    # Display problematic blocks
    block_numbers = ", ".join(str(i+1) for i, _, _ in problematic_blocks)
    print(f"The time selected for blocks #{block_numbers} is greater than the time available of each playlist")
    
    # Create table with all blocks, highlighting problematic ones
    all_blocks_data = []
    for i, block in enumerate(selected_playlist_blocks):
        playlist = block["playlist"]
        duration_seconds = block.get("duration_seconds")
        
        # Check if this is a problematic block
        is_problematic = any(pb_i == i for pb_i, _, _ in problematic_blocks)
        
        # Calculate the available time for this block
        temp_blocks = selected_playlist_blocks.copy()
        temp_blocks.pop(i)
        available_seconds = calculate_available_time(playlist["id"], temp_blocks, playlists)
        
        # Format duration
        if duration_seconds is None:
            total_seconds = playlist.get("duration_ms", 0) // 1000
            selected_str = format_duration_hhmm(total_seconds)
        else:
            selected_str = format_duration_hhmm(duration_seconds)
        
        # Format available column
        if is_problematic:
            available_str = format_duration_hhmm(available_seconds)
            warning = "X"
        else:
            available_str = "✓"
            warning = ""
            
        all_blocks_data.append([
            warning,
            i+1,
            playlist["id"],
            playlist["user"],
            playlist["name"],
            selected_str,
            available_str
        ])
    
    print(tabulate(
        all_blocks_data,
        headers=["!", "Block #", "ID", "User", "Name", "Selected", "Available"],
        tablefmt="simple"
    ))
    
    # Fix problematic blocks one by one
    for i, block, available_seconds in problematic_blocks:
        playlist = block["playlist"]
        fixed = False
        
        while not fixed:
            prompt = f"For block #{i+1} (ID: {playlist['id']}, User: {playlist['user']}, Name: {playlist['name']})\n"
            prompt += f"Select a time (in HH:MM) up to {format_duration_hhmm(available_seconds)}: "
            
            time_str = input(prompt).strip()
            
            # Parse the time input
            try:
                if ':' in time_str:
                    parts = time_str.strip().split(':')
                    if len(parts) == 2:
                        hours, minutes = map(int, parts)
                        new_duration_seconds = (hours * 3600) + (minutes * 60)
                        
                        if new_duration_seconds <= available_seconds:
                            # Update the block duration
                            selected_playlist_blocks[i]["duration_seconds"] = new_duration_seconds
                            fixed = True
                        else:
                            print(f"Time exceeds available time. Maximum is {format_duration_hhmm(available_seconds)}.")
                    else:
                        print(Message.INVALID_INPUT_TIME.value)
                else:
                    print(Message.INVALID_INPUT_TIME.value)
            except ValueError:
                print("Invalid time format. Please enter hours and minutes as numbers.")
    
    return True

def display_playlist_selection_table(playlists, selected_blocks):
    """
    Display playlist selection table with usage statistics.
    
    Parameters:
    playlists (List[Dict]): List of all playlists
    selected_blocks (List[Dict]): Currently selected playlist blocks
    """
    # Calculate usage by playlist ID
    usage_by_id = {}
    for block in selected_blocks:
        playlist_id = block["playlist"]["id"]
        duration_seconds = block.get("duration_seconds", 0) or 0
        
        if playlist_id not in usage_by_id:
            usage_by_id[playlist_id] = {
                "blocks": 0,
                "used_seconds": 0
            }
        
        usage_by_id[playlist_id]["blocks"] += 1
        usage_by_id[playlist_id]["used_seconds"] += duration_seconds
    
    # Create table data
    table_data = []
    for playlist in playlists:
        playlist_id = playlist["id"]
        usage = usage_by_id.get(playlist_id, {"blocks": 0, "used_seconds": 0})
        
        # Calculate total, used and available durations
        total_seconds = playlist.get("duration_ms", 0) // 1000
        used_seconds = usage["used_seconds"]
        
        # If full playlist is used in any block, consider all used
        if any(block.get("duration_seconds") is None for block in selected_blocks 
               if block["playlist"]["id"] == playlist_id):
            used_seconds = total_seconds
            
        available_seconds = max(0, total_seconds - used_seconds)
        
        # Display blocks column
        blocks_display = str(usage["blocks"]) if usage["blocks"] > 0 else "-"
        
        # Format available time
        available_time_str = "✗" if available_seconds == 0 else format_duration_hhmm(available_seconds)
        
        table_data.append([
            blocks_display,
            playlist["id"],
            playlist["user"],
            playlist["name"],
            playlist["track_count"],
            format_duration_hhmm(total_seconds),
            format_duration_hhmm(used_seconds),
            available_time_str
        ])
    
    print()
    print(tabulate(
        table_data,
        headers=["# Blocks", "ID", "User", "Name", "Tracks", "Total", "Used", "Available"],
        tablefmt="simple"
    ))
    
    total_playlists = len(playlists)
    total_tracks = sum(p.get("track_count", 0) for p in playlists)
    total_duration_ms = sum(p.get("duration_ms", 0) for p in playlists)
    total_duration_str = format_duration(total_duration_ms)
    
    print(f"\n{total_playlists} playlists, {total_tracks} tracks, {total_duration_str} playback time.")

    # Display totals using the reusable function
    calculate_and_display_blocks_totals(selected_blocks)
    
def handle_add_playlists(playlists, selected_playlist_blocks, is_initial_selection=False):
    """
    Handle the adding of playlists to selection.

    Parameters:
    playlists (List[Dict]): List of all playlists
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    is_initial_selection (bool): Whether this is the initial selection

    Returns:
    bool: True if playlists were added, False if the user went back
    """
    while True:
        display_playlist_selection_table(playlists, selected_playlist_blocks)
        
        selected_input = input(SELECT_IDS).strip()
        if selected_input.lower() in ['b', 'back']:
            return False  # Signal that the user wants to go back
        
        try:
            # Parse the input and validate IDs
            selected_playlists_with_time, invalid_ids = parse_playlist_selection(selected_input, playlists)
            
            if not selected_playlists_with_time:
                print("No valid IDs entered.")
                continue  # Reprompt for input
            
            if invalid_ids:
                print(f"Invalid ID(s) ignored: {', '.join(map(str, invalid_ids))}")
            
            new_block_indices = process_playlist_selection(selected_input, playlists, selected_playlist_blocks)
            
            if new_block_indices:
                validate_playlist_blocks(selected_playlist_blocks, playlists, new_block_indices)
                return True  # Signal that playlists were added
        except ValueError:
            print("Invalid input format. Only positive integers values are expected.")

def handle_remove_playlists(selected_playlist_blocks, playlists):
    """
    Handle the removal of playlists from selection.
    
    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlists (List[Dict]): List of all playlists
    """
    if not selected_playlist_blocks:
        print("No playlists to remove.")
        return
        
    # Display the block table only once at the start
    display_selected_blocks(selected_playlist_blocks, playlists)
    
    while True:  # Loop to reprompt if there are invalid block numbers
        remove_blocks = input("Enter block numbers to remove (comma-separated) or 'b' to go back: ").strip()
        
        # Handle "b" or "back" to go back
        if remove_blocks.lower() in ['b', 'back']:
            return  # Exit the function and go back to the previous menu
            
        if not remove_blocks:
            continue  # Reprompt if no input is provided
            
        try:
            # Parse input into block indices
            remove_indices = [int(x.strip()) - 1 for x in remove_blocks.split(",") if x.strip()]
            
            # Validate block indices
            invalid_indices = [
                idx + 1 for idx in remove_indices
                if idx < 0 or idx >= len(selected_playlist_blocks)
            ]
            
            if invalid_indices:
                # Display all invalid block numbers in a single line
                print(f"Invalid block numbers: {', '.join(map(str, invalid_indices))}")
                continue  # Reprompt for input without re-displaying the table
            
            # Sort indices in descending order to avoid index shifting during removal
            remove_indices.sort(reverse=True)
            
            # Remove valid blocks
            for idx in remove_indices:
                del selected_playlist_blocks[idx]
            
            print("Blocks removed successfully.")
            break  # Exit the loop after successful removal
            
        except ValueError:
            print("Invalid input format. Only positive integers values are expected.")

def handle_shuffle_blocks(selected_playlist_blocks):
    """
    Handle the shuffling of selected playlist blocks by reassigning their positions randomly.

    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks

    Returns:
    bool: True if the user cancels or goes back, False otherwise
    """
    while True:
        # Prompt for blocks to shuffle
        shuffle_input = input(
            "Enter the numbers of the blocks (comma-separated) to shuffle or 'a' to shuffle all: "
        ).strip().lower()

        # Handle "back" or "cancel"
        if shuffle_input in ['b', 'back']:
            return False
        if shuffle_input in ['c', 'cancel', 'main', 'main menu']:
            return True

        # Handle "a" to shuffle all
        if shuffle_input == 'a':
            block_indices = list(range(len(selected_playlist_blocks)))
        else:
            # Parse and validate block numbers
            try:
                block_indices = [int(x.strip()) - 1 for x in shuffle_input.split(",") if x.strip()]
                invalid_indices = [idx + 1 for idx in block_indices if idx < 0 or idx >= len(selected_playlist_blocks)]
                valid_indices = [idx for idx in block_indices if 0 <= idx < len(selected_playlist_blocks)]

                if invalid_indices:
                    if not valid_indices:
                        # No valid block numbers entered
                        print("No valid block numbers inserted.")
                        continue  # Reprompt for input
                    else:
                        # At least one valid and one invalid block number
                        print(f"Invalid block numbers: {', '.join(map(str, invalid_indices))}")
                        options = {
                            "1": "Ignore them and shuffle the rest",
                            "2": "Ignore them and enter additional block numbers to shuffle",
                            "3": "Restart the selection of blocks to shuffle",
                            "b": "Back",
                            "c": "Cancel and go to main menu",
                        }
                        option = menu_navigation(options, prompt=Prompt.SELECT.value)

                        if option == "1":
                            block_indices = valid_indices
                        elif option == "2":
                            while True:
                                additional_input = input("Enter additional block numbers (comma-separated) to shuffle: ").strip()
                                additional_indices = [int(x.strip()) - 1 for x in additional_input.split(",") if x.strip()]
                                # Validate additional block numbers
                                invalid_additional_indices = [idx + 1 for idx in additional_indices if idx < 0 or idx >= len(selected_playlist_blocks)]
                                valid_additional_indices = [idx for idx in additional_indices if 0 <= idx < len(selected_playlist_blocks)]

                                if invalid_additional_indices:
                                    # If there are invalid block numbers, print them and reprompt
                                    print(f"Invalid block numbers: {', '.join(map(str, invalid_additional_indices))}")
                                    # Add valid additional indices to the list of valid indices
                                    valid_indices.extend(valid_additional_indices)
                                    continue  # Reprompt for additional input
                                else:
                                    # If all additional block numbers are valid, add them to the list of valid indices
                                    valid_indices.extend(valid_additional_indices)
                                    block_indices = valid_indices
                                    break
                        elif option == "3":
                            continue  # Restart the outer loop
                        elif option in ['b', 'back']:
                            return False
                        elif option in ['c', 'cancel', 'main', 'main menu']:
                            return True
                else:
                    # All block numbers are valid
                    block_indices = valid_indices
            except ValueError:
                print("Invalid input. Expected comma-separated block numbers or 'a'.")
                continue

        # Ensure at least one valid block is selected
        if not block_indices:
            print("No valid blocks selected.")
            continue

        # Display blocks to shuffle
        print(f"Blocks to shuffle: {', '.join(map(str, [idx + 1 for idx in block_indices]))}")

        # Prompt to proceed or restart
        options = {
            "1": "Proceed to shuffle",
            "2": "Restart the selection",
            "b": "Back",
            "c": "Cancel and go to main menu",
        }
        option = menu_navigation(options, prompt=Prompt.SELECT.value)

        if option == "1":
            # Reassign block positions randomly
            for idx in block_indices:
                # Generate a random new position (different from the current one)
                new_position = idx
                while new_position == idx:
                    new_position = random.randint(0, len(selected_playlist_blocks) - 1)

                # Move the block to the new position
                block_to_move = selected_playlist_blocks.pop(idx)
                selected_playlist_blocks.insert(new_position, block_to_move)

            print("Blocks shuffled successfully.")
            return False  # Go back to the main menu
        elif option == "2":
            continue  # Restart the outer loop
        elif option in ['b', 'back']:
            return False
        elif option in ['c', 'cancel', 'main', 'main menu']:
            return True
                
def handle_reorder_blocks(selected_playlist_blocks, playlists):
    """
    Handle the reordering of selected playlist blocks.

    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlists (List[Dict]): List of all playlists

    Returns:
    bool: True if the user cancels or goes back, False otherwise
    """
    # Check if there are enough blocks to reorder
    if len(selected_playlist_blocks) < 2:
        print("There is only one block. If I could rearrange it I would have already conquered the multiverse.")
        return False

    # Display current blocks
    display_selected_blocks(selected_playlist_blocks, playlists)
    print()

    # Main loop for reordering or shuffling
    while True:
        # Prompt for the block to reorder or shuffle
        block_input = input(
            "Enter a block number to reorder or 's' to see the shuffle options: "
        ).strip().lower()

        # Handle "back" or "cancel"
        if block_input in ['b', 'back']:
            return False
        if block_input in ['c', 'cancel', 'main', 'main menu']:
            return True  # Signal to cancel the whole process

        # Handle shuffle option
        if block_input in ['s', 'shuffle']:
            if handle_shuffle_blocks(selected_playlist_blocks):
                return True  # Signal to cancel the whole process
            else:
                return False  # Go back to the main menu of the new playlist creation process

        # Validate block number for reordering
        try:
            block_index = int(block_input) - 1  # Convert to 0-based index
            if 0 <= block_index < len(selected_playlist_blocks):
                break  # Valid block number, proceed to reordering
            else:
                print(f"ValueError. Expected a single integer value from 1 to {len(selected_playlist_blocks)}.")
        except ValueError:
            print(f"ValueError. Expected a single integer value from 1 to {len(selected_playlist_blocks)}.")

    # Prompt for the new position
    while True:
        new_position_input = input(
            f"Enter a new block number for block {block_index + 1}: "
        ).strip().lower()

        # Handle "back" or "cancel"
        if new_position_input in ['b', 'back']:
            return False
        if new_position_input in ['c', 'cancel', 'main', 'main menu']:
            return True  # Signal to cancel the whole process

        # Validate new position
        try:
            new_position = int(new_position_input) - 1  # Convert to 0-based index
            if 0 <= new_position < len(selected_playlist_blocks):
                if new_position == block_index:
                    print("The number entered is the same as the selected block. Enter a different one.")
                    continue
                break  # Valid new position, proceed to reordering
            else:
                print(f"ValueError. Expected a single integer value from 1 to {len(selected_playlist_blocks)}.")
        except ValueError:
            print(f"ValueError. Expected a single integer value from 1 to {len(selected_playlist_blocks)}.")

    # Handle reordering
    if abs(new_position - block_index) == 1:
        # Swap adjacent blocks
        selected_playlist_blocks[block_index], selected_playlist_blocks[new_position] = (
            selected_playlist_blocks[new_position], selected_playlist_blocks[block_index]
        )
        print("Done!")
    else:
        # Prompt for swap or push using menu_navigation
        options = {
            "1": "Swap those two blocks",
            "2": "Push needed blocks",
            "b": "Back",
            "c": "Cancel",
        }
        option_input = menu_navigation(options, prompt=Prompt.SELECT.value)

        # Handle "back" or "cancel"
        if option_input in ['b', 'back']:
            return False
        if option_input in ['c', 'cancel', 'main', 'main menu']:
            return True  # Signal to cancel the whole process

        # Validate option
        if option_input == "1":
            # Swap the two blocks
            selected_playlist_blocks[block_index], selected_playlist_blocks[new_position] = (
                selected_playlist_blocks[new_position], selected_playlist_blocks[block_index]
            )
            print("Done!")
        elif option_input == "2":
            # Push blocks
            block_to_move = selected_playlist_blocks.pop(block_index)
            selected_playlist_blocks.insert(new_position, block_to_move)
            print("Done!")

    return False  # Signal that reordering was successful

def handle_edit_blocks(selected_playlist_blocks, playlists):
    """
    Handle the editing of selected playlist blocks.
    
    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlists (List[Dict]): List of all playlists
    """
    while True:
        # Display current selection
        display_selected_blocks(selected_playlist_blocks, playlists)
        
        # Prompt for block number
        print()
        block_input = input("Select a block number: ").strip()
        if block_input.lower() in ['b', 'back']:
            break  # Exit the editing loop
        
        try:
            block_index = int(block_input) - 1  # Convert to 0-based index
            if 0 <= block_index < len(selected_playlist_blocks):
                block = selected_playlist_blocks[block_index]
                playlist_id = block["playlist"]["id"]
                
                # Calculate available time for this block
                temp_blocks = selected_playlist_blocks.copy()
                temp_blocks.pop(block_index)
                available_seconds = calculate_available_time(playlist_id, temp_blocks, playlists)
                
                # Loop for time input
                while True:
                    time_prompt = f"Select a time in the format HH:MM up to {format_duration_hhmm(available_seconds)}: "
                    time_str = input(time_prompt).strip()
                    
                    # Check if the user wants to go back
                    if time_str.lower() in ['b', 'back']:
                        break  # Exit the time input loop and go back to block selection
                    
                    # Validate time format
                    if not validate_time_format(time_str):
                        print(Message.INVALID_INPUT_TIME.value)
                        continue  # Restart the loop
                    
                    # Parse time
                    try:
                        parts = time_str.split(':')
                        if len(parts) == 2:
                            hours, minutes = map(int, parts)
                            new_duration_seconds = (hours * 3600) + (minutes * 60)
                            
                            # Validate time amount
                            if new_duration_seconds <= available_seconds:
                                # Update the block duration
                                selected_playlist_blocks[block_index]["duration_seconds"] = new_duration_seconds
                                print("Done!")
                                break  # Exit the time input loop
                            else:
                                print(f"Invalid time. It must be less than or equal to {format_duration_hhmm(available_seconds)}.")
                        else:
                            print(Message.INVALID_INPUT_TIME.value)
                    except ValueError:
                        print("Invalid time format. Please enter numbers for hours and minutes.")
            else:
                print(f"Invalid block number: {block_input}")
        except ValueError:
            print("Invalid input. Please enter a valid block number.")
        
        # Prompt for next action
        edit_menu = {
            "1": "Edit a block",
            "b": "Go back",
        }
        edit_choice = menu_navigation(edit_menu, prompt=Prompt.SELECT.value)
        
        if edit_choice == "b":
            break  # Exit the editing loop

def get_songs_from_playlist(sp, playlist_id: str) -> Tuple[List[Dict[str, str]], int]:
    """
    Fetch all songs from a playlist.
    
    Parameters:
    sp: Spotify client
    playlist_id (str): Spotify playlist ID
    
    Returns:
    Tuple[List[Dict[str, str]], int]: List of songs and total duration in milliseconds
    """
    song_list = []
    track_offset = 0
    
    # Fetch all tracks from the playlist
    while True:
        try:
            tracks_response = sp.playlist_items(
                playlist_id,
                offset=track_offset,
                fields="items.track.uri,items.track.duration_ms,items.track.name,next",
                additional_types=["track"],
            )
            if "items" in tracks_response:
                for track in tracks_response["items"]:
                    if track.get("track"):  # Check if track exists
                        song_list.append(
                            {
                                "uri": track["track"].get("uri"),
                                "name": track["track"].get("name"),
                                "duration_ms": track["track"].get("duration_ms", 0),
                            }
                        )
        except Exception as e:
            logger.error(f"Error fetching playlist items: {e}")
            break

        if not tracks_response.get("next"):
            break
        track_offset += 100

    # Return all songs and their total duration
    return song_list, sum(song["duration_ms"] for song in song_list)

def get_unique_songs_from_blocks(selected_playlist_blocks, sp):
    """
    Collect unique songs from the selected playlist blocks, respecting the specified duration for each block.
    
    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    sp: Spotify client
    
    Returns:
    Tuple[List[Dict], int]: List of unique songs and total duration in milliseconds
    """
    used_track_uris = set()  # Track URIs that have already been used
    all_selected_songs = []  # List of all selected songs
    total_duration = 0  # Total duration of the selected songs

    # Process each block
    for block in selected_playlist_blocks:
        playlist = block["playlist"]
        duration_seconds = block.get("duration_seconds")
        
        # Fetch all songs from the playlist
        playlist_songs, _ = get_songs_from_playlist(sp, playlist["spotify_id"])
        
        # Filter out already used tracks
        unique_songs = [song for song in playlist_songs 
                       if song["uri"] not in used_track_uris]
        
        # If a duration is specified, limit the number of songs
        if duration_seconds is not None:
            duration_ms = duration_seconds * 1000  # Convert seconds to milliseconds
            selected_songs = []
            current_duration = 0
            
            # Randomly shuffle the unique songs to ensure randomness
            random.shuffle(unique_songs)
            
            # Add songs until the duration limit is reached
            for song in unique_songs:
                if current_duration + song["duration_ms"] <= duration_ms:
                    selected_songs.append(song)
                    current_duration += song["duration_ms"]
                else:
                    break
        else:
            # If no duration is specified, use all unique songs
            selected_songs = unique_songs
        
        # Add these track URIs to the used set
        used_track_uris.update([song["uri"] for song in selected_songs])
        all_selected_songs.extend(selected_songs)
        total_duration += sum(song["duration_ms"] for song in selected_songs)
    
    return all_selected_songs, total_duration

def create_playlist_on_spotify(sp, selected_playlist_blocks, playlist_name, privacy, playlists):
    """
    Create the playlist on Spotify with the selected configuration.
    
    Parameters:
    sp: Spotify client
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlist_name (str): Playlist name
    privacy (str): Privacy setting
    playlists (List[Dict]): List of all playlists
    """
    try:
        # Get all unique songs from the selected blocks
        all_selected_songs, total_duration = get_unique_songs_from_blocks(selected_playlist_blocks, sp)
        
        if not all_selected_songs:
            print("No songs selected. Playlist creation canceled.")
            return
        
        # Create the playlist
        new_playlist = sp.user_playlist_create(
            sp.current_user()["id"],
            playlist_name[:40],  # Truncate name if too long
            public=(privacy == "public"),
        )
        
        # Add tracks in batches of 100 (Spotify API limit)
        track_uris = [song["uri"] for song in all_selected_songs]
        for i in range(0, len(track_uris), 100):
            sp.playlist_add_items(new_playlist["id"], track_uris[i:i + 100])

        # Add the new playlist to the list
        new_id = max([p.get("id", 0) for p in playlists], default=0) + 1
        playlists.append({
            "id": new_id,
            "spotify_id": new_playlist["id"],
            "user": sp.current_user()["display_name"],
            "name": playlist_name[:40],
            "track_count": len(all_selected_songs),
            "duration_ms": total_duration,
            "duration": format_duration(total_duration),
        })

        # Save the updated playlists to file
        from playlistarchitect.operations.retrieve_playlists_table import save_playlists_to_file
        save_playlists_to_file(playlists)
        
        # Convert total_duration from milliseconds to seconds
        total_duration_seconds = total_duration // 1000
        # Format the duration as HH:MM:SS
        hours, remainder = divmod(total_duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours:02}:{minutes:02}:{seconds:02}"

        print(f"\nSuccess! Created playlist '{playlist_name}' with {len(all_selected_songs)} tracks and {duration_str} of playback time.")
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        print(f"Error creating playlist: {e}")