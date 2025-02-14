# retrieve_playlists_table.py
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

    # Load cached playlists and build a proper lookup map
    cached_playlists = load_playlists_from_file()
    cached_playlist_map = {p["spotify_id"]: p for p in cached_playlists if "spotify_id" in p}

    # Ensure assigned_ids is initialized BEFORE logging
    assigned_ids = set(p["id"] for p in cached_playlists if "id" in p)

    logger.debug(f"Assigned IDs found: {assigned_ids}")

    # Initialize next_available_id AFTER assigned_ids exist
    next_available_id = max(assigned_ids, default=0) + 1
    logger.debug(f"Starting next_available_id at: {next_available_id}")

    # First, get total number of playlists
    initial_response = sp.current_user_playlists(limit=1)
    total_playlist_count = initial_response['total']

    offset, limit = 0, 50
    processed_spotify_ids = set()
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

                            # Skip if already processed
                            if spotify_id in processed_spotify_ids:
                                continue

                            logger.debug(f"Processing playlist {result['name']} with Spotify ID {spotify_id}")
                            
                            # ✅ Fix: Properly check if a playlist ID already exists
                            if spotify_id in cached_playlist_map and "id" in cached_playlist_map[spotify_id]:
                                result["id"] = cached_playlist_map[spotify_id]["id"]
                                logger.debug(f"Reusing cached ID {result['id']} for playlist {result['name']}")
                            else:
                                # ✅ Assign a unique new ID
                                result["id"] = next_available_id
                                logger.debug(f"Assigning new ID {next_available_id} to playlist {result['name']}")
                                assigned_ids.add(next_available_id)  # Track the ID
                                next_available_id += 1
                                
                            # ✅ Update the cache properly
                            cached_playlist_map[spotify_id] = result

                            processed_spotify_ids.add(spotify_id)
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

    # Save the playlists with unique IDs
    save_playlists_to_file(playlists)
    return playlists

def save_playlists_to_file(playlists, filename="playlists_data.json"):
    """Save playlists data, ensuring IDs are preserved."""

    # Debugging: Check what IDs exist before saving
    logger.debug(f"Saving playlists with assigned IDs: {[p.get('id', 'N/A') for p in playlists]}")

    # Find the maximum existing ID in the playlists
    max_id = max([p.get("id", 0) for p in playlists], default=0)

    # Assign new IDs to playlists that don't have one
    for playlist in playlists:
        if "id" not in playlist:
            max_id += 1
            playlist["id"] = max_id

    # Save the playlists to a temporary file
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

def prepare_table_data(playlists, truncate_length=40):
    # Sort playlists by ID in ascending order
    sorted_playlists = sorted(playlists, key=lambda p: p.get("id", float("inf")))
    
    return [
        [index + 1,  # Generate Count dynamically
         playlist.get("id", "N/A"),  
         truncate(playlist["user"], truncate_length), 
         truncate(playlist["name"], truncate_length),
         playlist["track_count"], 
         format_duration(playlist["duration_ms"] // 1000)]
        for index, playlist in enumerate(sorted_playlists)
    ]
    

def display_playlists_table(playlists, msg=""):
    """Display playlists in a tabular format."""
    try:
        print(f"\n{msg}\n")
        print(tabulate(
            prepare_table_data(playlists), 
            headers=["Count", "ID", "User", "Name", "Tracks", "Duration"],
            tablefmt="grid"
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
        headers=["Count", "ID", "User", "Name", "Tracks", "Duration"],  # Fixed headers
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