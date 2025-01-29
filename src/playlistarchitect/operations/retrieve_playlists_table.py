import json
import os
import sys
import logging
import time
import itertools
from typing import List, Dict, Generator, Tuple
from tabulate import tabulate
from playlistarchitect.auth.spotify_auth import get_spotify_client, initialize_spotify_client
from concurrent.futures import ThreadPoolExecutor, as_completed
from playlistarchitect.utils.playlist_helpers import process_single_playlist
from playlistarchitect.utils.formatting_helpers import truncate


# Setup logging
logger = logging.getLogger(__name__)

# Generator for spinner animation
def create_spinner() -> Generator[str, None, None]:
    """Creates a spinner animation generator."""
    while True:
        for char in '|/-\\':
            yield char


def prepare_table_data(playlists, truncate_length=40):
    """Prepare playlist data for tabulation."""
    return [
        [
            playlist["id"],
            truncate(playlist["user"], truncate_length),
            truncate(playlist["name"], truncate_length),
            playlist["duration"],
        ]
        for playlist in playlists
    ]

def process_playlists() -> Generator[Dict, None, None]:
    """
    Process user's playlists using multithreading for improved performance.
    Returns:
        Tuple[int, int, int]: Total playlists, tracks, and duration in seconds
    """
    initialize_spotify_client()
    sp = get_spotify_client()

    if sp is None:
        logger.critical("Spotify client is None in process_playlists()! Cannot continue.")
        raise RuntimeError("Spotify client is not initialized.")

    offset = 0
    limit = 50
    custom_id = 1
    processed_ids = set()
    total_tracks = 0
    total_duration = 0
    total_playlists = 0
    spinner = create_spinner()

    while True:
        try:
            response = sp.current_user_playlists(limit=limit, offset=offset)
            playlists = response.get("items", [])
            if not playlists:
                break

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(process_single_playlist, playlist): playlist
                    for playlist in playlists
                    if playlist["id"] not in processed_ids
                }

                for i, future in enumerate(as_completed(futures), 1):
                    try:
                        result = future.result()
                        if result:
                            processed_ids.add(result["spotify_id"])
                            result["id"] = custom_id
                            custom_id += 1
                            total_playlists += 1
                            total_tracks += result.get("track_count", 0)
                            total_duration += result.get("duration_seconds", 0)

                            # Update progress with spinner
                            progress = int((i / len(futures)) * 10)
                            bar = "#" * progress + "-" * (10 - progress)
                            sys.stdout.write(f"\r{next(spinner)} Fetching playlists: [{bar}] {i}/{len(futures)}")
                            sys.stdout.flush()

                            yield result
                    except Exception as e:
                        failed_playlist = futures[future]
                        logger.error(f"Error processing playlist {failed_playlist['name']}: {e}")

            if response["next"] is None:
                break

            offset += limit

        except Exception as e:
            logger.error(f"Error fetching playlists: {e}")
            return total_playlists, total_tracks, total_duration

    # Clear the progress line
    sys.stdout.write("\r" + " " * 50 + "\r")
    sys.stdout.flush()
    
    return total_playlists, total_tracks, total_duration

def get_all_playlists_with_details() -> List[Dict]:
    """
    Fetch all playlists with detailed information.
    Returns:
        list[dict]: A list of all processed playlists.
    """
    playlists = list(process_playlists())
    total_playlists = len(playlists)
    total_tracks = sum(p.get("track_count", 0) for p in playlists)
    total_duration = sum(p.get("duration_seconds", 0) for p in playlists)
    
    formatted_duration = format_duration(total_duration)
    print(f"Done! Fetched {total_playlists} playlists, {total_tracks} tracks, "
          f"and {formatted_duration} playback time.")
    
    return playlists

def save_playlists_to_file(playlists, filename="playlists_data.json"):
    """Save playlists data to a file with a temporary write process."""
    temp_filename = f"{filename}.tmp"
    try:
        with open(temp_filename, "w") as temp_file:
            json.dump(playlists, temp_file)
        os.replace(temp_filename, filename)  # Atomically replace the old file
    except Exception as e:
        logger.error(f"Error saving playlists to {filename}: {str(e)}")

def load_playlists_from_file(filename="playlists_data.json"):
    """Load playlists data from a file."""
    if os.path.exists(filename):
        try:
            with open(filename, "r") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Error loading playlists from {filename}: {str(e)}")
    return []

def display_playlists_table(playlists):
    """Display playlists in a tabular format."""
    print("\nFetching all playlists...\n")
    try:
        playlist_data = prepare_table_data(playlists)
        print(tabulate(
            playlist_data,
            headers=["ID", "User", "Name", "Duration"],
            tablefmt="grid",
        ))
    except Exception as e:
        logger.error(f"Error displaying playlists: {str(e)}")

def display_selected_playlists(selected_ids, all_playlists):
    """
    Display the selected playlists with their original IDs using tabulate.
    :param selected_ids: List of selected playlist IDs
    :param all_playlists: List of all playlists (general table)
    """
    selected_playlists = [
        playlist for playlist in all_playlists if playlist["id"] in selected_ids
    ]

    table_data = prepare_table_data(selected_playlists)

    print("\nSelected Playlist Data:")
    print(tabulate(
        table_data,
        headers=["ID", "User", "Name", "Duration"],
        tablefmt="grid",
    ))

def format_duration(seconds):
    """Format seconds to hh:mm:ss."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

#if __name__ == "__main__":
#    try:
#        playlists = get_all_playlists_with_details()
#        save_playlists_to_file(playlists)
#        display_playlists_table(playlists)
#
#        # Print final message
#        total_playlists, total_tracks, total_duration = get_all_playlists_with_details()
#        formatted_duration = format_duration(total_duration)
#        print(f"\nDone! Fetched {total_playlists} playlists, {total_tracks} tracks, "
#              f"and {formatted_duration} playback time.", end="")
#    except KeyboardInterrupt:
#        print("\nProcess interrupted by user. Exiting...")
#        sys.exit(0)
#    except Exception as e:
#        logger.error(f"Unexpected error: {str(e)}")
