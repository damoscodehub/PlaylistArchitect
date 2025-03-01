import random
import logging
from playlistarchitect.auth.spotify_auth import get_spotify_client, initialize_spotify_client
from playlistarchitect.operations.retrieve_playlists_table import (
    display_playlists_table,
    save_playlists_to_file,
)
from playlistarchitect.utils.helpers import menu_navigation, parse_time_input, get_variation_input
from playlistarchitect.utils.formatting_helpers import format_duration
from typing import List, Dict, Optional, Tuple, Any, Callable
from tabulate import tabulate

logger = logging.getLogger(__name__)

SELECT_IDS = "Set the comma-separated track blocks in the format 'ID' (to use all the available time) or 'ID-HH:MM' (to use a custom time). 'b' to go back.\n> "

def format_duration_hhmm(seconds):
    """Format seconds to hh:mm format without seconds"""
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}"

def safe_input(prompt, validator=None, error_msg="Invalid input"):
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

def parse_playlist_selection(input_str):
    """
    Parse the input string in the format 'ID-hh:mm' or 'ID'.
    Returns a list of tuples (playlist_id, duration_seconds).
    For plain IDs, duration_seconds will be None, indicating to use available time.
    
    Parameters:
    input_str (str): Comma-separated string of playlist IDs with optional durations
    
    Returns:
    List[Tuple[int, Optional[int]]]: List of (playlist_id, duration_seconds) tuples
    """
    selected_playlists = []
    for item in input_str.split(','):
        item = item.strip()
        if '-' in item:
            playlist_id, time_str = item.split('-')
            try:
                playlist_id = int(playlist_id.strip())
                if ':' in time_str:
                    # Check if time_str contains hours and minutes
                    parts = time_str.strip().split(':')
                    if len(parts) == 2:
                        hours, minutes = map(int, parts)
                        duration_seconds = (hours * 3600) + (minutes * 60)  # Convert to seconds
                    else:
                        print(f"Invalid time format for '{item}'. Expected hh:mm. Skipping.")
                        continue
                else:
                    print(f"Invalid time format for '{item}'. Expected hh:mm. Skipping.")
                    continue
                selected_playlists.append((playlist_id, duration_seconds))
            except ValueError:
                print(f"Invalid format for '{item}'. Skipping.")
        else:
            try:
                playlist_id = int(item.strip())
                # When just ID is provided, return None to indicate "use available time"
                selected_playlists.append((playlist_id, None))
            except ValueError:
                print(f"Invalid playlist ID '{item}'. Skipping.")
    return selected_playlists

def get_songs_from_playlist(
    sp,
    playlist_id: str, 
    total_duration_seconds: Optional[int] = None, 
    acceptable_deviation_ms: Optional[int] = None
) -> Tuple[List[Dict[str, str]], int]:
    """
    Fetch songs from a playlist, optionally limiting by duration.
    
    Parameters:
    sp: Spotify client
    playlist_id (str): Spotify playlist ID
    total_duration_seconds (Optional[int]): Duration limit in seconds
    acceptable_deviation_ms (Optional[int]): Acceptable deviation in milliseconds
    
    Returns:
    Tuple[List[Dict[str, str]], int]: List of songs and total duration in milliseconds
    """
    song_list = []
    track_offset = 0
    
    # Convert total_duration_seconds to milliseconds if provided
    total_duration_ms = None
    if total_duration_seconds is not None:
        total_duration_ms = total_duration_seconds * 1000  # Convert seconds to milliseconds

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

    # If no duration limit, return all songs
    if total_duration_ms is None:
        return song_list, sum(song["duration_ms"] for song in song_list)

    # Randomly pick songs until total duration is close to target
    selected_songs = []
    current_duration = 0
    available_songs = song_list.copy()

    while available_songs and current_duration < total_duration_ms - (acceptable_deviation_ms or 0):
        song = random.choice(available_songs)
        if current_duration + song["duration_ms"] <= total_duration_ms + (acceptable_deviation_ms or 0):
            selected_songs.append(song)
            current_duration += song["duration_ms"]
        available_songs.remove(song)

    return selected_songs, current_duration

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
    selected_playlists_with_time = parse_playlist_selection(selected_input)
    
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
                        print("Invalid time format. Expected HH:MM.")
                else:
                    print("Invalid time format. Expected HH:MM.")
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

