print("Test script started.")
import sys
print("Sys.path:", sys.path)

try:
    print("Before import")
    import retrieve_playlists_table
    print("Module loaded:", retrieve_playlists_table)
except Exception as e:
    print("Error importing module:", str(e))
