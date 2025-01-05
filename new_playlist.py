import random
from spotify_auth import sp
from retrieve_playlists_table import get_all_playlists_with_details, format_duration, truncate


def get_song_from_playlist(playlist_id, total_duration_ms, acceptable_deviation_ms):
    """Fetch random songs from a playlist until the desired total duration is met."""
    song_list = []
    track_offset = 0
    while True:
        tracks_response = sp.playlist_items(
            playlist_id, 
            offset=track_offset, 
            fields="items.track.duration_ms,items.track.name", 
            additional_types=["track"]
        )

        for track in tracks_response['items']:
            if track['track']:
                song_list.append({
                    "name": track['track']['name'],
                    "duration_ms": track['track']['duration_ms']
                })

        if not tracks_response['next']:
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


def create_new_playlist():
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

    time_input = input("Enter the total time for the playlist (hh:mm:ss): ").strip()
    hours, minutes, seconds = map(int, time_input.split(":"))
    total_duration_ms = (hours * 3600 + minutes * 60 + seconds) * 1000

    acceptable_deviation_input = input("Enter the acceptable +- variation in minutes (e.g. 2): ").strip()
    acceptable_deviation_ms = int(acceptable_deviation_input) * 60 * 1000

    # 2. Select playlists for random song selection
    all_playlists = list(get_all_playlists_with_details())
    print("Available playlists:")
    for playlist in all_playlists:
        print(f"{playlist['id']}: {playlist['name']}")

    selected_playlists = input("Select playlist IDs (comma-separated) to fetch songs from: ").strip().split(",")
    selected_playlists = [int(x.strip()) for x in selected_playlists]

    # 3. Select songs from chosen playlists
    all_selected_songs = []
    for playlist_id in selected_playlists:
        print(f"Fetching songs from playlist {playlist_id}...")
        songs, total_time = get_song_from_playlist(all_playlists[playlist_id - 1]['id'], total_duration_ms, acceptable_deviation_ms)
        all_selected_songs.extend(songs)
        print(f"Fetched {len(songs)} songs totaling {format_duration(total_time)}.")

    # 4. Ask to add more songs or commit
    while True:
        add_more = input("Would you like to add more songs? (y/n): ").strip().lower()
        if add_more == 'y':
            # Prompt for more songs
            new_time_input = input("Enter the additional time to fill (hh:mm:ss): ").strip()
            hours, minutes, seconds = map(int, new_time_input.split(":"))
            additional_time_ms = (hours * 3600 + minutes * 60 + seconds) * 1000
            new_songs, new_time = get_song_from_playlist(
                all_playlists[playlist_id - 1]['id'], additional_time_ms, acceptable_deviation_ms
            )
            all_selected_songs.extend(new_songs)
            print(f"Fetched {len(new_songs)} additional songs totaling {format_duration(new_time)}.")
        else:
            break

    # 5. Commit the new playlist
    final_playlist_name = truncate(playlist_name, 40)
    playlist = sp.user_playlist_create(sp.current_user()['id'], final_playlist_name, public=(privacy == "public"))
    track_uris = [f"spotify:track:{track['uri']}" for track in all_selected_songs]
    sp.playlist_add_items(playlist['id'], track_uris)
    print(f"New playlist '{final_playlist_name}' created with {len(all_selected_songs)} songs.")