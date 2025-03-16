import spotipy
import os
import logging
from dotenv import load_dotenv
from pathlib import Path
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError, CacheFileHandler

logger = logging.getLogger(__name__)

# Default cache file path (can be overridden via environment variables)
cache_path = Path(os.getenv("SPOTIPY_CACHE_PATH", ".spotify_cache")).resolve()

# Global Spotify client
sp = None


def check_env_file():
    """Check if the .env file exists and contains the required Spotify credentials."""
    env_path = Path(".env")
    if not env_path.exists():
        return False
    with open(env_path, "r") as f:
        content = f.read()
        return "SPOTIPY_CLIENT_ID" in content and "SPOTIPY_CLIENT_SECRET" in content


def setup_spotify_credentials():
    """Interactively prompt the user for Spotify API credentials and save them to the .env file."""
    print()
    print("Your Spotify API credentials are needed.")
    print("You can find them at https://developer.spotify.com/dashboard/applications.")
    print("(Video tutorial https://youtu.be/0fhkkkRuUxw.)")
    print()
    
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    redirect_uri = input("Redirect URI (or leave it empty to use the default: http://localhost:8888/callback): ").strip() or "http://localhost:8888/callback"

    with open(".env", "w") as f:
        f.write(f"SPOTIPY_CLIENT_ID={client_id}\n")
        f.write(f"SPOTIPY_CLIENT_SECRET={client_secret}\n")
        f.write(f"SPOTIPY_REDIRECT_URI={redirect_uri}\n")

    print("Credentials saved to .env file. You can now authenticate with Spotify.")


def check_environment_variables():
    """Ensure all required environment variables are set."""
    required_vars = ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"]
    missing_vars = [var for var in required_vars if not os.environ.get(var, "").strip()]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")


def create_spotify_oauth():
    """Create a SpotifyOAuth object with the required credentials and scope."""
    logging.getLogger('spotipy').setLevel(logging.CRITICAL)
    cache_handler = CacheFileHandler(cache_path=str(cache_path))
    return SpotifyOAuth(
        client_id=os.getenv("SPOTIPY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
        scope="user-library-read user-library-modify playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private",
        cache_handler=cache_handler,
        open_browser=True,
    )

def initialize_spotify_client():
    """Initializes the global Spotify client. Call this once at the start of the app."""
    global sp
    if sp is not None:
        return  # Already initialized

    # Check if .env file exists and contains credentials
    if not check_env_file():
        setup_spotify_credentials()

    try:
        logger.debug("Initializing Spotify client...")
        load_dotenv()  # Load environment variables from .env file
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