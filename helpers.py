def assign_temporary_ids(playlists):
    for idx, playlist in enumerate(playlists, start=1):
        playlist['id'] = idx