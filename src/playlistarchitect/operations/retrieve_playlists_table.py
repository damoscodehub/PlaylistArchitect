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

def prepare_table_data(playlists, truncate_length=40, selected_ids=None):
    """
    Prepare data for table display.
    
    Args:
        playlists (list): List of playlists.
        truncate_length (int): Max text length for truncation.
        selected_ids (set or None): Set of selected playlist IDs.
    """
    table_data = []
    for playlist in playlists:
        playlist_id = playlist.get("id", "N/A")
        user = truncate(playlist.get("user", "Unknown"), truncate_length)
        name = truncate(playlist.get("name", "Unnamed Playlist"), truncate_length)
        track_count = playlist.get("track_count", 0)
        duration = format_duration(playlist.get("duration_ms", 0) // 1000)
        # Build row based on what columns should be included
        row = []
        if selected_ids is not None:  # Only add selection column if selected_ids is provided
            row.append("███" if playlist_id in selected_ids else "-")
        row.extend([playlist_id, user, name, track_count, duration])
        table_data.append(row)
    return table_data


def display_playlists_table(playlists, msg="", selected_ids=None, show_selection_column=False,
                            show_count_column=False, total_details=True, sort_by="id",
                            sort_reverse=False, table_format="simple"):
    """
    Display playlists in a tabular format.
    
    Args:
        playlists (list): List of playlists.
        msg (str): Message to display before the table.
        selected_ids (set): Set of selected playlist IDs.
        show_selection_column (bool): Whether to include the "Sel." column.
        show_count_column (bool): Whether to include the "Count" column.
        total_details (bool): Whether to display total playlists, tracks, and duration.
        sort_by (str): Column to sort by. Options: "name", "user", "tracks", "duration", "id"
        sort_reverse (bool): If True, sort in descending order
    """
    try:
        print(f"\n{msg}\n")

        if not playlists:
            print("⚠️ No playlists found! Returning without displaying a table.")
            return

        # Define sorting key functions
        sort_keys = {
            "name": lambda p: p.get("name", "").lower(),
            "user": lambda p: p.get("user", "").lower(),
            "tracks": lambda p: p.get("track_count", 0),
            "duration": lambda p: p.get("duration_ms", 0),
            "id": lambda p: p.get("id", 0)
        }

        # Sort playlists using the specified key
        sort_key = sort_keys.get(sort_by.lower(), sort_keys["name"])  # Default to name sorting if invalid key
        sorted_playlists = sorted(playlists, key=sort_key, reverse=sort_reverse)

        # Define headers and prepare table data
        headers = []
        column_alignments = []
        
        if show_count_column:
            headers.append("#")
            column_alignments.append("center")
            
        if show_selection_column:
            headers.append("Sel.")
            column_alignments.append("center")
            
        headers.extend(["ID", "User", "Name", "Tracks", "Duration"])
        column_alignments.extend(["center", "left", "left", "right", "center"])

        # Prepare table data with selection column only if needed
        table_data = prepare_table_data(
            sorted_playlists,
            selected_ids=None if not show_selection_column else selected_ids
        )

        # Add count numbers
        if show_count_column:
            for i, row in enumerate(table_data, 1):
                row.insert(0, i)

        # Print the table
        print(tabulate(
            table_data,
            headers=headers,
            tablefmt=table_format,
            colalign=column_alignments
        ))

        # Calculate and display totals if requested
        if total_details:
            total_playlists = len(playlists)
            total_tracks = sum(playlist.get("track_count", 0) for playlist in playlists)
            total_duration_ms = sum(playlist.get("duration_ms", 0) for playlist in playlists)
            total_duration = format_duration(total_duration_ms // 1000)
            
            print(f"\n{total_playlists} playlists, {total_tracks} tracks, {total_duration} playback time.")

    except Exception as e:
        logger.error(f"Error displaying playlists: {e}")
        print(f"❌ Error displaying playlists: {e}")
        

def show_selected_playlists(selected_playlists, all_playlists, msg="Currently selected playlists"):
    """
    Display the selected playlists in a table format without the "Sel." column.
    
    Args:
        selected_playlists (list): List of selected playlists (with IDs).
        all_playlists (list): Full list of playlists.
        msg (str): Message to display before the table.
    """
    # Filter playlists to include only the selected ones
    selected_playlists_filtered = [p for p in all_playlists if p["id"] in [p["id"] for p in selected_playlists]]

    # Display the selected playlists without the "Sel." column
    display_playlists_table(
        selected_playlists_filtered,
        msg=msg,
        show_selection_column=False,  # No "Sel." column
        show_count_column=True
    )


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