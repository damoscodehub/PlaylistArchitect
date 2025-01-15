import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from src.utils.error_handler import handle_spotify_errors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
REQUIRED_ENV_VARS = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]
CACHE_PATH = ".spotify_cache"
SCOPE = "user-library-read playlist-modify-public playlist-modify-private"

def validate_credentials() -> bool:
    """Validate required environment variables exist."""
    missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        return False
    return True

@handle_spotify_errors
def get_spotify_client() -> spotipy.Spotify:
    """Initialize and return authenticated Spotify client."""
    logger.info("Initializing Spotify client...")
    if not validate_credentials():
        raise ValueError("Missing required Spotify credentials")
    
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope=SCOPE,
        cache_path=CACHE_PATH
    ))

@handle_spotify_errors
def clear_cached_token() -> None:
    """Clear the cached authentication token."""
    logger.info("Attempting to clear cached token...")
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)
        logger.info("Cached token cleared successfully")
    else:
        logger.info("No cached token found")

if __name__ == "__main__":
    try:
        sp = get_spotify_client()
        user = sp.current_user()
        logger.info(f"Connected as: {user['display_name']}")
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")