def apply_shuffle_strategy(selected_playlist_blocks, shuffle_option, sp, variation_ms):
    """
    Applies the selected shuffle strategy and returns the songs list
    
    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    shuffle_option (str): Shuffle strategy to apply
    sp: Spotify client
    variation_ms (Optional[int]): Acceptable time variation in milliseconds
    
    Returns:
    Tuple[List[Dict], int]: Selected songs and total duration in milliseconds
    """
    used_track_uris = set()
    all_selected_songs = []
    
    # If shuffling playlists, do it before processing
    blocks_to_process = selected_playlist_blocks.copy()
    if shuffle_option == "Shuffle playlists":
        random.shuffle(blocks_to_process)
    
    # Process each block
    for block in blocks_to_process:
        playlist = block["playlist"]
        duration_seconds = block.get("duration_seconds")
        
        playlist_songs, _ = get_songs_from_playlist(
            sp,
            playlist["spotify_id"],
            duration_seconds,
            variation_ms,
        )
        
        # Filter out already used tracks
        unique_songs = [song for song in playlist_songs 
                       if song["uri"] not in used_track_uris]
        
        # Add these track URIs to the used set
        used_track_uris.update([song["uri"] for song in unique_songs])
        all_selected_songs.extend(unique_songs)
    
    # Apply track-level shuffling if needed
    if shuffle_option == "Shuffle tracks":
        random.shuffle(all_selected_songs)
    
    total_duration = sum(song["duration_ms"] for song in all_selected_songs)
    return all_selected_songs, total_duration

def handle_add_playlists(playlists, selected_playlist_blocks):
    """
    Handle the adding of playlists to selection
    
    Parameters:
    playlists (List[Dict]): List of all playlists
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    """
    display_playlist_selection_table(playlists, selected_playlist_blocks)
    
    selected_input = input(SELECT_IDS).strip()
    if selected_input.lower() in ['b', 'back']:
        return
        
    new_block_indices = process_playlist_selection(selected_input, playlists, selected_playlist_blocks)
    
    if new_block_indices:
        validate_playlist_blocks(selected_playlist_blocks, playlists, new_block_indices)

def handle_remove_playlists(selected_playlist_blocks, playlists):
    """
    Handle the removal of playlists from selection
    
    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlists (List[Dict]): List of all playlists
    """
    if not selected_playlist_blocks:
        print("No playlists to remove.")
        return
        
    display_selected_blocks(selected_playlist_blocks, playlists)
    
    try:
        remove_blocks = input("Enter block numbers to remove (comma-separated): ").strip()
        if not remove_blocks:
            return
            
        remove_indices = [int(x.strip()) - 1 for x in remove_blocks.split(",") if x.strip()]
        
        # Sort indices in descending order to avoid index shifting during removal
        remove_indices.sort(reverse=True)
        
        for idx in remove_indices:
            if 0 <= idx < len(selected_playlist_blocks):
                del selected_playlist_blocks[idx]
            else:
                print(f"Invalid block number: {idx+1}")
        
    except ValueError:
        print("Invalid input. Please enter numeric block numbers.")

def handle_shuffle_options():
    """
    Handle shuffle options selection
    
    Returns:
    str: Selected shuffle option
    """
    shuffle_menu = {
        "1": "Shuffle the order of selected playlists",
        "2": "Shuffle all tracks",
        "3": "No shuffle",
    }
    shuffle_choice = menu_navigation(shuffle_menu, prompt="Select shuffle option:")
    return {
        "1": "Shuffle playlists",
        "2": "Shuffle tracks",
        "3": "No shuffle",
    }[shuffle_choice]

