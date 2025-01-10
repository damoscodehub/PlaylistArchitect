import json

def verify_playlists(file_path):
    with open(file_path, "r") as file:
        playlists = json.load(file)
    
    for playlist in playlists:
        playlist_name = playlist.get("name", "Unknown")
        track_count = len(playlist.get("tracks", []))
        print(f"Playlist '{playlist_name}' has {track_count} tracks.")

# Path to your JSON file
file_path = "d:/Programming/Projects/PlaylistArchitect/Backups/BU4.json"
verify_playlists(file_path)