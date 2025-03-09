import logging
from playlistarchitect.operations.retrieve_playlists_table import display_playlists_table, save_playlists_to_file
from playlistarchitect.utils.helpers import menu_navigation
from playlistarchitect.utils.constants import Option, Prompt, Message

logger = logging.getLogger(__name__)

def remove_playlists_from_library(sp, playlists):
    """Main menu for removing playlists from the library."""
    while True:
        main_menu = {
            "1": "Remove a selection of playlists",
            "2": "Remove all playlists",
            "b": Option.BACK.value,
        }
        choice = menu_navigation(main_menu, prompt=Prompt.SELECT.value)

        if choice == "1":
            remove_selected_playlists(sp, playlists)
            return  # Return to main menu after removing selected playlists
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
                return  # Return to main menu after removing all playlists
            elif confirm != "n":
                print(Message.INVALID_INPUT_YN.value)
        elif choice == "b":
            return  # Return to main menu if 'b' is selected

def remove_selected_playlists(sp, playlists):
    """Remove specific playlists from the library."""
    selected_playlists = []  # Track selected playlists
    selected_ids = set()  # Track selected playlist IDs

    while True:
        # Pass selected_ids to display_playlists_table
        display_playlists_table(playlists, "Showing cached playlists", selected_ids=selected_ids, show_selection_column=True)

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
            selected_ids = {int(x.strip()) for x in selected_input.split(",")}
            selected_playlists = [p for p in playlists if p["id"] in selected_ids]  # Correctly filter by ID
        except ValueError:
            print(Message.INVALID_INPUT_ID.value)
            continue

        while True:
            selection_menu = {
                "1": "Show selected playlists data",
                "2": "Edit selection",
                "3": "Remove selected playlists from Your Library",
                "b": Option.BACK.value,
            }
            sub_choice = menu_navigation(selection_menu, prompt="What do you want to do with this selection?")

            if sub_choice == "1":
                # Pass selected_ids to display_playlists_table
                display_playlists_table(selected_playlists, "Showing selected playlists", selected_ids=selected_ids, show_selection_column=False)
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
    selected_ids = {p["id"] for p in selected_playlists}  # Get current selected IDs

    while True:
        edit_menu = {
            "1": "Add more playlists to the selection",
            "2": "Remove one or more playlists from the selection",
            "b": Option.BACK.value,
        }
        choice = menu_navigation(edit_menu, prompt="Edit selection:")

        if choice == "1":
            # Pass selected_ids to display_playlists_table
            display_playlists_table(playlists, "Showing cached playlists", selected_ids=selected_ids, show_selection_column=True)
            try:
                new_ids = input("Enter playlist IDs to add (comma-separated): ").strip()
                new_ids = {int(x.strip()) for x in new_ids.split(",")}
                selected_ids.update(new_ids)  # Add new IDs to the selection
                selected_playlists.extend([p for p in playlists if p["id"] in new_ids])
            except ValueError:
                print(Message.INVALID_INPUT_ID.value)
        elif choice == "2":
            # Pass selected_ids to display_playlists_table
            display_playlists_table(selected_playlists, "Showing selected playlists", selected_ids=selected_ids, show_selection_column=False)
            try:
                remove_ids = input("Enter playlist IDs to remove from the selection (comma-separated): ").strip()
                remove_ids = {int(x.strip()) for x in remove_ids.split(",")}
                selected_ids.difference_update(remove_ids)  # Remove IDs from the selection
                selected_playlists[:] = [p for p in selected_playlists if p["id"] not in remove_ids]
            except ValueError:
                print(Message.INVALID_INPUT_ID.value)
        elif choice == "b":
            return