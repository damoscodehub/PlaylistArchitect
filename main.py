import os
from retrieve_playlists_table import display_playlists_table, get_all_playlists_with_details, save_playlists_to_file, load_playlists_from_file
from new_playlist import create_new_playlist

def main():
    # Load playlists from file
    playlists = load_playlists_from_file()

    while True:
        # Display main menu
        print("\nSelect an option:")
        print("1. Create a new playlist")
        print("2. Show cached playlists")
        print("3. Refresh playlists data")
        print("4. Exit")

        choice = input("Enter your choice (1/2/3/4): ").strip()

        if choice == "1":
            create_new_playlist(playlists)  # Call the new playlist creation process
        elif choice == "2":
            display_playlists_table(playlists)  # Call the function to display all playlists
        elif choice == "3":
            playlists = get_all_playlists_with_details()
            save_playlists_to_file(playlists)
            print("Playlists data refreshed.")
        elif choice == "4":
            print("Exiting program.")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()