def handle_time_options():
    """
    Handle time options selection
    
    Returns:
    Tuple[str, Optional[int], Optional[int]]: Time option description, time in milliseconds, 
                                            and acceptable variation in milliseconds
    """
    time_menu = {
        "1": "Set time for each playlist (the same for all playlists)",
        "2": "Set total time (equally divided between all playlists)",
        "3": "Not specified (use full playlists)",
    }
    time_choice = menu_navigation(time_menu, prompt="Select time option:")
    
    time_ms = None
    variation_ms = None
    time_option = "Not specified"
    
    if time_choice in ["1", "2"]:
        time_str = safe_input(
            "Insert a time (hh:mm:ss): ", 
            validator=validate_time_format,
            error_msg="Invalid time format. Please use HH:MM or HH:MM:SS format."
        )
        if time_str.lower() in ['b', 'back', 'c', 'cancel']:
            return time_option, time_ms, variation_ms
            
        time_ms = parse_time_input(time_str)
        if time_ms is None:
            return time_option, time_ms, variation_ms
        
        variation_str = safe_input(
            "Set the acceptable +- variation in minutes (e.g. 2): ",
            validator=lambda x: x.isdigit() or x == "",
            error_msg="Please enter a valid number of minutes."
        )
        if variation_str.lower() in ['b', 'back', 'c', 'cancel']:
            return time_option, time_ms, variation_ms
            
        variation_ms = get_variation_input(variation_str)
        if variation_ms is None:
            return time_option, time_ms, variation_ms
        
        time_option = (f"Each playlist: {time_str} ± {variation_str} minutes"
                      if time_choice == "1"
                      else f"Total time: {time_str} ± {variation_str} minutes")
                      
    return time_option, time_ms, variation_ms

def display_playlist_summary(playlist_name, privacy, block_count, shuffle_option, time_option):
    """
    Display a summary of the playlist configuration
    
    Parameters:
    playlist_name (str): Playlist name
    privacy (str): Privacy setting
    block_count (int): Number of playlist blocks
    shuffle_option (str): Selected shuffle option
    time_option (str): Selected time option
    """
    print(f"\nPlaylist Configuration:")
    print(f"Name: {playlist_name}")
    print(f"Privacy: {privacy}")
    print(f"Number of source playlist blocks: {block_count}")
    print(f"Shuffle option: {shuffle_option}")
    print(f"Time option: {time_option}")

def create_playlist_on_spotify(
    sp, 
    selected_playlist_blocks, 
    playlist_name, 
    privacy, 
    shuffle_option, 
    time_ms, 
    variation_ms,
    playlists
):
    """
    Create the playlist on Spotify with the selected configuration
    
    Parameters:
    sp: Spotify client
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlist_name (str): Playlist name
    privacy (str): Privacy setting
    shuffle_option (str): Selected shuffle option
    time_ms (Optional[int]): Selected time in milliseconds
    variation_ms (Optional[int]): Acceptable time variation in milliseconds
    playlists (List[Dict]): List of all playlists
    """
    try:
        # Get all songs based on the selected shuffle strategy
        all_selected_songs, total_duration = apply_shuffle_strategy(
            selected_playlist_blocks, 
            shuffle_option, 
            sp, 
            variation_ms
        )
        
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
        save_playlists_to_file(playlists)
        
        print(f"\nSuccess! Created playlist '{playlist_name}' with {len(all_selected_songs)} songs.")
        
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        print(f"Error creating playlist: {e}")

def handle_proceed_menu(
    selected_playlist_blocks, 
    playlist_name, 
    privacy, 
    shuffle_option, 
    time_option,
    sp,
    playlists
):
    """
    Handle the proceed menu and playlist creation
    
    Parameters:
    selected_playlist_blocks (List[Dict]): Currently selected playlist blocks
    playlist_name (str): Playlist name
    privacy (str): Privacy setting
    shuffle_option (str): Selected shuffle option
    time_option (str): Selected time option
    sp: Spotify client
    playlists (List[Dict]): List of all playlists
    
    Returns:
    bool: True if canceled or playlist created successfully
    """
    time_ms = None
    variation_ms = None
    
    while True:
        proceed_menu = {
            "1": "Shuffle options",
            "2": "Time options",
            "3": "Create playlist",
            "b": "Back",
            "c": "Cancel",
        }
        proceed_choice = menu_navigation(proceed_menu, prompt="Select an option:")

        if proceed_choice == "1":
            shuffle_option = handle_shuffle_options()

        elif proceed_choice == "2":
            time_option, time_ms, variation_ms = handle_time_options()

        elif proceed_choice == "3":
            display_playlist_summary(
                playlist_name, 
                privacy, 
                len(selected_playlist_blocks), 
                shuffle_option, 
                time_option
            )
            
            if input("\nCreate playlist? (y/n): ").lower() == "y":
                create_playlist_on_spotify(
                    sp, 
                    selected_playlist_blocks, 
                    playlist_name, 
                    privacy, 
                    shuffle_option, 
                    time_ms, 
                    variation_ms,
                    playlists
                )
                return True
                
        elif proceed_choice in ["b", "c"]:
            return proceed_choice == "c"  # Return True if canceled

