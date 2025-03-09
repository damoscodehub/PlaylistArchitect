import logging
from typing import List, Dict, Any
from playlistarchitect.auth.spotify_auth import get_spotify_client, initialize_spotify_client
from playlistarchitect.utils.helpers import menu_navigation
from playlistarchitect.utils.new_playlist_helpers import (    
    display_selected_blocks,
    handle_add_playlists,
    handle_remove_playlists,    
    handle_edit_blocks,
    handle_reorder_blocks,
    create_playlist_on_spotify,
)
from playlistarchitect.utils.constants import Prompt, Message

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
    privacy = "public"  # Default privacy setting

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
        if not handle_add_playlists(playlists, selected_playlist_blocks, is_initial_selection=True):
            # If the user entered "b" during the initial selection, return to the main menu
            return    
        
    # Main menu loop
    while True:
        main_menu = {
            "1": "Show selected blocks", 
            "2": "Add blocks to selection",
            "3": "Edit selected blocks",
            "4": "Reorder blocks",
            "5": "Remove blocks from selection",
            "6": "Create the playlist",  # Updated option
            "b": "Back",
            "c": "Cancel",
        }
        main_choice = menu_navigation(main_menu, prompt=Prompt.SELECT.value)

        if main_choice == "1":  # Show selected blocks
            display_selected_blocks(selected_playlist_blocks, playlists)

        elif main_choice == "2":  # Add blocks to selection
            handle_add_playlists(playlists, selected_playlist_blocks)

        elif main_choice == "3":  # Edit selected blocks
            handle_edit_blocks(selected_playlist_blocks, playlists)

        elif main_choice == "4":  # Reorder blocks
            if handle_reorder_blocks(selected_playlist_blocks, playlists):
                return  # Cancel the whole process if the user chose to cancel

        elif main_choice == "5":  # Remove blocks from selection
            handle_remove_playlists(selected_playlist_blocks, playlists)

        elif main_choice == "6":  # Create the playlist
            # Display the playlist summary
            print("\nThe following playlist will be created:")
            display_selected_blocks(selected_playlist_blocks, playlists)
            print(f"Name: {playlist_name}")
            print(f"Privacy: {privacy}")

            # Prompt for confirmation
            while True:
                confirm = input("\nConfirm? (y/n): ").strip().lower()
                if confirm in ['y', 'n']:
                    break
                print(Message.INVALID_INPUT_YN.value)

            if confirm == 'y':
                # Create the playlist
                create_playlist_on_spotify(sp, selected_playlist_blocks, playlist_name, privacy, playlists)
                return  # Exit the function after creating the playlist
            else:
                # If the user selects 'n', go back to the main menu
                continue

        elif main_choice in ["b", "c"]:
            return

if __name__ == "__main__":
    # Example usage
    playlists = []  # Replace with actual playlists data
    create_new_playlist(playlists)