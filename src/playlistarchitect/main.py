import logging
import sys
from playlistarchitect.utils.logging_utils import setup_logging, log_and_print
from playlistarchitect.auth.spotify_auth import get_spotify_client, clear_cached_token
from playlistarchitect.operations.retrieve_playlists_table import (
    get_all_playlists_with_details,
    save_playlists_to_file,
    load_playlists_from_file,
    display_playlists_table,
)
from playlistarchitect.operations.backup import backup_options
from playlistarchitect.operations.new_playlist import create_new_playlist
from playlistarchitect.operations.remove_from_library import remove_playlists_from_library
from playlistarchitect.utils.helpers import assign_temporary_ids, menu_navigation
from playlistarchitect.utils.constants import CANCEL_OPTION, BACK_OPTION

setup_logging()
logger = logging.getLogger(__name__)


def main():
    sp = get_spotify_client()
    try:
        user = sp.current_user()
        print(f"Successfully connected to Spotify as {user['display_name']}")
    except Exception as e:
        log_and_print(f"Error: {str(e)}", level="error")
    clear_at_exit = False
    playlists = load_playlists_from_file()

    while True:
        # Define the main menu using the constants
        main_menu = {
            "1": "Create a new playlist",
            "2": "Remove playlists from Your Library",
            "3": "Show cached playlists",
            "4": "Refresh playlists data",
            "5": "Backup options",
            "6": "Clear Spotify authentication",
            "7": "Exit"
        }

        choice = menu_navigation(main_menu, prompt="Select an action:")

        if choice == "1":
            create_new_playlist(playlists)
            save_playlists_to_file(playlists)
        elif choice == "2":
            remove_playlists_from_library(sp, playlists)
            save_playlists_to_file(playlists)
        elif choice == "3":
            assign_temporary_ids(playlists)
            display_playlists_table(playlists)
            # Remove temporary IDs after display
            for playlist in playlists:
                if "id" in playlist:
                    del playlist["id"]
        elif choice == "4":
            playlists = get_all_playlists_with_details()
            save_playlists_to_file(playlists)
            print("Playlists data refreshed.")
        elif choice == "5":
            backup_options(playlists)
            save_playlists_to_file(playlists)
        elif choice == "6":
            # Submenu for clearing Spotify authentication
            auth_menu = {
                "1": "Clear now (restart authentication immediately)",
                "2": "Clear at exit (next app start)",
                BACK_OPTION: "Return to main menu",
            }
            sub_choice = menu_navigation(auth_menu, prompt="Select an option:")

            if sub_choice == "1":
                clear_cached_token()
                sp = get_spotify_client()
                try:
                    user = sp.current_user()
                    print(f"Successfully connected to Spotify as {user['display_name']}")
                except Exception as e:
                    log_and_print(f"Error: {str(e)}", level="error")
            elif sub_choice == "2":
                clear_at_exit = True
                print("Spotify authentication will be cleared at exit.")
            elif sub_choice == BACK_OPTION:
                continue
        elif choice == "7":
            if clear_at_exit:
                clear_cached_token()
            print("Exiting program.")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting the application...")
        sys.exit(0)  # Exit gracefully
