import logging
import sys
from typing import List, Dict, Any

from playlistarchitect.utils.logging_utils import setup_logging
from playlistarchitect.auth.spotify_auth import initialize_spotify_client, clear_cached_token, force_immediate_authentication, get_spotify_client
from playlistarchitect.operations.retrieve_playlists_table import (
    get_all_playlists_with_details,
    save_playlists_to_file,
    load_playlists_from_file,
    display_playlists_table,
)
from playlistarchitect.operations.backup import backup_options
from playlistarchitect.operations.new_playlist import create_new_playlist
from playlistarchitect.operations.remove_from_library import remove_playlists_from_library
from playlistarchitect.utils.helpers import menu_navigation
from playlistarchitect.utils.constants import BACK_OPTION

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    """
    Main function for the Playlist Architect application.
    Initializes the Spotify client, loads playlists, and provides a menu for user interaction.
    """
    clear_at_exit: bool = False
    
    try:
        # Initialize Spotify client
        initialize_spotify_client()
        print("\nWelcome to Playlist Architect!")
    except RuntimeError as e:
        logger.error(f"Failed to initialize Spotify client: {e}")
        sys.exit(1)  # Exit the program if Spotify client initialization fails

    playlists: List[Dict[str, Any]] = load_playlists_from_file()

    try:
        while True:
            # Define the main menu
            main_menu: Dict[str, str] = {
                "1": "Create a new playlist",
                "2": "Remove playlists from Your Library",
                "3": "Show cached playlists",
                "4": "Refresh playlists data",
                "5": "Backup options",
                "6": "Clear Spotify authentication",
                "7": "Exit",
            }

            choice: str = menu_navigation(main_menu, prompt="Select an action:")

            if choice == "1":
                create_new_playlist(playlists)
                save_playlists_to_file(playlists)
            elif choice == "2":
                sp = get_spotify_client()
                remove_playlists_from_library(sp, playlists)
                save_playlists_to_file(playlists)
            elif choice == "3":
                display_playlists_table(playlists, "Showing cached playlists")
            elif choice == "4":
                playlists = get_all_playlists_with_details()
                save_playlists_to_file(playlists)
                print("Playlists data refreshed.")
            elif choice == "5":
                backup_options(playlists)
                save_playlists_to_file(playlists)
 
            if choice == "6":
                # Clear the cached token
                clear_cached_token()                
                print("A new authentication is required to operate a Spotify account.")
                
                # Authentication submenu
                auth_menu: Dict[str, str] = {
                    "1": "Authenticate now",
                    "2": "Authenticate automatically when necessary",
                }
                sub_choice: str = menu_navigation(auth_menu, prompt="Select an option:")

                if sub_choice == "1":
                    # Attempt immediate authentication
                    if force_immediate_authentication():
                        print("Authentication successful!")
                    else:
                        print("Authentication failed. You may need to manually authenticate later.")
                elif sub_choice == "2":
                    # Do nothing, authentication will happen automatically when needed
                    print("Authentication will occur automatically when needed.")
            elif choice == "7":
                logger.info("Exiting program.")
                break
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        print(f"An unexpected error occurred: {e}")
    finally:
        if clear_at_exit:
            clear_cached_token()
            logger.info("Cached token cleared at exit.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Exiting the application...")
        sys.exit(0)  # Exit gracefully