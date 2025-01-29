import json
import os
import sys
import logging
from tabulate import tabulate
from playlistarchitect.auth.spotify_auth import get_spotify_client


# Setup logging
logger = logging.getLogger(__name__)

sp = get_spotify_client()


def format_duration(milliseconds):
    """Convert a duration in milliseconds to the format hh:mm:ss."""
    seconds = milliseconds // 1000
    minutes = seconds // 60
    hours = minutes // 60
    return f"{hours:02}:{minutes % 60:02}:{seconds % 60:02}"


def truncate(text, length):
    """Truncate text to the specified length, adding '...' if necessary."""
    return text if len(text) <= length else text[:length - 3] + "..."


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


def process_playlists(fetch_details=True):
    """Generator to process user's playlists one by one."""
    offset = 0
    limit = 50
    custom_id = 1

    while True:
        response = sp.current_user_playlists(limit=limit, offset=offset)
        for playlist in response["items"]:
            print(f"Processing playlist: {playlist['name'][:40]}...")

            try:
                playlist_id = playlist["id"]
                name = playlist["name"]
                owner = playlist["owner"]["display_name"]

                total_duration_ms = 0
                if fetch_details:
                    track_offset = 0
                    while True:
                        tracks_response = sp.playlist_items(
                            playlist_id,
                            offset=track_offset,
                            fields="items.track.duration_ms,next",
                            additional_types=["track"],
                        )
                        for track in tracks_response["items"]:
                            if track["track"]:
                                total_duration_ms += track["track"]["duration_ms"]

                        if not tracks_response.get("next"):
                            break
                        track_offset += 100

                playlist_info = {
                    "id": custom_id,
                    "spotify_id": playlist_id,
                    "user": truncate(owner, 40),
                    "name": truncate(name, 40),
                    "duration": format_duration(total_duration_ms) if fetch_details else "N/A",
                }
                custom_id += 1

                logger.info(
                    f"Finished processing(is this?): ID={playlist_info['id']} | User={playlist_info['user']} "
                    f"| Name={playlist_info['name']} | Duration={playlist_info['duration']}"
                )

                yield playlist_info

            except Exception as e:
                logger.error(f"Error processing playlist {playlist['name'][:40]}: {str(e)}")

        if response.get("next") is None:
            break

        offset += limit


def get_all_playlists_with_details(fetch_details=True):
    """Fetch all playlists with detailed information."""
    playlists = []
    logger.info("Fetching all playlists...")

    try:
        for playlist in process_playlists(fetch_details=fetch_details):
            playlists.append(playlist)
    except Exception as e:
        logger.error(f"Error fetching playlists: {str(e)}")

    logger.info(f"Total playlists fetched: {len(playlists)}")
    return playlists


def save_playlists_to_file(playlists, filename="playlists_data.json"):
    """Save playlists data to a file with a temporary write process."""
    temp_filename = f"{filename}.tmp"
    try:
        with open(temp_filename, "w") as temp_file:
            json.dump(playlists, temp_file)
        os.replace(temp_filename, filename)  # Atomically replace the old file
        logger.info(f"Playlists saved to {filename}")
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


if __name__ == "__main__":
    try:
        playlists = get_all_playlists_with_details()
        save_playlists_to_file(playlists)
        display_playlists_table(playlists)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
