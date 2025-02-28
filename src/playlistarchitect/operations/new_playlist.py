import random
import logging
from playlistarchitect.auth.spotify_auth import get_spotify_client, initialize_spotify_client
from playlistarchitect.operations.retrieve_playlists_table import (
    display_playlists_table,
    save_playlists_to_file,
    show_selected_playlists,
)
from playlistarchitect.utils.helpers import menu_navigation, parse_time_input, get_variation_input
from playlistarchitect.utils.formatting_helpers import format_duration
from typing import List, Dict, Optional, Tuple
from tabulate import tabulate

logger = logging.getLogger(__name__)

# Add this new function to format durations as HH:MM
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
    sp,  # Add sp as an argument
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

def create_new_playlist(playlists: List[Dict[str, str]]) -> None:
    """Handle the creation of a new playlist with advanced options."""
    # Ensure Spotify client is initialized before calling the client
    initialize_spotify_client()
    sp = get_spotify_client()

    all_selected_songs = []
    shuffle_option = "No shuffle"
    time_option = "Not specified"
    selected_playlists = []
    selected_ids = set()

    # Get playlist details
    playlist_name = input("Enter a name for the new playlist: ").strip()

    # Privacy menu
    privacy_menu = {
        "1": "Public",
        "2": "Private",
    }
    privacy_choice = menu_navigation(privacy_menu, prompt="Choose privacy:")
    privacy = "public" if privacy_choice == "1" else "private"

    # Display and select playlists
    display_playlists_table(playlists, "Showing saved/created playlists from cache")

    while True:
        selected_input = input("Select playlist IDs (comma-separated) in the format 'ID-hh:mm' or 'ID': ").strip()
        selected_playlists_with_time = parse_playlist_selection(selected_input)
        
        if selected_playlists_with_time:
            selected_playlists = []
            for playlist_id, duration_seconds in selected_playlists_with_time:
                playlist = next((p for p in playlists if p["id"] == playlist_id), None)
                if playlist:
                    playlist["selected_duration_seconds"] = duration_seconds
                    selected_playlists.append(playlist)
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
            # Display selected playlists with their selected times - FIXED
            table_data = []
            for playlist in selected_playlists:
                duration_seconds = playlist.get("selected_duration_seconds")
                if duration_seconds is None:
                    # Use the full playlist duration (already in seconds)
                    duration_str = format_duration_hhmm(playlist.get("duration_ms", 0) // 1000)
                else:
                    # Use the selected duration (already in seconds)
                    duration_str = format_duration_hhmm(duration_seconds)
                table_data.append([
                    playlist["id"],
                    playlist["user"],
                    playlist["name"],
                    duration_str
                ])
            print(tabulate(table_data, headers=["ID", "User", "Name", "Selected Time"], tablefmt="simple"))

        elif main_choice == "2":
            display_playlists_table(playlists, "Showing saved/created playlists from cache", selected_ids={p["id"] for p in selected_playlists}, show_selection_column=True)
            try:
                new_ids = [int(x.strip()) for x in input("Enter playlist IDs to add (comma-separated): ").strip().split(",")]

                # Get sets of existing and already selected playlist IDs
                existing_ids = {p["id"] for p in playlists}
                already_selected = {p["id"] for p in selected_playlists}

                # Identify invalid and duplicate IDs
                invalid_ids = [id_ for id_ in new_ids if id_ not in existing_ids]
                duplicate_ids = [id_ for id_ in new_ids if id_ in already_selected]

                # Display messages for issues
                if invalid_ids:
                    print(f"⚠️ Invalid ID(s): {', '.join(map(str, invalid_ids))} (These do not exist).")

                if duplicate_ids:
                    print(f"🔄 Already selected ID(s): {', '.join(map(str, duplicate_ids))} (These are already in your selection).")

                # Add only valid and non-duplicate playlists
                valid_new_playlists = [p for p in playlists if p["id"] in new_ids and p["id"] not in already_selected]
                selected_playlists.extend(valid_new_playlists)

            except ValueError:
                print("❌ Invalid input. Please enter numeric playlist IDs.")

        elif main_choice == "3":
            if selected_playlists:
                print("\nCurrently selected playlists:")
                # FIXED: Also update the display format here
                table_data = []
                for playlist in selected_playlists:
                    duration_seconds = playlist.get("selected_duration_seconds")
                    if duration_seconds is None:
                        # Use the full playlist duration (already in seconds)
                        duration_str = format_duration_hhmm(playlist.get("duration_ms", 0) // 1000)
                    else:
                        # Use the selected duration (already in seconds)
                        duration_str = format_duration_hhmm(duration_seconds)
                    table_data.append([
                        playlist["id"],
                        playlist["user"],
                        playlist["name"],
                        duration_str
                    ])
                print(tabulate(table_data, headers=["ID", "User", "Name", "Selected Time"], tablefmt="simple"))
                try:
                    remove_ids = [int(x.strip()) for x in input("Enter playlist IDs to remove (comma-separated): ").strip().split(",")]
                    selected_playlists = [p for p in selected_playlists if p["id"] not in remove_ids]
                except ValueError:
                    print("Invalid input. Please enter numeric playlist IDs.")
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
                    print(f"Number of source playlists: {len(selected_playlists)}")
                    print(f"Shuffle option: {shuffle_option}")
                    print(f"Time option: {time_option}")

                    if input("\nCreate playlist? (y/n): ").lower() == "y":
                        all_selected_songs = []
                        total_duration = 0
                        
                        logger.debug(f"Playlists before creation: {playlists}")
                        
                        for playlist in selected_playlists:
                            # FIXED: Pass the selected_duration_seconds correctly
                            playlist_songs, duration = get_songs_from_playlist(
                                sp,  # Pass sp as the first argument
                                playlist["spotify_id"],
                                playlist.get("selected_duration_seconds"),  # This now contains seconds
                                variation_ms,
                            )
                            all_selected_songs.extend(playlist_songs)
                            total_duration += duration

                        if shuffle_option == "Shuffle tracks":
                            random.shuffle(all_selected_songs)
                        elif shuffle_option == "Shuffle playlists":
                            random.shuffle(selected_playlists)
                            # FIXED: Make sure to pass sp when getting songs from playlist
                            for playlist in selected_playlists:
                                playlist_songs, _ = get_songs_from_playlist(
                                    sp,
                                    playlist["spotify_id"]
                                )
                                all_selected_songs.extend(playlist_songs)
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