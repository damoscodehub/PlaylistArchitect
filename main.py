print("Main script started")
from retrieve_playlists_table import display_playlists_table
from new_playlist import create_new_playlist

def main():
    while True:
        # Display main menu
        print("\nSelect an option:")
        print("1. Create a new playlist")
        print("2. Fetch all existing playlists")

        choice = input("Enter your choice (1/2): ").strip()

        if choice == "1":
            create_new_playlist()  # Call the new playlist creation process
        elif choice == "2":
            display_playlists_table()  # Call the function to display all playlists
        else:
            print("Invalid option. Please try again.")

        # Prompt to continue or exit
        exit_choice = input("\nWould you like to: \n1. Create another playlist\n2. Just fetch all playlists\n3. Exit\nEnter your choice (1/2/3): ").strip()
        if exit_choice == "3":
            print("Exiting program.")
            break
        elif exit_choice == "2":
            display_playlists_table()

if __name__ == "__main__":
    main()