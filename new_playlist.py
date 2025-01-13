from spotify_auth import get_spotify_client
from retrieve_playlists_table import format_duration, truncate, display_playlists_table, save_playlists_to_file
from helpers import assign_temporary_ids  # Import the helper function
import random

sp = get_spotify_client()

def get_song_from_playlist(playlist_id, total_duration_ms, acceptable_deviation_ms):
    """Fetch random songs from a playlist until the desired total duration is met."""
    song_list = []
    track_offset = 0
    while True:
        tracks_response = sp.playlist_items(
            playlist_id,
            offset=track_offset, 
            fields="items.track.uri,items.track.duration_ms,items.track.name", 
            additional_types=["track"]
        )

        for track in tracks_response['items']:
            if track['track']:
                song_list.append({
                    "uri": track['track']['uri'],
                    "name": track['track']['name'],
                    "duration_ms": track['track']['duration_ms']
                })

        if 'next' not in tracks_response or not tracks_response['next']:
            break
        track_offset += 100

    # Randomly pick songs until total duration is close to the target duration
    selected_songs = []
    total_time = 0
    while total_time < total_duration_ms - acceptable_deviation_ms:
        song = random.choice(song_list)
        selected_songs.append(song)
        total_time += song['duration_ms']

    return selected_songs, total_time

def create_new_playlist(playlists):
    """Handle the creation of a new playlist."""
    # 1. Prompt for new playlist details
    playlist_name = input("Enter a name for the new playlist: ").strip()
    privacy = input("Choose privacy (1. Public, 2. Private): ").strip()

    # Convert privacy choice to valid string
    if privacy == "1":
        privacy = "public"
    elif privacy == "2":
        privacy = "private"
    else:
        print("Invalid choice. Defaulting to private.")
        privacy = "private"

    all_selected_songs = []

    while True:
        # Assign temporary IDs before displaying
        assign_temporary_ids(playlists)
        
        # Display available playlists as a table
        display_playlists_table(playlists)

        # Select playlists for random song selection
        selected_playlists_input = input("Select playlist IDs (comma-separated) to fetch songs from.\n"
                                         "• Add \"-t\" flag to shuffle tracks (they won't be grouped by playlists)\n"
                                         "• Add \"-p\" flag to shuffle the order of selected playlists source (tracks will be grouped by playlists)\n"
                                         "• No flag to import from the playlist in the entered order (tracks will be grouped by playlists)\n>: ").strip()
        
        # Parse flags
        shuffle_tracks = "-t" in selected_playlists_input
        shuffle_playlists = "-p" in selected_playlists_input
        selected_playlists_input = selected_playlists_input.replace("-t", "").replace("-p", "").strip()
        selected_playlists = [int(x.strip()) for x in selected_playlists_input.split(",")]

        # Shuffle playlists if the flag is set
        if shuffle_playlists:
            random.shuffle(selected_playlists)

        # Prompt for time and acceptable deviation
        time_input = input("Set the time you want to fill with tracks from each playlist (hh:mm:ss). Leave blank to ignore: ").strip()
        if time_input:
            hours, minutes, seconds = map(int, time_input.split(":"))
            total_duration_ms = (hours * 3600 + minutes * 60 + seconds) * 1000
        else:
            total_duration_ms = None

        if not total_duration_ms:
            time_input = input("Set the total time you want to fill with tracks (hh:mm:ss): ").strip()
            hours, minutes, seconds = map(int, time_input.split(":"))
            total_duration_ms = (hours * 3600 + minutes * 60 + seconds) * 1000

        acceptable_deviation_input = input("Set the acceptable +- variation in minutes (e.g. 2): ").strip()
        acceptable_deviation_ms = int(acceptable_deviation_input) * 60 * 1000

        # Select songs from chosen playlists
        for playlist_id in selected_playlists:
            print(f"Fetching songs from playlist {playlist_id}...")
            spotify_playlist_id = playlists[playlist_id - 1]['spotify_id']  # Use the correct Spotify playlist ID
            songs, total_time = get_song_from_playlist(spotify_playlist_id, total_duration_ms, acceptable_deviation_ms)
            all_selected_songs.extend(songs)
            print(f"Fetched {len(songs)} songs totaling {format_duration(total_time)}.")

        # Shuffle tracks if the flag is set
        if shuffle_tracks:
            random.shuffle(all_selected_songs)

        # Prompt for next action
        while True:
            next_action = input("Select an option:\n1. Add more songs\n2. Save the playlist\n3. Cancel\nEnter your choice: ").strip()
            if next_action == "1":
                break  # Continue the loop to add more songs
            elif next_action == "2":
                # Save the playlist
                final_playlist_name = truncate(playlist_name, 40)
                playlist = sp.user_playlist_create(sp.current_user()['id'], final_playlist_name, public=(privacy == "public"))
                track_uris = [track['uri'] for track in all_selected_songs]  # Correctly format the track URIs
                print(f"Track URIs to be added: {track_uris}")  # Debug print to check URIs
                sp.playlist_add_items(playlist['id'], track_uris)
                print(f"New playlist '{final_playlist_name}' created with {len(all_selected_songs)} songs.")

                # Update cached playlists data
                new_playlist_info = {
                    "id": len(playlists) + 1,
                    "spotify_id": playlist['id'],
                    "user": truncate(sp.current_user()['display_name'], 40),
                    "name": truncate(final_playlist_name, 40),
                    "duration": format_duration(sum(track['duration_ms'] for track in all_selected_songs))
                }
                playlists.append(new_playlist_info)
                save_playlists_to_file(playlists)  # Update cached playlists data
                return  # Exit the function
            elif next_action == "3":
                print("Playlist creation canceled.")
                return  # Exit the function
            else:
                print("Invalid option. Please try again.")

        # Remove the temporary 'id' field after display
        for playlist in playlists:
            if 'id' in playlist:
                del playlist['id']