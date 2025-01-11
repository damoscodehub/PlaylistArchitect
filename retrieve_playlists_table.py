import json
import os
from tabulate import tabulate
from spotify_auth import get_spotify_client
import sys

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

def process_playlists():
    """Generator to process user's playlists one by one."""
    offset = 0
    limit = 50
    custom_id = 1

    while True:
        response = sp.current_user_playlists(limit=limit, offset=offset)
        for playlist in response['items']:
            print(f"Processing playlist: {playlist['name'][:40]}...")

            try:
                playlist_id = playlist['id']
                name = playlist['name']
                owner = playlist['owner']['display_name']

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

                playlist_info = {
                    "id": custom_id,
                    "spotify_id": playlist_id,
                    "user": truncate(owner, 40),
                    "name": truncate(name, 40),
                    "duration": format_duration(total_duration_ms)
                }
                custom_id += 1

                print(
                    f"Finished processing: ID={playlist_info['id']} | User={playlist_info['user']} "
                    f"| Name={playlist_info['name']} | Duration={playlist_info['duration']}"
                )

                yield playlist_info

            except Exception as e:
                print(f"Error processing playlist {playlist['name'][:40]}: {str(e)}")

        if response['next'] is None:
            break

        offset += limit

def get_all_playlists_with_details():
    """Fetch all playlists with detailed information."""
    playlists = []

    # Process user playlists
    for playlist in process_playlists():
        playlists.append(playlist)

    print(f"Total playlists fetched: {len(playlists)}")
    return playlists

def save_playlists_to_file(playlists, filename="playlists_data.json"):
    """Save playlists data to a file."""
    with open(filename, "w") as file:
        json.dump(playlists, file)

def load_playlists_from_file(filename="playlists_data.json"):
    """Load playlists data from a file."""
    if os.path.exists(filename):
        with open(filename, "r") as file:
            return json.load(file)
    return []

def display_playlists_table(playlists):
    """Display playlists in a tabular format."""
    # os.system('cls' if os.name == 'nt' else 'clear') # Clear the console

    print("\nFetching all playlists...\n")
    playlist_data = []

    try:
        for playlist in playlists:
            playlist_data.append([
                playlist["id"],
                playlist["user"],
                playlist["name"],
                playlist["duration"]
            ])

        print(f"Debug: Playlist data to be displayed: {playlist_data}")

        print("\nFinal Playlist Data:")
        print(tabulate(
            playlist_data,
            headers=["ID", "User", "Name", "Duration"],
            tablefmt="grid"
        ))

        sys.stdout.flush()

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    playlists = get_all_playlists_with_details()
    save_playlists_to_file(playlists)
    display_playlists_table(playlists)