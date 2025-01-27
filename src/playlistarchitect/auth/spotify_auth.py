import spotipy
import os
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from playlistarchitect.utils.logging_utils import log_and_print
load_dotenv()

# Create a cache file path
cache_path = ".spotify_cache"

# Initialize Spotify client with auth manager
def get_spotify_client():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope="user-library-read user-library-modify playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private",
        cache_path=cache_path,
        open_browser=True  # This will automatically open your browser
    ))

def clear_cached_token():
    """Clear the cached authentication token."""
    if os.path.exists(cache_path):
        os.remove(cache_path)
        print("Cached token cleared. Please re-authenticate.")

# Test the connection
if __name__ == "__main__":
    sp = get_spotify_client()
    try:
        # Try to get current user's info as a test
        user_info = sp.current_user()
        print(f"Successfully connected to Spotify as {user_info['display_name']}")
    except Exception as e:
        log_and_print(f"Error: {str(e)}", level="error")