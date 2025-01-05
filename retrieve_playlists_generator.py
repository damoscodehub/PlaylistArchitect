import spotipy
from spotify_auth import sp  # Import the authenticated Spotify client
import math
import time
import sys


def format_duration(milliseconds):
    """Convert a duration in milliseconds to the format hh:mm:ss."""
    seconds = milliseconds // 1000
    minutes = seconds // 60
    hours = minutes // 60
    return f"{hours:02}:{minutes % 60:02}:{seconds % 60:02}"


def process_playlists():
    """
    Generator to process playlists one by one.
    
    Yields:
        dict: Processed playlist info with custom ID, user, name, and total duration.
    """
    offset = 0
    limit = 50  # Spotify API returns a maximum of 50 playlists per request
    custom_id = 1  # Custom in-account ID starting from 1

    while True:
        response = sp.current_user_playlists(limit=limit, offset=offset)
        for playlist in response['items']:
            try:
                temp_message = f"Processing playlist: {playlist['name']}..."
                sys.stdout.write(f"\r{temp_message}")
                sys.stdout.flush()

                # Get playlist details
                playlist_id = playlist['id']
                name = playlist['name']
                owner = playlist['owner']['display_name']

                # Calculate total duration of all tracks in the playlist
                total_duration_ms = 0
                track_offset = 0

                while True:
                    tracks_response = sp.playlist_items(
                        playlist_id,
                        offset=track_offset,
                        fields="items.track.duration_ms,next",
                        additional_types=["track"]
                    )
                    for track in tracks_response['items']:
                        if track['track']:
                            total_duration_ms += track['track']['duration_ms']

                    if not tracks_response['next']:
                        break

                    track_offset += 100

                # Final playlist details
                playlist_info = {
                    "id": custom_id,
                    "user": owner,
                    "name": name,
                    "duration": format_duration(total_duration_ms)
                }
                custom_id += 1

                # Yield the result
                yield playlist_info

            except Exception as e:
                sys.stdout.write(f"\rError processing playlist {playlist['name']}: {str(e)}\n")
                sys.stdout.flush()

        if response['next'] is None:
            break

        offset += limit


if __name__ == "__main__":
    print("Fetching all playlists...\n")
    try:
        for playlist in process_playlists():
            # Clear the temporary message
            sys.stdout.write("\r" + " " * 80 + "\r")  # Clear the line
            sys.stdout.flush()
            # Print the final result
            print(f"{playlist['id']:>3}: {playlist['name']} by {playlist['user']} [{playlist['duration']}]")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"\nError: {str(e)}")
