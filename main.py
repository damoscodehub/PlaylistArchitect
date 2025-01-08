import os
from retrieve_playlists_table import display_playlists_table, get_all_playlists_with_details, save_playlists_to_file, load_playlists_from_file
from new_playlist import create_new_playlist
from backup import backup_options
from spotify_auth import clear_cached_token, get_spotify_client

def main():
    # Authenticate with Spotify
    sp = get_spotify_client()
    try:
        user = sp.current_user()
        print(f"Successfully connected to Spotify as {user['display_name']}")
    except Exception as e:
        print(f"Error: {str(e)}")
        return

    # Load playlists from file
    playlists = load_playlists_from_file()

    while True:
        # Display main menu
        print("\nSelect an option:")
        print("1. Create a new playlist")
        print("2. Show cached playlists")
        print("3. Refresh playlists data")
        print("4. Backup options")
        print("5. Clear Spotify authentication")
        print("6. Exit")

        choice = input("Enter your choice (1/2/3/4/5/6): ").strip()

        if choice == "1":
            create_new_playlist(playlists)  # Call the new playlist creation process
        elif choice == "2":
            display_playlists_table(playlists)  # Call the function to display all playlists
        elif choice == "3":
            playlists = get_all_playlists_with_details()
            save_playlists_to_file(playlists)
            print("Playlists data refreshed.")
        elif choice == "4":
            backup_options(playlists)  # Call the backup options menu
        elif choice == "5":
            clear_cached_token()  # Clear the cached Spotify authentication token
            sp = get_spotify_client()  # Re-authenticate with Spotify
            try:
                user = sp.current_user()
                print(f"Successfully connected to Spotify as {user['display_name']}")
            except Exception as e:
                print(f"Error: {str(e)}")
        elif choice == "6":
            print("Exiting program.")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()