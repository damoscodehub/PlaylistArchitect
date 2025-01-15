import random
import logging
from src.auth.spotify_auth import get_spotify_client
from src.operations.retrieve_playlists_table import format_duration, truncate, display_playlists_table, save_playlists_to_file
from src.utils.api_helpers import assign_temporary_ids
from src.utils.error_handler import handle_spotify_errors

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sp = get_spotify_client()

@handle_spotify_errors
def get_song_from_playlist(playlist_id, total_duration_ms, acceptable_deviation_ms):
    """Fetch random songs from a playlist until the desired total duration is met."""
    song_list = []
    track_offset = 0
    while True:
        tracks_response = sp.playlist_items(
            playlist_id,
            offset=track_offset, 
            fields="items.track.uri,items.track.duration_ms,items.track.name",
            additional_types=["track"]
        )
        
        if not tracks_response['items']:
            break
            
        for track in tracks_response['items']:
            if track['track']:
                song_list.append(track)
                
        track_offset += len(tracks_response['items'])

    selected_songs = []
    current_duration = 0

    while song_list:
        song = random.choice(song_list)
        song_list.remove(song)
        
        duration = song['track']['duration_ms']
        current_duration += duration
        selected_songs.append(song)
        
        if abs(current_duration - total_duration_ms) <= acceptable_deviation_ms:
            break
            
        if current_duration > total_duration_ms + acceptable_deviation_ms:
            selected_songs.pop()
            current_duration -= duration
            break
    
    return selected_songs

@handle_spotify_errors
def create_new_playlist(playlists):
    """Create a new playlist with songs from selected playlist."""
    logger.info("Starting new playlist creation...")
    
    # Display available playlists
    display_playlists_table(playlists)
    
    # Get user input
    try:
        playlist_id = int(input("\nEnter the ID of the source playlist: "))
        hours = int(input("Enter the desired duration (hours): "))
        minutes = int(input("Enter the desired duration (minutes): "))
        playlist_name = input("Enter the name for the new playlist: ")
    except ValueError as e:
        logger.error(f"Invalid input: {str(e)}")
        return
    
    # Calculate durations
    total_duration_ms = (hours * 3600 + minutes * 60) * 1000
    acceptable_deviation_ms = 5 * 60 * 1000  # 5 minutes deviation
    
    # Find source playlist
    source_playlist = next((p for p in playlists if p['id'] == playlist_id), None)
    if not source_playlist:
        logger.error("Invalid playlist ID")
        return
    
    logger.info(f"Creating playlist '{playlist_name}' with target duration: {format_duration(total_duration_ms)}")
    
    # Get songs
    selected_songs = get_song_from_playlist(
        source_playlist['spotify_id'],
        total_duration_ms,
        acceptable_deviation_ms
    )
    
    if not selected_songs:
        logger.error("No songs selected")
        return
    
    # Calculate actual duration
    actual_duration = sum(song['track']['duration_ms'] for song in selected_songs)
    
    # Create new playlist
    user_id = sp.current_user()['id']
    new_playlist = sp.user_playlist_create(
        user_id,
        playlist_name,
        public=False,
        description=f"Generated from {source_playlist['name']}"
    )
    
    # Add tracks
    track_uris = [song['track']['uri'] for song in selected_songs]
    sp.playlist_add_items(new_playlist['id'], track_uris)
    
    logger.info(f"Created playlist with {len(selected_songs)} songs")
    logger.info(f"Target duration: {format_duration(total_duration_ms)}")
    logger.info(f"Actual duration: {format_duration(actual_duration)}")
    
    # Update playlists list
    playlists.append({
        'spotify_id': new_playlist['id'],
        'name': playlist_name,
        'tracks': {'total': len(selected_songs)},
        'duration_ms': actual_duration
    })
    save_playlists_to_file(playlists)

if __name__ == "__main__":
    try:
        playlists = []  # Add test playlists here
        create_new_playlist(playlists)
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")