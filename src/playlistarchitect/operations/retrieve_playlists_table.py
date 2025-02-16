import json
import os
import sys
import logging
import time
import threading
import itertools
from typing import List, Dict, Generator
from tabulate import tabulate
from concurrent.futures import ThreadPoolExecutor, as_completed
from playlistarchitect.auth.spotify_auth import get_spotify_client, initialize_spotify_client
from playlistarchitect.utils.playlist_helpers import process_single_playlist
from playlistarchitect.utils.formatting_helpers import truncate

# Setup logging
logger = logging.getLogger(__name__)

class ProgressDisplay:
    def __init__(self, total_items=None):
        self.spinner = itertools.cycle('|/-\\')
        self.running = False
        self.thread = None
        self.current = 0
        self.total = total_items
        self.lock = threading.Lock()

    def update_progress(self):
        while self.running:
            with self.lock:
                if self.total:
                    progress = int(30 * self.current / self.total)
                    bar = '=' * progress + '>' + ' ' * (30 - progress)
                    sys.stdout.write(f"\r{next(self.spinner)} Fetching playlists... [{bar}] {self.current}/{self.total}")
                else:
                    sys.stdout.write(f"\r{next(self.spinner)} Fetching playlists...")
                sys.stdout.flush()
            time.sleep(0.1)

    def increment(self):
        with self.lock:
            self.current += 1

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.update_progress)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            sys.stdout.write("\r" + " " * 80 + "\r")  # Clear the line
            sys.stdout.flush()

def process_playlists() -> Generator[Dict, None, None]:
    """
    Process user's playlists using multithreading while preserving IDs.
    """
    initialize_spotify_client()
    sp = get_spotify_client()

    if sp is None:
        logger.critical("Spotify client is None! Cannot continue.")
        raise RuntimeError("Spotify client is not initialized.")

    # Load cached playlists
    cached_playlists = load_playlists_from_file()
    cached_playlist_map = {p["spotify_id"]: p for p in cached_playlists}

    # First, get total number of playlists
    initial_response = sp.current_user_playlists(limit=1)
    total_playlist_count = initial_response['total']

    offset, limit = 0, 50
    processed_ids = set()
    total_playlists, total_tracks, total_duration_ms = 0, 0, 0
    progress_display = ProgressDisplay(total_playlist_count)

    try:
        progress_display.start()
        while True:
            response = sp.current_user_playlists(limit=limit, offset=offset)
            playlists = response.get("items", [])
            if not playlists:
                break

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(process_single_playlist, pl): pl for pl in playlists}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            spotify_id = result["spotify_id"]

                            # Preserve ID if the playlist exists in cache
                            if spotify_id in cached_playlist_map:
                                result["id"] = cached_playlist_map[spotify_id]["id"]
                            else:
                                # Assign new ID only to new playlists
                                new_id = max([p["id"] for p in cached_playlists], default=0) + 1
                                result["id"] = new_id
                                cached_playlist_map[spotify_id] = result  # Store in cache

                            processed_ids.add(spotify_id)
                            total_playlists += 1
                            total_tracks += result.get("track_count", 0)
                            total_duration_ms += result.get("duration_ms", 0)
                            progress_display.increment()
                            yield result
                    except Exception as e:
                        logger.error(f"Error processing playlist: {e}")

            if response["next"] is None:
                break
            offset += limit

    finally:
        progress_display.stop()

    yield {
        "total_playlists": total_playlists,
        "total_tracks": total_tracks,
        "total_duration": total_duration_ms // 1000  # Convert to seconds
    }

def get_all_playlists_with_details() -> List[Dict]:
    """
    Fetch all playlists with detailed information.
    Returns:
        list[dict]: A list of all processed playlists.
    """
    playlists = []
    summary = {}
    for result in process_playlists():
        if isinstance(result, dict) and "spotify_id" in result:
            playlists.append(result)
        else:
            summary = result

    print(f"\nDone! Fetched {summary.get('total_playlists', 0)} playlists, "
          f"{summary.get('total_tracks', 0)} tracks, "
          f"and {format_duration(summary.get('total_duration', 0))} playback time.")

    return playlists

