import json
import logging
from retrieve_playlists_table import display_playlists_table, save_playlists_to_file, format_duration
from spotify_auth import get_spotify_client
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from helpers import assign_temporary_ids
from spotipy.exceptions import SpotifyException

# Configure spotipy logging
logging.getLogger('spotipy').setLevel(logging.ERROR)


sp = get_spotify_client()

def export_playlists(playlists, selected_ids=None):
    """Export selected or all playlists to a file."""
    # Assign temporary IDs before filtering
    assign_temporary_ids(playlists)
    
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
                fields="items.track.uri,items.track.name,items.track.artists,items.track.album.name,items.track.duration_ms,next",
                additional_types=["track"]
            )
            for track in tracks_response['items']:
                if track['track']:
                    tracks.append({
                        "uri": track['track']['uri'],
                        "name": track['track']['name'],
                        "artists": [artist['name'] for artist in track['track']['artists']],
                        "album": track['track']['album']['name'],
                        "duration_ms": track['track'].get('duration_ms', 0)
                    })
            if not tracks_response['next']:
                break
            track_offset += 100
        playlist['tracks'] = tracks

    # Remove the custom 'id' key from each playlist
    for playlist in playlists_to_export:
        if 'id' in playlist:
            del playlist['id']

    # Prompt for file name and path using Tkinter
    print("Initializing Tkinter...")
    root = Tk()
    root.withdraw()  # Hide the root window
    root.attributes('-topmost', True)  # Keep the root window on top
    root.lift()  # Bring the root window to the front
    root.focus_force()  # Focus on the root window

    print("Opening file dialog...")
    file_path = asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, "w") as file:
            json.dump(playlists_to_export, file, indent=4)
        print(f"Playlists exported successfully to {file_path}")
    else:
        print("Export canceled.")
    root.destroy()

def import_playlists(playlists, option):
    """Import playlists from a file."""
    root = None
    try:
        print("Initializing Tkinter...")
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()

        print("Opening file dialog...")
        file_path = askopenfilename(title="Select a backup file", filetypes=[("JSON files", "*.json")])

        if not file_path:
            print("No file selected.")
            return

        print(f"Selected file: {file_path}")

        # Load the playlists from the file
        with open(file_path, "r") as file:
            imported_playlists = json.load(file)

        print("Playlists loaded from file.")

        # Debug: Print structure of first playlist
        if imported_playlists:
            print(f"Debug: Keys in first playlist: {imported_playlists[0].keys()}")

        # Recreate or follow playlists in the connected account
        total_tracks = 0
        total_duration_ms = 0

        for playlist in imported_playlists:
            if option == "1":
                recreate_playlist(sp, playlist)
            elif option == "2":
                if not follow_playlist(sp, playlist):
                    recreate_playlist(sp, playlist)
            elif option == "3":
                follow_playlist(sp, playlist)

            # Use the duration field if it exists, otherwise calculate from tracks
            if 'duration' in playlist:
                # Convert HH:MM:SS to milliseconds
                time_parts = playlist['duration'].split(':')
                duration_ms = (int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])) * 1000
                total_duration_ms += duration_ms
            else:
                # Fallback to tracks duration_ms
                playlist_duration = sum(track.get('duration_ms', 0) for track in playlist['tracks'])
                total_duration_ms += playlist_duration

            total_tracks += len(playlist['tracks'])

        # Update the cached playlists data
        playlists.extend(imported_playlists)
        save_playlists_to_file(playlists)

        # Format and display total duration
        formatted_duration = format_duration(total_duration_ms)
        print(f"Import complete with:\n{len(imported_playlists)} playlists, {total_tracks} tracks, {formatted_duration} hours total.")
    except Exception as e:
        print(f"Error during import: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if root:
            root.destroy()
                         
def recreate_playlist(sp, playlist):
    """Recreate a playlist in the user's account."""
    new_playlist = sp.user_playlist_create(sp.current_user()['id'], playlist['name'], public=True)
    track_uris = [track['uri'] for track in playlist['tracks'] if 'uri' in track]
    if track_uris:
        for i in range(0, len(track_uris), 100):
            sp.playlist_add_items(new_playlist['id'], track_uris[i:i+100])
        print(f"Playlist '{playlist['name']}' created with {len(track_uris)} tracks.")
    else:
        print(f"Playlist '{playlist['name']}' has no tracks to add.")

def follow_playlist(sp, playlist):
    """Attempt to follow a playlist. Return True if successful, False otherwise."""
    try:
        # Catch specific Spotipy exception        
        try:
            sp.current_user_follow_playlist(playlist['spotify_id'])
            print(f"Followed playlist '{playlist['name']}'")
            return True
        except SpotifyException as e:
            if e.http_status == 404:
                print(f"Could not follow playlist '{playlist['name']}': Playlist not found or private.")
            else:
                print(f"Could not follow playlist '{playlist['name']}': {e.msg}")
            return False
    except Exception as e:
        print(f"Could not follow playlist '{playlist['name']}': {str(e)}")
        return False

def backup_options(playlists):
    """Display backup options menu."""
    while True:
        print("\nSelect an option:")
        print("1. Export")
        print("2. Import")
        print("3. Main menu")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            print("\nSelect an option:")
            print("1. A selection of saved/created playlists.")
            print("2. All the saved/created playlists.")

            export_choice = input("Enter your choice: ").strip()

            if export_choice == "1":
                assign_temporary_ids(playlists)  # Assign temporary IDs before displaying
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
            print("\nSelect an option:")
            print("1. Recreate all playlists (you will be the author)")
            print("2. Add original playlists to Your Library if possible and recreate the rest")
            print("3. Add original playlists to Your Library and ignore the rest")

            import_choice = input("Enter your choice: ").strip()

            if import_choice in ["1", "2", "3"]:
                import_playlists(playlists, import_choice)
            else:
                print("Invalid option. Please try again.")
        elif choice == "3":
            break
        else:
            print("Invalid option. Please try again.")