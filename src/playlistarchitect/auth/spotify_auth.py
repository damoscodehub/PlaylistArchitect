import spotipy
import os
import logging
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Default cache file path (can be overridden via environment variables)
cache_path = os.getenv("SPOTIPY_CACHE_PATH", ".spotify_cache")

# Global Spotify client
sp = None


def check_environment_variables():
    """
    Ensure all required environment variables are set.
    Raises:
        EnvironmentError: If any required environment variable is missing.
    """
    required_vars = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")


def create_spotify_oauth():
    """
    Create a SpotifyOAuth object with the required credentials and scope.
    Returns:
        SpotifyOAuth: An instance configured for Spotify API authentication.
    """
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope="user-library-read user-library-modify playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private",
        cache_path=cache_path,
        open_browser=True,
    )


def initialize_spotify_client():
    """
    Initializes the global Spotify client. Call this at the start of the app.
    Raises:
        RuntimeError: If the Spotify client cannot be initialized.
    """
    global sp
    try:
        logger.debug("Initializing Spotify client...")

        # Validate environment variables
        check_environment_variables()

        # Initialize Spotify client
        auth_manager = create_spotify_oauth()
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
    """Return the initialized Spotify client."""
    global sp
    if sp is None:
        logger.debug("get_spotify_client() called but 'sp' is None. Attempting to reinitialize...")
        initialize_spotify_client()

    if sp is None:
        logger.error("get_spotify_client() failed: 'sp' is still None after reinitialization!")
        raise RuntimeError("Spotify client is not initialized.")

    return sp



def clear_cached_token():
    """
    Clear the cached authentication token.
    """
    try:
        if os.path.exists(cache_path):
            os.remove(cache_path)
            logger.info("Cached token cleared. Please re-authenticate.")
    except Exception as e:
        logger.error(f"Failed to clear cached token: {e}")