def save_playlists_to_file(playlists, filename="playlists_data.json"):
    """Save playlists data, ensuring IDs are preserved."""
    for i, playlist in enumerate(playlists, start=1):
        if "id" not in playlist:  # Only assign ID if missing
            playlist["id"] = i
    temp_filename = f"{filename}.tmp"
    try:
        with open(temp_filename, "w") as temp_file:
            json.dump(playlists, temp_file, indent=4)
        os.replace(temp_filename, filename)
    except Exception as e:
        logger.error(f"Error saving playlists to {filename}: {e}")

def load_playlists_from_file(filename="playlists_data.json"):
    """Load playlists from file and ensure IDs remain consistent."""
    if os.path.exists(filename):
        try:
            with open(filename, "r") as file:
                playlists = json.load(file)
                return playlists
        except Exception as e:
            logger.error(f"Error loading playlists from {filename}: {e}")
    return []

def prepare_table_data(playlists, truncate_length=40, selected_ids=None):
    """
    Prepare data for table display.
    Args:
        playlists (list): The list of playlists.
        truncate_length (int): Maximum text length for truncation.
        selected_ids (set): The set of selected playlist IDs.
    Returns:
        list: A formatted list ready for tabulate.
    """
    if selected_ids is None:
        selected_ids = set()

    # Sort playlists by ID in ascending order
    sorted_playlists = sorted(playlists, key=lambda p: p.get("id", float("inf")))

    return [
        ["███" if playlist.get("id") in selected_ids else "-",  # Selection indicator
         index + 1,  # Generate Count dynamically
         playlist.get("id", "N/A"),  
         truncate(playlist["user"], truncate_length), 
         truncate(playlist["name"], truncate_length),
         playlist["track_count"], 
         format_duration(playlist["duration_ms"] // 1000)]
        for index, playlist in enumerate(sorted_playlists)
    ]
    

def display_playlists_table(playlists, msg="", selected_ids=None):
    """
    Display playlists in a tabular format.
    Args:
        playlists (list): List of playlists.
        msg (str): Message to display before the table.
        selected_ids (set): Set of selected playlist IDs.
    """
    try:
        print(f"\n{msg}\n")
        print(tabulate(
            prepare_table_data(playlists, selected_ids=selected_ids), 
            headers=["Sel.", "#", "ID", "User", "Name", "Tracks", "Duration"],
            tablefmt="grid",
            colalign=("center", "right", "right", "left", "left", "right", "center")
        ))
    except Exception as e:
        logger.error(f"Error displaying playlists: {e}")       
        
        
def display_selected_playlists(selected_ids, all_playlists):
    """
    Display the selected playlists with their original IDs using tabulate.
    The first column is "Count" (incremental index), followed by "ID".
    """
    selected_playlists = [
        playlist for playlist in all_playlists if playlist["id"] in selected_ids
    ]

    table_data = [
        [index + 1,  # Count (incremental)
         playlist["id"], 
         playlist["user"], 
         playlist["name"], 
         playlist["track_count"], 
         format_duration(playlist["duration_ms"] // 1000)]  # Convert ms to seconds
        for index, playlist in enumerate(selected_playlists)
    ]

    print("\nSelected Playlist Data:")
    print(tabulate(
        table_data,
        headers=["#", "ID", "User", "Name", "Tracks", "Duration"],  # Fixed headers
        tablefmt="grid",
    ))

def format_duration(seconds):
    """Format seconds to hh:mm:ss."""
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

if __name__ == "__main__":
    try:
        playlists = get_all_playlists_with_details()
        save_playlists_to_file(playlists)
        display_playlists_table(playlists)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")