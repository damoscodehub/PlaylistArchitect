# retrieve_playlists.py

import spotipy
from spotify_auth import sp  # Import the authenticated Spotify client

def get_all_playlists():
    """
    Retrieve all playlists created/saved by the user.
    
    Returns:
        list: A list of dictionaries, each representing a playlist with details such as name and id.
    """
    playlists = []
    offset = 0
    limit = 50  # Spotify API returns a maximum of 50 playlists per request

    while True:
        # Fetch playlists with pagination
        response = sp.current_user_playlists(limit=limit, offset=offset)
        playlists.extend(response['items'])

        # Check if we got all playlists
        if response['next'] is None:
            break
        
        offset += limit

    return playlists

if __name__ == "__main__":
    playlists = get_all_playlists()
    print(f"Retrieved {len(playlists)} playlists:")
    for playlist in playlists:
        print(f" - {playlist['name']} (ID: {playlist['id']})")