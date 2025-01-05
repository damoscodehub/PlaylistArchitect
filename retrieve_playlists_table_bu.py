from tabulate import tabulate
import spotipy
from spotify_auth import sp  # Import the authenticated Spotify client
import math
import time


def format_duration(milliseconds):
    """Convert a duration in milliseconds to the format hh:mm:ss."""
    seconds = milliseconds // 1000
    minutes = seconds // 60
    hours = minutes // 60
    return f"{hours:02}:{minutes % 60:02}:{seconds % 60:02}"


def truncate(text, length):
    """Truncate text to the specified length, adding '...' if necessary."""
    return text if len(text) <= length else text[:length - 3] + "..."


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
            print(f"Processing playlist: {playlist['name'][:40]}...")  # Display the progress message

            try:
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
                    "user": truncate(owner, 40),
                    "name": truncate(name, 40),
                    "duration": format_duration(total_duration_ms)
                }
                custom_id += 1

                # Print the processing result
                print(
                    f"Finished processing: ID={playlist_info['id']} | User={playlist_info['user']} "
                    f"| Name={playlist_info['name']} | Duration={playlist_info['duration']}"
                )

                # Yield the result
                yield playlist_info

            except Exception as e:
                print(f"Error processing playlist {playlist['name'][:40]}: {str(e)}")

        if response['next'] is None:
            break

        offset += limit


if __name__ == "__main__":
    print("Fetching all playlists...\n")
    playlist_data = []  # List to store all playlist details

    try:
        for playlist in process_playlists():
            # Add the playlist info to the list
            playlist_data.append([playlist["id"], playlist["user"], playlist["name"], playlist["duration"]])

        # Print the data in a table format
        print("\nFinal Playlist Data:")
        print(tabulate(playlist_data, headers=["ID", "User", "Name", "Duration"], tablefmt="grid"))

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"\nError: {str(e)}")