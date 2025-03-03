import logging
from typing import List, Dict, Any
from playlistarchitect.auth.spotify_auth import get_spotify_client, initialize_spotify_client
from playlistarchitect.utils.helpers import menu_navigation
from playlistarchitect.utils.new_playlist_helpers import (    
    process_playlist_selection,
    display_selected_blocks,
    validate_playlist_blocks,
    display_playlist_selection_table,
    handle_add_playlists,
    handle_remove_playlists,    
    handle_proceed_menu,
    handle_edit_blocks,
    parse_playlist_selection,
)

logger = logging.getLogger(__name__)

def create_new_playlist(playlists: List[Dict[str, Any]]) -> None:
    """
    Handle the creation of a new playlist with advanced options.
    
    Parameters:
    playlists (List[Dict]): List of all playlists
    """
    # Ensure Spotify client is initialized before calling the client
    initialize_spotify_client()
    sp = get_spotify_client()

    # Initialize variables
    selected_playlist_blocks = []
    shuffle_option = "No shuffle"
    time_option = "Not specified"

    # Get basic playlist details
    playlist_name = input("Enter a name for the new playlist: ").strip()
    if not playlist_name:
        print("Playlist name cannot be empty.")
        return

    # Privacy menu
    privacy_menu = {"1": "Public", "2": "Private"}
    privacy_choice = menu_navigation(privacy_menu, prompt="Choose privacy:")
    privacy = "public" if privacy_choice == "1" else "private"

    # Initial playlist selection
    while not selected_playlist_blocks:
        handle_add_playlists(playlists, selected_playlist_blocks)
    
    # Main menu loop
    while True:
        main_menu = {
            "1": "Show selected blocks", 
            "2": "Add blocks to selection",
            "3": "Remove blocks from selection",
            "4": "Edit selected blocks",
            "5": "Proceed with current selection",
            "b": "Back",
            "c": "Cancel",
        }
        main_choice = menu_navigation(main_menu, prompt="Select an option:")

        if main_choice == "1":
            display_selected_blocks(selected_playlist_blocks, playlists)

        elif main_choice == "2":
            handle_add_playlists(playlists, selected_playlist_blocks)

        elif main_choice == "3":
            handle_remove_playlists(selected_playlist_blocks, playlists)

        elif main_choice == "4":  # New option
            handle_edit_blocks(selected_playlist_blocks, playlists)

        elif main_choice == "5":  # Updated option
            if handle_proceed_menu(
                selected_playlist_blocks, 
                playlist_name, 
                privacy, 
                shuffle_option, 
                time_option,
                sp,
                playlists
            ):
                return  # Playlist creation was successful or user canceled

        elif main_choice in ["b", "c"]:
            return

if __name__ == "__main__":
    # Example usage
    playlists = []  # Replace with actual playlists data
    create_new_playlist(playlists)