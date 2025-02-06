import logging
import sys
from typing import List, Dict, Any

from playlistarchitect.utils.logging_utils import setup_logging
from playlistarchitect.auth.spotify_auth import initialize_spotify_client, clear_cached_token
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
    try:
        # Initialize Spotify client
        initialize_spotify_client()
        print("\nWelcome to Playlist Architect!")
    except RuntimeError as e:
        logger.error(f"Failed to initialize Spotify client: {e}")
        sys.exit(1)  # Exit the program if Spotify client initialization fails

    clear_at_exit: bool = False
    playlists: List[Dict[str, Any]] = load_playlists_from_file()

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
            remove_playlists_from_library(playlists)
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
        elif choice == "6":
            # Submenu for clearing Spotify authentication
            auth_menu: Dict[str, str] = {
                "1": "Clear now (restart authentication immediately)",
                "2": "Clear at exit (next app start)",
                BACK_OPTION: "Return to main menu",
            }
            sub_choice: str = menu_navigation(auth_menu, prompt="Select an option:")

            if sub_choice == "1":
                clear_cached_token()
                try:
                    initialize_spotify_client()  # Reinitialize the Spotify client
                    logger.info("Spotify client reinitialized successfully.")
                except RuntimeError as e:
                    logger.error(f"Failed to reinitialize Spotify client: {e}")
            elif sub_choice == "2":
                clear_at_exit = True
                logger.info("Spotify authentication will be cleared at exit.")
        elif choice == "7":
            if clear_at_exit:
                clear_cached_token()
            logger.info("Exiting program.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Exiting the application...")
        sys.exit(0)  # Exit gracefully