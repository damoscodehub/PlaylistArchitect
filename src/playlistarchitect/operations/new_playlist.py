import random
import logging
from playlistarchitect.auth.spotify_auth import get_spotify_client, initialize_spotify_client
from playlistarchitect.operations.retrieve_playlists_table import (
    display_playlists_table,
    save_playlists_to_file,
)
from playlistarchitect.utils.helpers import menu_navigation, parse_time_input, get_variation_input
from playlistarchitect.utils.formatting_helpers import format_duration
from typing import List, Dict, Optional, Tuple, Any
from tabulate import tabulate

logger = logging.getLogger(__name__)

# Format durations as HH:MM
def format_duration_hhmm(seconds):
    """Format seconds to hh:mm format without seconds"""
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}"

def parse_playlist_selection(input_str):
    """
    Parse the input string in the format 'ID-hh:mm' or 'ID'.
    Returns a list of tuples (playlist_id, duration_seconds).
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
                selected_playlists.append((playlist_id, None))  # None means full playlist
            except ValueError:
                print(f"Invalid playlist ID '{item}'. Skipping.")
    return selected_playlists


def get_songs_from_playlist(
    sp,
    playlist_id: str, 
    total_duration_seconds: Optional[int] = None, 
    acceptable_deviation_ms: Optional[int] = None
) -> Tuple[List[Dict[str, str]], int]:
    """Fetch songs from a playlist, optionally limiting by duration."""
    song_list = []
    track_offset = 0
    
    # Convert total_duration_seconds to milliseconds if provided
    total_duration_ms = None
    if total_duration_seconds is not None:
        total_duration_ms = total_duration_seconds * 1000  # Convert seconds to milliseconds

    while True:
        try:
            tracks_response = sp.playlist_items(
                playlist_id,
                offset=track_offset,
                fields="items.track.uri,items.track.duration_ms,items.track.name",
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

def display_selected_playlists(selected_playlist_blocks, playlists):
    """
    Display selected playlists with their selected times, used time, and available time.
    """
    table_data = []
    
    # Group by playlist ID to calculate total used time
    usage_by_id = {}
    for block in selected_playlist_blocks:
        playlist_id = block["playlist"]["id"]
        duration_seconds = block.get("duration_seconds", 0) or 0
        
        if playlist_id not in usage_by_id:
            usage_by_id[playlist_id] = {
                "blocks": 0,
                "used_seconds": 0,
                "playlist": block["playlist"]
            }
        
        usage_by_id[playlist_id]["blocks"] += 1
        usage_by_id[playlist_id]["used_seconds"] += duration_seconds
    
    # Create table data with usage info
    for playlist_id, usage in usage_by_id.items():
        playlist = usage["playlist"]
        total_seconds = playlist.get("duration_ms", 0) // 1000
        used_seconds = usage["used_seconds"]
        
        # If duration_seconds is None for any block, consider the full playlist as used
        if any(block.get("duration_seconds") is None for block in selected_playlist_blocks 
               if block["playlist"]["id"] == playlist_id):
            used_seconds = total_seconds
        
        available_seconds = max(0, total_seconds - used_seconds)
        
        table_data.append([
            playlist["id"],
            playlist["user"],
            playlist["name"],
            usage["blocks"],
            format_duration_hhmm(total_seconds),
            format_duration_hhmm(used_seconds),
            format_duration_hhmm(available_seconds)
        ])
    
    print(tabulate(
        table_data, 
        headers=["ID", "User", "Name", "# Blocks", "Total", "Used", "Available"], 
        tablefmt="simple"
    ))
    
    # Also show detailed blocks
    print("\nSelected blocks (detailed):")
    blocks_data = []
    for i, block in enumerate(selected_playlist_blocks):
        playlist = block["playlist"]
        duration_seconds = block.get("duration_seconds")
        
        if duration_seconds is None:
            duration_str = "Full playlist"
        else:
            duration_str = format_duration_hhmm(duration_seconds)
            
        blocks_data.append([
            i+1,
            playlist["id"],
            playlist["name"],
            duration_str
        ])
    
    print(tabulate(
        blocks_data,
        headers=["Block #", "ID", "Name", "Selected Time"],
        tablefmt="simple"
    ))

def display_playlist_selection_table(playlists, selected_blocks):
    """
    Display playlist selection table with usage statistics.
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
        
        table_data.append([
            blocks_display,
            playlist["id"],
            playlist["user"],
            playlist["name"],
            playlist["track_count"],
            format_duration_hhmm(total_seconds),
            format_duration_hhmm(used_seconds),
            format_duration_hhmm(available_seconds)
        ])
    
    print(tabulate(
        table_data,
        headers=["# Blocks", "ID", "User", "Name", "Tracks", "Total", "Used", "Available"],
        tablefmt="simple"
    ))
    
    total_playlists = len(playlists)
    total_tracks = sum(p.get("track_count", 0) for p in playlists)
    total_duration_ms = sum(p.get("duration_ms", 0) for p in playlists)
    total_duration_str = format_duration(total_duration_ms)
    
    print(f"{total_playlists} playlists, {total_tracks} tracks, {total_duration_str} playback time.")

