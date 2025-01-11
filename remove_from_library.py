from retrieve_playlists_table import display_playlists_table, save_playlists_to_file
from helpers import assign_temporary_ids  # Import the helper function

def remove_playlists_from_library(sp, playlists):
    while True:
        print("\nSelect what you want to remove:")
        print("1. A selection of playlists")
        print("2. All playlists")
        print("3. Back")

        choice = input("Enter your choice (1/2/3): ").strip()

        if choice == "1":
            remove_selected_playlists(sp, playlists)
        elif choice == "2":
            confirm = input("Remove all the playlists from Your Library? (y/n): ").strip().lower()
            if confirm == "y":
                for playlist in playlists:
                    try:
                        print(f"Attempting to unfollow playlist: {playlist['name']} (ID: {playlist['spotify_id']})")
                        sp.current_user_unfollow_playlist(playlist['spotify_id'])
                        print(f"Unfollowed playlist: {playlist['name']}")
                    except Exception as e:
                        print(f"Error unfollowing playlist {playlist['name']}: {str(e)}")
                playlists.clear()  # Clear all playlists from the cache
                save_playlists_to_file(playlists)  # Update cached playlists data
                print("Done.")
                return
            else:
                continue
        elif choice == "3":
            return
        else:
            print("Invalid option. Please try again.")

def remove_selected_playlists(sp, playlists):
    selected_playlists = []

    while True:
        assign_temporary_ids(playlists)  # Assign temporary IDs before displaying
        display_playlists_table(playlists)
        selected_ids = input("Select the ID's of the playlists to remove (comma-separated): ").strip()

        if "-a" in selected_ids or "--all" in selected_ids:
            confirm = input("Remove all the playlists from Your Library? (y/n): ").strip().lower()
            if confirm == "y":
                for playlist in playlists:
                    try:
                        print(f"Attempting to unfollow playlist: {playlist['name']} (ID: {playlist['spotify_id']})")
                        sp.current_user_unfollow_playlist(playlist['spotify_id'])
                        print(f"Unfollowed playlist: {playlist['name']}")
                    except Exception as e:
                        print(f"Error unfollowing playlist {playlist['name']}: {str(e)}")
                playlists.clear()  # Clear all playlists from the cache
                save_playlists_to_file(playlists)  # Update cached playlists data
                print("Done.")
                return
            else:
                continue

        selected_ids = [int(x.strip()) for x in selected_ids.split(",")]

        for idx in selected_ids:
            selected_playlists.append(playlists[idx - 1])

        while True:
            print("\nWhat do you want to do with this selection?")
            print("1. Show selected playlists data")
            print("2. Edit selection")
            print("3. Remove selected playlists from Your Library")
            print("4. Cancel")

            sub_choice = input("Enter your choice (1/2/3/4): ").strip()

            if sub_choice == "1":
                assign_temporary_ids(selected_playlists)  # Assign temporary IDs before displaying
                display_playlists_table(selected_playlists)
                # Remove temporary IDs after display
                for playlist in selected_playlists:
                    if 'id' in playlist:
                        del playlist['id']
            elif sub_choice == "2":
                edit_selection(selected_playlists, playlists)
            elif sub_choice == "3":
                confirm = input("Are you sure you want to remove selected playlists from Your Library? (y/n): ").strip().lower()
                if confirm == "y":
                    for playlist in selected_playlists:
                        try:
                            print(f"Attempting to unfollow playlist: {playlist['name']} (ID: {playlist['spotify_id']})")
                            sp.current_user_unfollow_playlist(playlist['spotify_id'])
                            print(f"Unfollowed playlist: {playlist['name']}")
                            playlists.remove(playlist)  # Remove playlist from the cache
                        except Exception as e:
                            print(f"Error unfollowing playlist {playlist['name']}: {str(e)}")
                    save_playlists_to_file(playlists)  # Update cached playlists data
                    print("Done.")
                    return
                else:
                    continue
            elif sub_choice == "4":
                return
            else:
                print("Invalid option. Please try again.")

        # Remove the temporary 'id' field after display
        for playlist in playlists:
            if 'id' in playlist:
                del playlist['id']

def edit_selection(selected_playlists, playlists):
    while True:
        print("\nEdit selection:")
        print("1. Add more playlists to the selection")
        print("2. Remove one or more playlists from this selection")
        print("3. Back")

        choice = input("Enter your choice (1/2/3): ").strip()

        if choice == "1":
            assign_temporary_ids(playlists)  # Assign temporary IDs before displaying
            display_playlists_table(playlists)
            selected_ids = input("Select the ID's (comma-separated) of the playlists to add to the selection: ").strip()
            selected_ids = [int(x.strip()) for x in selected_ids.split(",")]

            for idx in selected_ids:
                selected_playlists.append(playlists[idx - 1])

            print("Done.")

            # Remove the temporary 'id' field after display
            for playlist in playlists:
                if 'id' in playlist:
                    del playlist['id']
        elif choice == "2":
            assign_temporary_ids(selected_playlists)  # Assign temporary IDs before displaying
            display_playlists_table(selected_playlists)
            selected_ids = input("Select the ID's (comma-separated) of the playlists to remove from the selection: ").strip()
            selected_ids = [int(x.strip()) for x in selected_ids.split(",")]

            for idx in selected_ids:
                selected_playlists.remove(playlists[idx - 1])

            print("Done.")

            # Remove the temporary 'id' field after display
            for playlist in selected_playlists:
                if 'id' in playlist:
                    del playlist['id']
        elif choice == "3":
            return
        else:
            print("Invalid option. Please try again.")