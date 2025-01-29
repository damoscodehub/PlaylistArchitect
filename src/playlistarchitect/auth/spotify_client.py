# spotify_client.py
import logging
from typing import Optional
from spotipy import Spotify
from playlistarchitect.auth.spotify_auth import initialize_spotify_client, get_spotify_client

logger = logging.getLogger(__name__)

class SpotifyClient:
    _instance: Optional[Spotify] = None
    
    @classmethod
    def get_client(cls) -> Spotify:
        """Get or create the Spotify client instance."""
        if cls._instance is None:
            logger.info("Initializing Spotify client...")
            initialize_spotify_client()
            cls._instance = get_spotify_client()
        return cls._instance
    
    @classmethod
    def reset_client(cls) -> None:
        """Reset the client instance (useful after clearing cache)."""
        cls._instance = None