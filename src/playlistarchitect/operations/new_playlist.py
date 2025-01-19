from playlistarchitect.auth.spotify_auth import get_spotify_client
from playlistarchitect.operations.retrieve_playlists_table import (
    display_playlists_table,
)
from playlistarchitect.utils.helpers import assign_temporary_ids, menu_navigation, parse_time_input, get_variation_input
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
    """Handle the creation of a new playlist using the menu_navigation system."""
    all_selected_songs = []
    shuffle_option = "No shuffle"
    time_option = "Not specified"
    selected_playlists = []
    
    #Prompt for new playlist details
    playlist_name = input("Enter a name for the new playlist: ").strip()

    # Loop to get valid privacy choice
    while True:
        privacy = input("Choose privacy (1. Public, 2. Private): ").strip()
        if privacy == "1":
            privacy = "public"
            break
        elif privacy == "2":
            privacy = "private"
            break
        else:
            print("Invalid choice. Please choose either 1 for Public or 2 for Private.")
    
    print(f"Privacy: {privacy}")
    assign_temporary_ids(playlists)
    display_playlists_table(playlists)


    # Select playlists by ID
    while True:
        selected_input = input("Select playlist IDs (comma-separated) to fetch songs from: ").strip()
        try:
            selected_playlists = [int(x.strip()) for x in selected_input.split(",")]
            if not selected_playlists:
                print("No playlists selected. Please enter at least one playlist ID.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter valid numeric playlist IDs.")



    while True:        
        main_choice = menu_navigation(
            ["Show selected playlists", "Add playlists to selection", "Remove playlists from selection", 
             "Proceed with current selection", "Back", "Cancel"],
            "Select an option:"
        )

        if main_choice == 1:
            # Show selected playlists
            print("\nCurrently selected playlists:", selected_playlists)

        elif main_choice == 2:
            # Add playlists
            display_playlists_table(playlists)
            selected_input = input("Enter playlist IDs to add (comma-separated): ").strip()
            try:
                selected_playlists.extend([int(x.strip()) for x in selected_input.split(",")])
            except ValueError:
                print("Invalid input. Please enter numeric playlist IDs.")

        elif main_choice == 3:
            # Remove playlists
            if selected_playlists:
                print("Currently selected playlists:", selected_playlists)
                to_remove = input("Enter playlist IDs to remove (comma-separated): ").strip()
                try:
                    for playlist_id in map(int, to_remove.split(",")):
                        if playlist_id in selected_playlists:
                            selected_playlists.remove(playlist_id)
                except ValueError:
                    print("Invalid input. Please enter numeric playlist IDs.")
            else:
                print("No playlists to remove.")

        elif main_choice == 4:
            # Proceed with current selection
            while True:
                proceed_choice = menu_navigation(
                    ["Shuffle options", "Time options", "Proceed", "Back", "Cancel"],
                    "Select an option:"
                )

                if proceed_choice == 1:
                    # Shuffle options submenu
                    shuffle_choice = menu_navigation(
                        ["Shuffle the order of selected playlists (grouped by playlists)", 
                         "Shuffle tracks (not grouped)", "No shuffle", "Back"],
                        "Select an option:"
                    )
                    shuffle_option = {
                        1: "Shuffle playlists",
                        2: "Shuffle tracks",
                        3: "No shuffle"
                    }.get(shuffle_choice, shuffle_option)

                elif proceed_choice == 2:
                    # Time options submenu
                    time_choice = menu_navigation(
                        ["Set time for each playlist", "Set total time", 
                         "Not specified (use full playlists)", "Back"],
                        "Select an option:" 
                    )
                    if time_choice == 1:
                        # Set time for each playlist
                        time_str = input("Insert a time (hh:mm:ss): ").strip()
                        time_ms = parse_time_input(time_str)
                        if time_ms is None:
                            continue
                        variation_str = input("Set the acceptable +- variation in minutes (e.g. 2): ").strip()
                        variation_ms = get_variation_input(variation_str)
                        if variation_ms is None:
                            continue
                        time_option = f"Each playlist: {time_str} ± {variation_str} minutes"

                    elif time_choice == 2:
                        # Set total time
                        time_str = input("Insert a time (hh:mm:ss): ").strip()
                        time_ms = parse_time_input(time_str)
                        if time_ms is None:
                            continue
                        variation_str = input("Set the acceptable +- variation in minutes (e.g. 2): ").strip()
                        variation_ms = get_variation_input(variation_str)
                        if variation_ms is None:
                            continue
                        time_option = f"Total time: {time_str} ± {variation_str} minutes"

                    elif time_choice == 3:
                        time_option = "Not specified"

                elif proceed_choice == 3:
                    # Confirm playlist creation
                    print(f"Selected playlists: {selected_playlists}")
                    print(f"Shuffle option: {shuffle_option}")
                    print(f"Time option: {time_option}")
                    confirm = input("Confirm new playlist? (y/n): ").strip().lower()
                    if confirm == "y":
                        # Call playlist creation logic
                        print("Playlist created with the selected options.")
                        break
                    elif confirm == "n":
                        continue

                elif proceed_choice == 4:
                    break  # Return to the previous menu

                elif proceed_choice == 5:
                    return  # Cancel operation

        elif main_choice == 5:
            break  # Return to the previous step

        elif main_choice == 6:
            return  # Exit to the main menu