def create_new_playlist(playlists: List[Dict[str, Any]]) -> None:
    """Handle the creation of a new playlist with advanced options."""
    # Ensure Spotify client is initialized before calling the client
    initialize_spotify_client()
    sp = get_spotify_client()

    all_selected_songs = []
    shuffle_option = "No shuffle"
    time_option = "Not specified"
    
    # Store selected playlists as blocks (can have the same playlist multiple times)
    selected_playlist_blocks = []

    # Get playlist details
    playlist_name = input("Enter a name for the new playlist: ").strip()

    # Privacy menu
    privacy_menu = {
        "1": "Public",
        "2": "Private",
    }
    privacy_choice = menu_navigation(privacy_menu, prompt="Choose privacy:")
    privacy = "public" if privacy_choice == "1" else "private"

    # Display and select playlists with new format
    display_playlist_selection_table(playlists, selected_playlist_blocks)

    while True:
        selected_input = input("Select playlist IDs (comma-separated) in the format 'ID-hh:mm' or 'ID': ").strip()
        selected_playlists_with_time = parse_playlist_selection(selected_input)
        
        if selected_playlists_with_time:
            for playlist_id, duration_seconds in selected_playlists_with_time:
                playlist = next((p for p in playlists if p["id"] == playlist_id), None)
                if playlist:
                    selected_playlist_blocks.append({
                        "playlist": playlist,
                        "duration_seconds": duration_seconds
                    })
            break
        else:
            print("No valid playlists selected. Please enter at least one valid playlist ID.")

    time_ms = None
    variation_ms = None

    while True:
        # Main menu
        main_menu = {
            "1": "Show selected playlists",
            "2": "Add playlists to selection",
            "3": "Remove playlists from selection",
            "4": "Proceed with current selection",
            "b": "Back",
            "c": "Cancel",
        }
        main_choice = menu_navigation(main_menu, prompt="Select an option:")

        if main_choice == "1":
            # Display selected playlists with their selected times
            display_selected_playlists(selected_playlist_blocks, playlists)

        elif main_choice == "2":
            # Display available playlists with usage info
            display_playlist_selection_table(playlists, selected_playlist_blocks)
            
            # Use the same input format as initial selection
            selected_input = input("Select playlist IDs (comma-separated) in the format 'ID-hh:mm' or 'ID': ").strip()
            selected_playlists_with_time = parse_playlist_selection(selected_input)
            
            if selected_playlists_with_time:
                for playlist_id, duration_seconds in selected_playlists_with_time:
                    playlist = next((p for p in playlists if p["id"] == playlist_id), None)
                    if playlist:
                        selected_playlist_blocks.append({
                            "playlist": playlist,
                            "duration_seconds": duration_seconds
                        })
            else:
                print("No valid playlists selected.")

        elif main_choice == "3":
            if selected_playlist_blocks:
                # Display blocks with index numbers
                display_selected_playlists(selected_playlist_blocks, playlists)
                
                try:
                    remove_blocks = input("Enter block numbers to remove (comma-separated): ").strip()
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
            else:
                print("No playlists to remove.")

        elif main_choice == "4":
            while True:
                # Submenu for proceeding
                proceed_menu = {
                    "1": "Shuffle options",
                    "2": "Time options",
                    "3": "Create playlist",
                    "b": "Back",
                    "c": "Cancel",
                }
                proceed_choice = menu_navigation(proceed_menu, prompt="Select an option:")

                if proceed_choice == "1":
                    shuffle_menu = {
                        "1": "Shuffle the order of selected playlists",
                        "2": "Shuffle all tracks",
                        "3": "No shuffle",
                    }
                    shuffle_choice = menu_navigation(shuffle_menu, prompt="Select shuffle option:")
                    shuffle_option = {
                        "1": "Shuffle playlists",
                        "2": "Shuffle tracks",
                        "3": "No shuffle",
                    }[shuffle_choice]

                elif proceed_choice == "2":
                    time_menu = {
                        "1": "Set time for each playlist (the same for all playlists)",
                        "2": "Set total time (equally divided between all playlists)",
                        "3": "Not specified (use full playlists)",
                    }
                    time_choice = menu_navigation(time_menu, prompt="Select time option:")

                    if time_choice in ["1", "2"]:
                        time_str = input("Insert a time (hh:mm:ss): ").strip()
                        time_ms = parse_time_input(time_str)
                        if time_ms is None:
                            continue

                        variation_str = input("Set the acceptable +- variation in minutes (e.g. 2): ").strip()
                        variation_ms = get_variation_input(variation_str)
                        if variation_ms is None:
                            continue

                        time_option = (f"Each playlist: {time_str} ± {variation_str} minutes"
                                       if time_choice == "1"
                                       else f"Total time: {time_str} ± {variation_str} minutes")
                    elif time_choice == "3":
                        time_ms = None
                        variation_ms = None
                        time_option = "Not specified"

                elif proceed_choice == "3":
                    print(f"\nPlaylist Configuration:")
                    print(f"Name: {playlist_name}")
                    print(f"Privacy: {privacy}")
                    print(f"Number of source playlist blocks: {len(selected_playlist_blocks)}")
                    print(f"Shuffle option: {shuffle_option}")
                    print(f"Time option: {time_option}")

                    if input("\nCreate playlist? (y/n): ").lower() == "y":
                        all_selected_songs = []
                        total_duration = 0
                        
                        logger.debug(f"Playlists before creation: {playlists}")
                        
                        for block in selected_playlist_blocks:
                            playlist = block["playlist"]
                            duration_seconds = block.get("duration_seconds")
                            
                            playlist_songs, duration = get_songs_from_playlist(
                                sp,
                                playlist["spotify_id"],
                                duration_seconds,
                                variation_ms,
                            )
                            all_selected_songs.extend(playlist_songs)
                            total_duration += duration

                        if shuffle_option == "Shuffle tracks":
                            random.shuffle(all_selected_songs)
                        elif shuffle_option == "Shuffle playlists":
                            random.shuffle(selected_playlist_blocks)
                            all_selected_songs = []
                            total_duration = 0
                            
                            for block in selected_playlist_blocks:
                                playlist = block["playlist"]
                                duration_seconds = block.get("duration_seconds")
                                
                                playlist_songs, duration = get_songs_from_playlist(
                                    sp,
                                    playlist["spotify_id"],
                                    duration_seconds,
                                    variation_ms,
                                )
                                all_selected_songs.extend(playlist_songs)
                                total_duration += duration
                                
                        try:
                            new_playlist = sp.user_playlist_create(
                                sp.current_user()["id"],
                                playlist_name[:40],  # Truncate name if too long
                                public=(privacy == "public"),
                            )
                            track_uris = [song["uri"] for song in all_selected_songs]
                            for i in range(0, len(track_uris), 100):
                                sp.playlist_add_items(new_playlist["id"], track_uris[i:i + 100])

                            # Assign a new ID to the playlist
                            new_id = max([p.get("id", 0) for p in playlists], default=0) + 1  # Get the next available ID
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
                            
                            logger.debug(f"Playlists after creation: {playlists}")
                            
                            print(f"\nSuccess! Created playlist '{playlist_name}' with {len(all_selected_songs)} songs.")
                            return
                        except Exception as e:
                            logger.error(f"Error creating playlist: {e}")
                            return

                elif proceed_choice in ["b", "c"]:
                    break

        elif main_choice in ["b", "c"]:
            return