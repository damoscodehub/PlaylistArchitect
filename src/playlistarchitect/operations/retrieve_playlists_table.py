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

    # Load cached playlists and initialize ID counter
    cached_playlists = load_playlists_from_file()
    cached_playlist_map = {p["spotify_id"]: p for p in cached_playlists}
    next_id = max([p["id"] for p in cached_playlists], default=0)

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
                                # Assign new incremental ID for new playlists
                                next_id += 1
                                result["id"] = next_id
                                cached_playlist_map[spotify_id] = result  # Store in cache
                                cached_playlists.append(result)  # Add to cached_playlists list

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

def prepare_table_data(playlists, truncate_length=40, selected_ids=None, show_selection_column=True):
    """
    Prepare data for table display.
    
    Args:
        playlists (list): List of playlists.
        truncate_length (int): Max text length for truncation.
        selected_ids (set or None): Set of selected playlist IDs.
        show_selection_column (bool): Whether to include the "Sel." column.

    Returns:
        list: Formatted list ready for tabulate.
    """
    if selected_ids is None:
        selected_ids = set()

    # Sort playlists by name to maintain consistent display order
    sorted_playlists = sorted(playlists, key=lambda p: p.get("name", "").lower())
    table_data = []

    # Use enumerate to generate the display count, starting from 1
    for display_count, playlist in enumerate(sorted_playlists, 1):
        # Get the stored ID for the playlist
        playlist_id = playlist.get("id", "N/A")
        user = truncate(playlist.get("user", "Unknown"), truncate_length)
        name = truncate(playlist.get("name", "Unnamed Playlist"), truncate_length)
        track_count = playlist.get("track_count", 0)
        duration = format_duration(playlist.get("duration_ms", 0) // 1000)

        row = []
        if show_selection_column:
            row.append("███" if playlist_id in selected_ids else "-")
        
        # Use display_count for the Count column and playlist_id for the ID column
        row.extend([display_count, playlist_id, user, name, track_count, duration])
        table_data.append(row)

    return table_data   

def display_playlists_table(playlists, msg="", selected_ids=None, show_selection_column=True):
    """
    Display playlists in a tabular format.
    
    Args:
        playlists (list): List of playlists.
        msg (str): Message to display before the table.
        selected_ids (set): Set of selected playlist IDs.
        show_selection_column (bool): Whether to include the "Sel." column.
    """
    try:
        print(f"\n{msg}\n")

        # Debugging output
        print(f"🔍 Debug Info: show_selection_column={show_selection_column}, selected_ids={selected_ids}")
        print(f"Total Playlists: {len(playlists)}")

        if len(playlists) == 0:
            print("⚠️ No playlists found! Returning without displaying a table.")
            return

        # Define headers based on whether the "Sel." column is included
        headers = ["Sel.", "Count", "ID", "User", "Name", "Tracks", "Duration"] if show_selection_column else \
                  ["Count", "ID", "User", "Name", "Tracks", "Duration"]

        # Get table data and debug it
        table_data = prepare_table_data(playlists, selected_ids=selected_ids, show_selection_column=show_selection_column)

        print(f"🔍 Debug Table Data (First 3 Rows): {table_data[:3]}")
        print(f"🔍 Expected Column Count: {len(headers)}, Actual Row Column Count: {len(table_data[0]) if table_data else 'No data'}")

        # Ensure no None values exist in table_data
        for row in table_data:
            if any(value is None for value in row):
                print(f"❌ Found None value in row: {row}")
                return  # Exit early to prevent tabulate error

        colalign_options = ("center", "center", "center", "left", "left", "center", "center") if show_selection_column else \
                   ("center", "center", "left", "left", "center", "center")
        
        try:
            # Use grid format but fallback to plain if it crashes
            print(tabulate(
                table_data, 
                headers=headers,
                tablefmt="grid",  # Restore grid format
                colalign=colalign_options  # Use dynamic colalign based on selection column
            ))
        except Exception as e:
            print(f"⚠️ Tabulate failed with 'grid' format: {e}")
            print("📌 Falling back to plain table format...\n")
            print(tabulate(
                table_data, 
                headers=headers,
                tablefmt="plain"  # Fallback to plain if grid fails
            )) 
    except Exception as e:
        logger.error(f"Error displaying playlists: {e}")
        print(f"❌ Error displaying playlists: {e}")


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
        display_playlists_table(playlists, "Showing selected playlists", show_selection_column=False)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")