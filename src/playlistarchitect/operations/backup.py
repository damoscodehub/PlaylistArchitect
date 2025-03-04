import json
import logging
from tkinter import Tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from playlistarchitect.utils.logging_utils import setup_logging
from playlistarchitect.operations.retrieve_playlists_table import (
    display_playlists_table,
    save_playlists_to_file,
)
from playlistarchitect.auth.spotify_auth import get_spotify_client
from playlistarchitect.utils.helpers import menu_navigation
from playlistarchitect.utils.constants import BACK_OPTION, CANCEL_OPTION
from spotipy.exceptions import SpotifyException
from playlistarchitect.utils.formatting_helpers import format_duration

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

def create_focused_tk_window():
    """
    Create a Tkinter window with enhanced focus settings.
    
    This function creates a Tkinter window that is designed to appear 
    in the foreground with focus, even on the first attempt.
    
    Returns:
        Tk: A configured Tkinter root window
    """
    import tkinter as tk
    
    # Create root window
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Try multiple focus-related techniques
    root.attributes("-topmost", True)  # Bring to top
    root.attributes("-toolwindow", False)  # Ensure it's not minimized
    root.deiconify()  # Show briefly to trigger focus
    root.withdraw()  # Hide again, but now initialized
    
    return root

def export_playlists(playlists, selected_ids=None):
    """
    Export selected or all playlists to a file.
    Args:
        playlists (list): List of playlists to export.
        selected_ids (list, optional): List of selected playlist IDs to export.
    """
    sp = get_spotify_client()
    failed_playlists = []
    total_tracks = 0
    total_duration_ms = 0
    successful_playlists = 0

    if selected_ids:
        playlists_to_export = [playlist for playlist in playlists if playlist["id"] in selected_ids]
    else:
        playlists_to_export = playlists

    # Keep track of playlist names to detect duplicates
    playlist_names = {}

    # Fetch track information for each playlist
    for playlist in playlists_to_export:
        try:
            playlist_name = playlist["name"]
            if playlist_name in playlist_names:
                playlist_names[playlist_name] += 1
                logger.warning(f'Found duplicate playlist "{playlist_name}" (occurrence {playlist_names[playlist_name]})')
            else:
                playlist_names[playlist_name] = 1

            print(f'Backing up "{playlist_name}"...')
            playlist_id = playlist["spotify_id"]
            tracks = []
            track_offset = 0
            
            while True:
                try:
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
                    
                except SpotifyException as e:
                    if e.http_status == 404:
                        error_msg = f'Playlist "{playlist_name}" (ID: {playlist_id}) not found or inaccessible'
                        if playlist_names[playlist_name] > 1:
                            error_msg += f" (duplicate {playlist_names[playlist_name]})"
                        logger.error(error_msg)
                        failed_playlists.append((playlist_name, "Playlist not found or inaccessible"))
                    else:
                        logger.error(f'Error fetching tracks for playlist "{playlist_name}": {str(e)}')
                        failed_playlists.append((playlist_name, f"Error: {str(e)}"))
                    break
                    
            playlist["tracks"] = tracks
            if tracks:  # Only count if tracks were successfully retrieved
                total_tracks += len(tracks)
                total_duration_ms += sum(track["duration_ms"] for track in tracks)
                successful_playlists += 1
            
        except Exception as e:
            logger.error(f'Unexpected error processing playlist "{playlist["name"]}": {str(e)}')
            failed_playlists.append((playlist["name"], f"Unexpected error: {str(e)}"))
            continue

    # Remove the custom "id" key from each playlist
    for playlist in playlists_to_export:
        if "id" in playlist:
            del playlist["id"]

    # Only proceed with file export if there are playlists to export
    if not all(playlist.get("tracks") == [] for playlist in playlists_to_export):
        import tkinter as tk
        from tkinter.filedialog import asksaveasfilename
        
        # Create Tkinter root window
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.iconify()   # Minimize to ensure it doesn't block
        
        # Use after method to show file dialog
        def show_save_dialog():
            file_path = asksaveasfilename(
                defaultextension=".json", 
                filetypes=[("JSON files", "*.json")]
            )
            
            # Process the file path
            if file_path:
                with open(file_path, "w") as file:
                    json.dump(playlists_to_export, file, indent=4)
                
                # Calculate total duration in hours, minutes, and seconds
                total_seconds = total_duration_ms // 1000
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                
                print(f"\nPlaylists exported successfully to {file_path}")
                print(f"Total exported: {successful_playlists} playlists, {total_tracks} tracks, "
                      f"{hours:02d}:{minutes:02d}:{seconds:02d} playback time")
                
                # Only show failed playlists if the export was completed
                if failed_playlists:
                    print("\nThe following playlists could not be backed up:")
                    for name, reason in failed_playlists:
                        print(f"- {name}: {reason}")
            else:
                print("\nExport canceled.")
            
            # Destroy the root window
            root.destroy()
        
        # Schedule the dialog to show immediately
        root.after(50, show_save_dialog)
        
        # Start the Tkinter event loop
        root.mainloop()

def import_playlists(playlists, option):
    """
    Import playlists from a file.
    Args:
        playlists (list): List of existing playlists.
        option (str): Import option (e.g., recreate, follow, etc.).
    """
    sp = get_spotify_client()  # Retrieve Spotify client within the function
    
    import tkinter as tk
    from tkinter.filedialog import askopenfilename
    
    # Create Tkinter root window
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.iconify()   # Minimize to ensure it doesn't block
    
    # Use after method to show file dialog
    def show_open_dialog():
        file_path = askopenfilename(
            title="Select a backup file", 
            filetypes=[("JSON files", "*.json")]
        )
        
        if not file_path:
            print("No file selected.")
            root.destroy()
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
        
        # Destroy the root window
        root.destroy()
    
    # Schedule the dialog to show immediately
    root.after(50, show_open_dialog)
    
    # Start the Tkinter event loop
    root.mainloop()
        
def recreate_playlist(sp, playlist):
    """
    Recreate a playlist in the user's account.
    Args:
        sp: Spotify client instance.
        playlist (dict): Playlist data to recreate.
    Returns:
        bool: True if successful, False otherwise.
    """
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
    """
    Attempt to follow a playlist.
    Args:
        sp: Spotify client instance.
        playlist (dict): Playlist data to follow.
    Returns:
        bool: True if successful, False otherwise.
    """
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
    """
    Display backup options menu.
    Args:
        playlists (list): List of playlists to display in the menu.
    """
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
                display_playlists_table(playlists, "Showing cached playlists", show_selection_column=False)
                try:
                    selected_ids = input("Select playlist IDs to export (comma-separated): ").strip()
                    selected_ids = [int(x.strip()) for x in selected_ids.split(",")]
                    export_playlists(playlists, selected_ids)
                    return  # Return to main menu after exporting
                except ValueError:
                    print("Invalid input. Please enter numeric playlist IDs.")
            elif export_choice == "2":
                export_playlists(playlists)
                return  # Return to main menu after exporting
            elif export_choice == "b":
                continue  # Stay in the backup menu

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
                return  # Return to main menu after importing
            elif import_choice == "b":
                continue  # Stay in the backup menu

        elif choice == "c":  # Handle CANCEL_OPTION
            break  # Exit the backup options loop and return to the main menu