def create_new_playlist(playlists: List[Dict[str, Any]]) -> None:
    """
    Handle the creation of a new playlist with advanced options.
    
    Parameters:
    playlists (List[Dict]): List of all playlists
    """
    # Ensure Spotify client is initialized before calling the client
    initialize_spotify_client()
    sp = get_spotify_client()

    # Initialize variables
    selected_playlist_blocks = []
    shuffle_option = "No shuffle"
    time_option = "Not specified"
    time_ms = None
    variation_ms = None

    # Get basic playlist details
    playlist_name = input("Enter a name for the new playlist: ").strip()
    if not playlist_name:
        print("Playlist name cannot be empty.")
        return

    # Privacy menu
    privacy_menu = {"1": "Public", "2": "Private"}
    privacy_choice = menu_navigation(privacy_menu, prompt="Choose privacy:")
    privacy = "public" if privacy_choice == "1" else "private"

    # Initial playlist selection
    initial_selection_completed = False
    while not initial_selection_completed:
        display_playlist_selection_table(playlists, selected_playlist_blocks)
        
        selected_input = input(SELECT_IDS).strip()
        if selected_input.lower() in ['b', 'back', 'c', 'cancel']:
            return
            
        new_block_indices = process_playlist_selection(selected_input, playlists, selected_playlist_blocks)
        
        if new_block_indices:
            validate_playlist_blocks(selected_playlist_blocks, playlists, new_block_indices)
            initial_selection_completed = True
        else:
            print("No valid playlists selected. Please enter at least one valid playlist ID.")

    # Main menu loop
    while True:
        main_menu = {
            "1": "Show selected blocks", 
            "2": "Add playlists to selection",
            "3": "Remove playlists from selection",
            "4": "Proceed with current selection",
            "b": "Back",
            "c": "Cancel",
        }
        main_choice = menu_navigation(main_menu, prompt="Select an option:")

        if main_choice == "1":
            display_selected_blocks(selected_playlist_blocks, playlists)

        elif main_choice == "2":
            handle_add_playlists(playlists, selected_playlist_blocks)

        elif main_choice == "3":
            handle_remove_playlists(selected_playlist_blocks, playlists)

        elif main_choice == "4":
            if handle_proceed_menu(
                selected_playlist_blocks, 
                playlist_name, 
                privacy, 
                shuffle_option, 
                time_option,
                sp,
                playlists
            ):
                return  # Playlist creation was successful or user canceled

        elif main_choice in ["b", "c"]:
            return

def handle_add_playlists(playlists, selected_playlist_blocks):
    """Handle the adding of playlists to selection"""
    display_playlist_selection_table(playlists, selected_playlist_blocks)
    
    selected_input = input(SELECT_IDS).strip()
    if selected_input.lower() in ['b', 'back']:
        return
        
    new_block_indices = process_playlist_selection(selected_input, playlists, selected_playlist_blocks)
    
    if new_block_indices:
        validate_playlist_blocks(selected_playlist_blocks, playlists, new_block_indices)

def handle_remove_playlists(selected_playlist_blocks, playlists):
    """Handle the removal of playlists from selection"""
    if not selected_playlist_blocks:
        print("No playlists to remove.")
        return
        
    display_selected_blocks(selected_playlist_blocks, playlists)
    
    try:
        remove_blocks = input("Enter block numbers to remove (comma-separated): ").strip()
        if not remove_blocks:
            return
            
        remove_indices = [int(x.strip()) - 1 for x in remove_blocks.split(",") if x.strip()]
        
        # Sort indices in descending order to avoid index shifting during removal
        remove_indices.sort(reverse=True)
        
        for idx in remove_indices:
            if 0 <= idx < len(selected_playlist_blocks):
                del selected_playlist_blocks[idx]
            else:
                print(f"Invalid block number: {idx+1}")
        
    except ValueError:
        print("Invalid input. Please enter numeric block numbers.")

