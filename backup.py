import json
import os
from retrieve_playlists_table import display_playlists_table
from spotify_auth import sp

def export_playlists(playlists, selected_ids=None):
    """Export selected or all playlists to a file."""
    if selected_ids:
        playlists_to_export = [playlist for playlist in playlists if playlist['id'] in selected_ids]
    else:
        playlists_to_export = playlists

    # Fetch track information for each playlist
    for playlist in playlists_to_export:
        print(f'Backing up "{playlist["name"]}"...')
        playlist_id = playlist['spotify_id']
        tracks = []
        track_offset = 0
        while True:
            tracks_response = sp.playlist_items(
                playlist_id,
                offset=track_offset,
                fields="items.track.uri,items.track.name,items.track.artists,items.track.album.name",
                additional_types=["track"]
            )
            for track in tracks_response['items']:
                if track['track']:
                    tracks.append({
                        "uri": track['track']['uri'],
                        "name": track['track']['name'],
                        "artists": [artist['name'] for artist in track['track']['artists']],
                        "album": track['track']['album']['name']
                    })
            if 'next' not in tracks_response or not tracks_response['next']:
                break
            track_offset += 100
        playlist['tracks'] = tracks

    # Remove the custom 'id' key from each playlist
    for playlist in playlists_to_export:
        if 'id' in playlist:
            del playlist['id']

    # Prompt for file name and path
    file_name = input("Enter the name for the backup file (without extension): ").strip()
    default_path = os.path.join(os.getcwd(), "Backups")
    os.makedirs(default_path, exist_ok=True)
    file_path = input(f"Enter the path to save the file (default: {default_path}): ").strip() or default_path
    full_path = os.path.join(file_path, f"{file_name}.json")

    # Save the playlists to the file
    with open(full_path, "w") as file:
        json.dump(playlists_to_export, file, indent=4)
    print(f"Playlists exported successfully to {full_path}")

def import_playlists():
    """Import playlists from a file."""
    from tkinter import Tk
    from tkinter.filedialog import askopenfilename

    Tk().withdraw()  # Hide the root window
    file_path = askopenfilename(title="Select a backup file", filetypes=[("JSON files", "*.json")])

    if not file_path:
        print("No file selected.")
        return

    # Load the playlists from the file
    with open(file_path, "r") as file:
        imported_playlists = json.load(file)

    # Recreate playlists in the connected account
    existing_playlists = sp.current_user_playlists(limit=50)['items']
    existing_playlists_names = {playlist['name']: playlist for playlist in existing_playlists}

    for playlist in imported_playlists:
        if playlist['name'] in existing_playlists_names:
            existing_playlist = existing_playlists_names[playlist['name']]
            existing_tracks = sp.playlist_tracks(existing_playlist['id'])['items']
            existing_track_uris = [track['track']['uri'] for track in existing_tracks]

            imported_track_uris = [track['uri'] for track in playlist['tracks']]
            if existing_track_uris == imported_track_uris:
                print(f"Playlist '{playlist['name']}' already exists with the same tracks. Skipping.")
                continue

        # Create the playlist
        new_playlist = sp.user_playlist_create(sp.current_user()['id'], playlist['name'], public=True)
        sp.playlist_add_items(new_playlist['id'], [track['uri'] for track in playlist['tracks']])
        print(f"Playlist '{playlist['name']}' created with {len(playlist['tracks'])} tracks.")

    print("Playlists imported successfully.")

def backup_options(playlists):
    """Display backup options menu."""
    while True:
        print("\nSelect an option:")
        print("1. Export")
        print("2. Import")
        print("3. Main menu")

        choice = input("Enter your choice (1/2/3): ").strip()

        if choice == "1":
            print("\nSelect an option:")
            print("1. A selection of saved/created playlists.")
            print("2. All the saved/created playlists.")

            export_choice = input("Enter your choice (1/2): ").strip()

            if export_choice == "1":
                # Add temporary 'id' field for display purposes
                for idx, playlist in enumerate(playlists, start=1):
                    playlist['id'] = idx

                display_playlists_table(playlists)

                # Remove the temporary 'id' field after display
                for playlist in playlists:
                    if 'id' in playlist:
                        del playlist['id']

                selected_ids = input("Select the ID's of the playlists to export (comma-separated): ").strip().split(",")
                selected_ids = [int(x.strip()) for x in selected_ids]
                export_playlists(playlists, selected_ids)
            elif export_choice == "2":
                export_playlists(playlists)
            else:
                print("Invalid option. Please try again.")
        elif choice == "2":
            import_playlists()
        elif choice == "3":
            break
        else:
            print("Invalid option. Please try again.")