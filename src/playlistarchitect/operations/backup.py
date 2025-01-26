import json
import logging
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from playlistarchitect.utils.logging_utils import setup_logging
from playlistarchitect.operations.retrieve_playlists_table import (
    display_playlists_table,
    save_playlists_to_file,
    format_duration,
)
from playlistarchitect.auth.spotify_auth import get_spotify_client
from playlistarchitect.utils.helpers import assign_temporary_ids, menu_navigation
from playlistarchitect.utils.constants import BACK_OPTION, CANCEL_OPTION
from spotipy.exceptions import SpotifyException

setup_logging()
logger = logging.getLogger(__name__)

sp = get_spotify_client()


def export_playlists(playlists, selected_ids=None):
    """Export selected or all playlists to a file."""
    assign_temporary_ids(playlists)

    if selected_ids:
        playlists_to_export = [playlist for playlist in playlists if playlist["id"] in selected_ids]
    else:
        playlists_to_export = playlists

    # Fetch track information for each playlist
    for playlist in playlists_to_export:
        print(f'Backing up "{playlist["name"]}"...')
        playlist_id = playlist["spotify_id"]
        tracks = []
        track_offset = 0
        while True:
            tracks_response = sp.playlist_items(
                playlist_id,
                offset=track_offset,
                fields="items.track.uri,items.track.name,items.track.artists,items.track.album.name,items.track.duration_ms,next",
                additional_types=["track"],
            )
            for track in tracks_response["items"]:
                if track["track"]:
                    tracks.append(
                        {
                            "uri": track["track"]["uri"],
                            "name": track["track"]["name"],
                            "artists": [artist["name"] for artist in track["track"]["artists"]],
                            "album": track["track"]["album"]["name"],
                            "duration_ms": track["track"].get("duration_ms", 0),
                        }
                    )
            if not tracks_response["next"]:
                break
            track_offset += 100
        playlist["tracks"] = tracks

    # Remove the custom "id" key from each playlist
    for playlist in playlists_to_export:
        if "id" in playlist:
            del playlist["id"]

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

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
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = askopenfilename(title="Select a backup file", filetypes=[("JSON files", "*.json")])
    if not file_path:
        print("No file selected.")
        return

    with open(file_path, "r") as file:
        imported_playlists = json.load(file)

    print("Playlists loaded from file.")
    successful_imports = []
    existing_ids = {pl["spotify_id"] for pl in playlists if "spotify_id" in pl}

    for playlist in imported_playlists:
        if playlist["spotify_id"] in existing_ids:
            print(f"Playlist '{playlist['name']}' already in cache - skipping")
            continue

        success = False
        if option == "1":
            success = recreate_playlist(sp, playlist)
        elif option == "2":
            success = follow_playlist(sp, playlist) or recreate_playlist(sp, playlist)
        elif option == "3":
            success = follow_playlist(sp, playlist)

        if success:
            successful_imports.append(playlist)
            existing_ids.add(playlist["spotify_id"])

    playlists.extend(successful_imports)
    save_playlists_to_file(playlists)

    formatted_duration = format_duration(
        sum(track.get("duration_ms", 0) for pl in successful_imports for track in pl["tracks"])
    )
    print(f"Import complete: {len(successful_imports)} new playlists added, total duration {formatted_duration}.")
    root.destroy()


def recreate_playlist(sp, playlist):
    """Recreate a playlist in the user's account."""
    try:
        new_playlist = sp.user_playlist_create(sp.current_user()["id"], playlist["name"], public=True)
        track_uris = [track["uri"] for track in playlist["tracks"] if "uri" in track]
        if track_uris:
            for i in range(0, len(track_uris), 100):
                sp.playlist_add_items(new_playlist["id"], track_uris[i : i + 100])
            print(f"Playlist '{playlist['name']}' created with {len(track_uris)} tracks.")
        else:
            print(f"Playlist '{playlist['name']}' has no tracks to add.")
        return True
    except Exception as e:
        print(f"Failed to recreate playlist '{playlist['name']}': {str(e)}")
        return False


def follow_playlist(sp, playlist):
    """Attempt to follow a playlist. Return True if successful, False otherwise."""
    try:
        sp.current_user_follow_playlist(playlist["spotify_id"])
        print(f"Followed playlist '{playlist['name']}'")
        return True
    except SpotifyException as e:
        if e.http_status == 404:
            print(f"Could not follow playlist '{playlist['name']}': Playlist not found or private.")
        else:
            print(f"Could not follow playlist '{playlist['name']}': {e.msg}")
        return False


def backup_options(playlists):
    """Display backup options menu."""
    while True:
        # Define the backup menu
        backup_menu = {
            "1": "Export playlists",
            "2": "Import playlists",
            "c": CANCEL_OPTION,  # Exit to main menu
        }

        choice = menu_navigation(backup_menu, prompt="Select a backup option:")

        if choice == "1":
            # Export menu
            export_menu = {
                "1": "A selection of saved/created playlists",
                "2": "All saved/created playlists",
                "b": BACK_OPTION,  # Return to backup menu
            }

            export_choice = menu_navigation(export_menu, prompt="Select export option:")

            if export_choice == "1":
                assign_temporary_ids(playlists)
                display_playlists_table(playlists)
                try:
                    selected_ids = input("Select playlist IDs to export (comma-separated): ").strip()
                    selected_ids = [int(x.strip()) for x in selected_ids.split(",")]
                    export_playlists(playlists, selected_ids)
                except ValueError:
                    print("Invalid input. Please enter numeric playlist IDs.")
            elif export_choice == "2":
                export_playlists(playlists)
            elif export_choice == "b":
                continue

        elif choice == "2":
            # Import menu
            import_menu = {
                "1": "Recreate all playlists (you will be the author)",
                "2": "Add original playlists to Your Library and recreate the rest",
                "3": "Add original playlists to Your Library and ignore the rest",
                "b": BACK_OPTION,  # Return to backup menu
            }

            import_choice = menu_navigation(import_menu, prompt="Select import option:")

            if import_choice in ["1", "2", "3"]:
                import_playlists(playlists, import_choice)
            elif import_choice == "b":
                continue

        elif choice == "x":
            break
