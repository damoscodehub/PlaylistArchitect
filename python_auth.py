import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

load_dotenv()

# Create a cache file path
cache_path = ".spotify_cache"

# Initialize Spotify client with auth manager
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-library-read user-library-modify playlist-read-private playlist-modify-public",
    cache_path=cache_path,
    open_browser=True  # This will automatically open your browser
))

# Test the connection
try:
    # Try to get current user's info as a test
    user_info = sp.current_user()
    print(f"Successfully connected to Spotify as {user_info['display_name']}")
except Exception as e:
    print(f"Error: {str(e)}")