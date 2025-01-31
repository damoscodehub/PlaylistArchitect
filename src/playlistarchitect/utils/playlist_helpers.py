from playlistarchitect.utils.logging_utils import logger
from playlistarchitect.auth.spotify_auth import get_spotify_client
from playlistarchitect.utils.formatting_helpers import format_duration, truncate

def process_single_playlist(playlist):
    """
    Process a single playlist to fetch its details and calculate the total duration.
    
    Args:
        playlist (dict): The playlist data from the Spotify API.
    
    Returns:
        dict: Processed playlist information (ID, name, duration, etc.).
    """
    sp = get_spotify_client()  # Ensure a valid Spotify client

    if sp is None:
        logger.error(f"Spotify client is None when processing playlist {playlist['name']}.")
        return None  # Return None to avoid breaking processing

    try:
        playlist_id = playlist["id"]
        name = playlist["name"]
        owner = playlist["owner"]["display_name"]

        total_duration_ms = 0
        track_count = 0
        track_offset = 0

        logger.debug(f"Fetching tracks for playlist: {name} (ID: {playlist_id})")

        while True:
            tracks_response = sp.playlist_items(
                playlist_id,
                offset=track_offset,
                fields="items.track.duration_ms,next,total",
                additional_types=["track"]
            )

            if "items" in tracks_response:
                for track in tracks_response["items"]:
                    if track.get("track") and track["track"].get("duration_ms"):
                        total_duration_ms += track["track"]["duration_ms"]
                        track_count += 1

            if not tracks_response.get("next"):
                break

            track_offset += 100  # Move to next batch of tracks

        # Keep duration in milliseconds until final formatting
        return {
            "id": None,  # Placeholder, assigned later
            "spotify_id": playlist_id,
            "user": truncate(owner, 40),
            "name": truncate(name, 40),
            "duration_ms": total_duration_ms,  # Store raw milliseconds
            "track_count": track_count
        }

    except Exception as e:
        logger.error(f"Error processing playlist {name[:40]}: {str(e)}")
        return None