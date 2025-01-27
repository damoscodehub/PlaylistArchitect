import logging
from playlistarchitect.operations.retrieve_playlists_table import display_playlists_table, save_playlists_to_file
from playlistarchitect.utils.helpers import assign_temporary_ids, menu_navigation
from playlistarchitect.utils.constants import BACK_OPTION

logger = logging.getLogger(__name__)

def remove_playlists_from_library(sp, playlists):
    """Main menu for removing playlists from the library."""
    while True:
        main_menu = {
            "1": "Remove a selection of playlists",
            "2": "Remove all playlists",
            "b": BACK_OPTION,
        }
        choice = menu_navigation(main_menu, prompt="Select an option:")

        if choice == "1":
            remove_selected_playlists(sp, playlists)
        elif choice == "2":
            confirm = input("Remove all playlists from Your Library? (y/n): ").strip().lower()
            if confirm == "y":
                for playlist in playlists:
                    try:
                        sp.current_user_unfollow_playlist(playlist["spotify_id"])
                        print(f"Unfollowed playlist: {playlist['name']}")
                    except Exception as e:
                        logger.error(f"Error unfollowing playlist {playlist['name']}: {str(e)}")
                playlists.clear()  # Clear all playlists from the cache
                save_playlists_to_file(playlists)  # Update cached playlists data
                print("All playlists removed from Your Library.")
            elif confirm != "n":
                print("Invalid input. Please enter 'y' or 'n'.")
        elif choice == "b":
            return


def remove_selected_playlists(sp, playlists):
    """Remove specific playlists from the library."""
    selected_playlists = []

    while True:
        assign_temporary_ids(playlists)
        display_playlists_table(playlists)

        selected_input = input("Select the IDs of the playlists to remove (comma-separated): ").strip()

        if "-a" in selected_input or "--all" in selected_input:
            confirm = input("Remove all playlists from Your Library? (y/n): ").strip().lower()
            if confirm == "y":
                for playlist in playlists:
                    try:
                        sp.current_user_unfollow_playlist(playlist["spotify_id"])
                        print(f"Unfollowed playlist: {playlist['name']}")
                    except Exception as e:
                        logger.error(f"Error unfollowing playlist {playlist['name']}: {str(e)}")
                playlists.clear()
                save_playlists_to_file(playlists)
                print("All playlists removed from Your Library.")
                return
            else:
                continue

        try:
            selected_ids = [int(x.strip()) for x in selected_input.split(",")]
            selected_playlists = [playlists[idx - 1] for idx in selected_ids]
        except ValueError:
            print("Invalid input. Please enter numeric playlist IDs.")
            continue

        while True:
            selection_menu = {
                "1": "Show selected playlists data",
                "2": "Edit selection",
                "3": "Remove selected playlists from Your Library",
                "b": BACK_OPTION,
            }
            sub_choice = menu_navigation(selection_menu, prompt="What do you want to do with this selection?")

            if sub_choice == "1":
                assign_temporary_ids(selected_playlists)
                display_playlists_table(selected_playlists)
            elif sub_choice == "2":
                edit_selection(selected_playlists, playlists)
            elif sub_choice == "3":
                confirm = input("Are you sure you want to remove the selected playlists from Your Library? (y/n): ").strip().lower()
                if confirm == "y":
                    for playlist in selected_playlists:
                        try:
                            sp.current_user_unfollow_playlist(playlist["spotify_id"])
                            print(f"Unfollowed playlist: {playlist['name']}")
                            playlists.remove(playlist)
                        except Exception as e:
                            logger.error(f"Error unfollowing playlist {playlist['name']}: {str(e)}")
                    save_playlists_to_file(playlists)
                    print("Selected playlists removed from Your Library.")
                    return
            elif sub_choice == "b":
                return

#        # Cleanup temporary IDs
#        for playlist in playlists:
#            if "id" in playlist:
#                del playlist["id"]


def edit_selection(selected_playlists, playlists):
    """Edit the selection of playlists to be removed."""
    while True:
        edit_menu = {
            "1": "Add more playlists to the selection",
            "2": "Remove one or more playlists from the selection",
            "b": BACK_OPTION,
        }
        choice = menu_navigation(edit_menu, prompt="Edit selection:")

        if choice == "1":
            assign_temporary_ids(playlists)
            display_playlists_table(playlists)
            try:
                selected_ids = input("Enter playlist IDs to add (comma-separated): ").strip()
                selected_ids = [int(x.strip()) for x in selected_ids.split(",")]
                for idx in selected_ids:
                    playlist_to_add = playlists[idx - 1]
                    if playlist_to_add not in selected_playlists:
                        selected_playlists.append(playlist_to_add)
            except ValueError:
                print("Invalid input. Please enter numeric playlist IDs.")
        elif choice == "2":
            assign_temporary_ids(selected_playlists)
            display_playlists_table(selected_playlists)
            try:
                selected_ids = input("Enter playlist IDs to remove from the selection (comma-separated): ").strip()
                selected_ids = [int(x.strip()) for x in selected_ids.split(",")]
                selected_playlists[:] = [p for p in selected_playlists if playlists.index(p) + 1 not in selected_ids]
            except ValueError:
                print("Invalid input. Please enter numeric playlist IDs.")
        elif choice == "b":
            return
