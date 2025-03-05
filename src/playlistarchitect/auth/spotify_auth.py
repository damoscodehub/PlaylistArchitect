import spotipy
import os
import logging
from dotenv import load_dotenv
from pathlib import Path
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Default cache file path (can be overridden via environment variables)
cache_path = Path(os.getenv("SPOTIPY_CACHE_PATH", ".spotify_cache")).resolve()

# Global Spotify client
sp = None


def check_environment_variables():
    """Ensure all required environment variables are set."""
    required_vars = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]
    missing_vars = [var for var in required_vars if not os.environ.get(var, "").strip()]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")


def create_spotify_oauth():
    """Create a SpotifyOAuth object with the required credentials and scope."""    
    logging.getLogger('spotipy').setLevel(logging.CRITICAL)
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope="user-library-read user-library-modify playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private",
        cache_path=str(cache_path),
        open_browser=True,
    )


def initialize_spotify_client():
    """Initializes the global Spotify client. Call this once at the start of the app."""
    global sp
    if sp is not None:
        return  # Already initialized
    try:
        logger.debug("Initializing Spotify client...")
        check_environment_variables()
        
        # Initialize SpotifyOAuth
        auth_manager = create_spotify_oauth()
        
        # Initialize Spotify client with the new token
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # Test the connection by retrieving user info
        user_info = sp.current_user()
        logger.info(f"Successfully connected to Spotify as {user_info['display_name']}")
        logger.debug("Spotify client initialized successfully.")
    except SpotifyOauthError as oauth_error:
        logger.error(f"Spotify OAuth failed: {oauth_error}")
        raise RuntimeError("Spotify authentication failed. Please check your credentials.") from oauth_error
    except EnvironmentError as env_error:
        logger.error(f"Environment setup error: {env_error}")
        raise    
    except Exception as e:
        logger.error(f"Unexpected error during Spotify client initialization: {str(e)}")
        raise RuntimeError("An unexpected error occurred during Spotify client initialization.") from e

def get_spotify_client():
    """Return the already initialized Spotify client."""
    global sp
    if sp is None:
        raise RuntimeError("Spotify client has not been initialized. Call initialize_spotify_client() first.")
    return sp


def clear_cached_token():
    """Clear the cached authentication token."""
    try:
        if cache_path.exists():
            cache_path.unlink()  # Remove cache file
            logger.info("Cached token cleared.")
    except Exception as e:
        logger.error(f"Failed to clear cached token: {e}")
        
def force_immediate_authentication():
    """
    Force immediate authentication by creating a new SpotifyOAuth instance
    and explicitly requesting a new access token.
    
    Returns:
        bool: True if authentication was successful, False otherwise
    """
    try:
        # Create a new auth manager
        auth_manager = create_spotify_oauth()
        
        # Explicitly request a new access token
        # This will open the browser and force user interaction
        token_info = auth_manager.get_access_token(as_dict=True)
        
        # Reinitialize the global Spotify client with the new auth manager
        global sp
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # Verify the connection by fetching user info
        user_info = sp.current_user()
        logger.info(f"Successfully connected to Spotify as {user_info['display_name']}")
        
        return True
    except Exception as e:
        logger.error(f"Immediate authentication failed: {e}")
        return False