def handle_proceed_menu(
    selected_playlist_blocks, 
    playlist_name, 
    privacy, 
    shuffle_option, 
    time_option,
    sp,
    playlists
):
    """Handle the proceed menu and playlist creation"""
    time_ms = None
    variation_ms = None
    
    while True:
        proceed_menu = {
            "1": "Shuffle options",
            "2": "Time options",
            "3": "Create playlist",
            "b": "Back",
            "c": "Cancel",
        }
        proceed_choice = menu_navigation(proceed_menu, prompt="Select an option:")

        if proceed_choice == "1":
            shuffle_option = handle_shuffle_options()

        elif proceed_choice == "2":
            time_option, time_ms, variation_ms = handle_time_options()

        elif proceed_choice == "3":
            display_playlist_summary(playlist_name, privacy, len(selected_playlist_blocks), 
                                    shuffle_option, time_option)
            
            if input("\nCreate playlist? (y/n): ").lower() == "y":
                create_playlist_on_spotify(
                    sp, 
                    selected_playlist_blocks, 
                    playlist_name, 
                    privacy, 
                    shuffle_option, 
                    time_ms, 
                    variation_ms,
                    playlists
                )
                return True
                
        elif proceed_choice in ["b", "c"]:
            return proceed_choice == "c"  # Return True if canceled

def handle_shuffle_options():
    """Handle shuffle options selection"""
    shuffle_menu = {
        "1": "Shuffle the order of selected playlists",
        "2": "Shuffle all tracks",
        "3": "No shuffle",
    }
    shuffle_choice = menu_navigation(shuffle_menu, prompt="Select shuffle option:")
    return {
        "1": "Shuffle playlists",
        "2": "Shuffle tracks",
        "3": "No shuffle",
    }[shuffle_choice]

def handle_time_options():
    """Handle time options selection"""
    time_menu = {
        "1": "Set time for each playlist (the same for all playlists)",
        "2": "Set total time (equally divided between all playlists)",
        "3": "Not specified (use full playlists)",
    }
    time_choice = menu_navigation(time_menu, prompt="Select time option:")
    
    time_ms = None
    variation_ms = None
    time_option = "Not specified"
    
    if time_choice in ["1", "2"]:
        time_str = safe_input(
            "Insert a time (hh:mm:ss): ", 
            validator=validate_time_format,
            error_msg="Invalid time format. Please use HH:MM or HH:MM:SS format."
        )
        if time_str.lower() in ['b', 'back', 'c', 'cancel']:
            return time_option, time_ms, variation_ms
            
        time_ms = parse_time_input(time_str)
        if time_ms is None:
            return time_option, time_ms, variation_ms
        
        variation_str = safe_input(
            "Set the acceptable +- variation in minutes (e.g. 2): ",
            validator=lambda x: x.isdigit() or x == "",
            error_msg="Please enter a valid number of minutes."
        )
        if variation_str.lower() in ['b', 'back', 'c', 'cancel']:
            return time_option, time_ms, variation_ms
            
        variation_ms = get_variation_input(variation_str)
        if variation_ms is None:
            return time_option, time_ms, variation_ms
        
        time_option = (f"Each playlist: {time_str} ± {variation_str} minutes"
                      if time_choice == "1"
                      else f"Total time: {time_str} ± {variation_str} minutes")
                      
    return time_option, time_ms, variation_ms

def display_playlist_summary(playlist_name, privacy, block_count, shuffle_option, time_option):
    """Display a summary of the playlist configuration"""
    print(f"\nPlaylist Configuration:")
    print(f"Name: {playlist_name}")
    print(f"Privacy: {privacy}")
    print(f"Number of source playlist blocks: {block_count}")
    print(f"Shuffle option: {shuffle_option}")
    print(f"Time option: {time_option}")

def create_playlist_on_spotify(
    sp, 
    selected_playlist_blocks, 
    playlist_name, 
    privacy, 
    shuffle_option, 
    time_ms, 
    variation_ms,
    playlists
):
    """Create the playlist on Spotify with the selected configuration"""
    try:
        # Get all songs based on the selected shuffle strategy
        all_selected_songs, total_duration = apply_shuffle_strategy(
            selected_playlist_blocks, 
            shuffle_option, 
            sp, 
            variation_ms
        )
        
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