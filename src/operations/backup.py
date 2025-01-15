import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from src.auth.spotify_auth import get_spotify_client
from src.utils.error_handler import handle_spotify_errors
from src.utils.api_helpers import assign_temporary_ids

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BACKUP_FILE = Path("data/playlists_backup.json")
BATCH_SIZE = 100

@handle_spotify_errors
def backup_options(playlists: List[Dict[str, Any]], selected_ids: Optional[List[int]] = None) -> None:
    """
    Backup selected or all playlists to a file.
    
    Args:
        playlists: List of playlist dictionaries
        selected_ids: Optional list of playlist IDs to backup
    """
    logger.info("Starting playlist backup...")
    assign_temporary_ids(playlists)
    
    playlists_to_export = [p for p in playlists if not selected_ids or p['id'] in selected_ids]
    
    if not playlists_to_export:
        logger.warning("No playlists selected for backup")
        return

    sp = get_spotify_client()
    
    for playlist in playlists_to_export:
        logger.info(f'Backing up "{playlist["name"]}"...')
        tracks = []
        
        for offset in range(0, playlist['tracks']['total'], BATCH_SIZE):
            response = sp.playlist_tracks(
                playlist['id'],
                offset=offset,
                fields='items(track(uri,name,artists(name),album(name)))'
            )
            
            tracks.extend([{
                'uri': item['track']['uri'],
                'name': item['track']['name'],
                'artists': [artist['name'] for artist in item['track']['artists']],
                'album': item['track']['album']['name']
            } for item in response['items'] if item['track']])
            
        playlist['tracks'] = tracks

    BACKUP_FILE.parent.mkdir(exist_ok=True)
    try:
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(playlists_to_export, f, indent=2, ensure_ascii=False)
        logger.info(f"Backup saved to {BACKUP_FILE}")
    except IOError as e:
        logger.error(f"Failed to save backup: {str(e)}")
        raise

@handle_spotify_errors
def import_playlists(backup_file: Path = BACKUP_FILE) -> None:
    """
    Import playlists from backup file.
    
    Args:
        backup_file: Path to backup file
    """
    logger.info(f"Importing playlists from {backup_file}")
    sp = get_spotify_client()
    user_id = sp.current_user()['id']
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            playlists = json.load(f)
    except IOError as e:
        logger.error(f"Failed to read backup file: {str(e)}")
        raise
    
    for playlist in playlists:
        logger.info(f'Importing "{playlist["name"]}"...')
        
        new_playlist = sp.user_playlist_create(
            user_id, 
            playlist['name'],
            public=playlist.get('public', True),
            description=playlist.get('description', '')
        )
        
        track_uris = [track['uri'] for track in playlist['tracks']]
        for i in range(0, len(track_uris), BATCH_SIZE):
            batch = track_uris[i:i + BATCH_SIZE]
            sp.playlist_add_items(new_playlist['id'], batch)
            
    logger.info("Import completed successfully")

if __name__ == "__main__":
    try:
        playlists = []  # Add test playlists here
        backup_options(playlists)
        import_playlists()
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")