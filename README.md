<div align="center">

# 🎵 Playlist Architect 📐
> (backup, delete and create Spotify playlists)
</div>

**Playlist Architect** is a Python-based application designed to help Spotify users manage their playlists. It gives a creative way of creating new playlist based on other playlists, besides other useful functionalities such as backup and bulk delete playlists.

It was born as a final project for the CS50’s course **`Introduction to Programming with Python`**.

## ▶️ Video Demo
https://youtu.be/Zz_8-q6o6sw

## 📑 Technical info
* **Title:** "Playlist Architect"
* **Type:** Python app
* **Submited to CS50 on:** March 16, 2025
* **Authors:**
    * Damián Ferrero (me):
        * [LinkedIn](https://linkedin.com/in/damianferrero)
        * [GitHub](https://github.com/damoscodehub) (@damoscodehub)
    * Eva Nikoghsyan:
        * [LinkedIn](https://linkedin.com/in/eva-nikoghosyan)
        * [GitHub](https://github.com/eva-niko) (@eva-niko)

## ✨ Features

### 1. **Create New Playlists with Custom Time Blocks**
   - Combine tracks blocks from multiple playlists into a new playlist.
   - Specify exact time durations for each track block (e.g., 30 minutes from Playlist A, 1 hour from Playlist B).
   - Reorder playlist blocks, even manually or shuffle them.
   - Choose between public or private playlist visibility.

### 2. **Backup and Restore Playlists**
   - Export your playlists to a JSON file for safekeeping.
   - Import playlists from a backup file to restore your library.
   - Options to recreate playlists, follow original playlists, or a mix of both.

### 3. **Remove Playlists from Your Library**
   - Easily unfollow playlists from your Spotify library.
   - Select specific playlists or remove all at once.

### 4. **View and Manage Playlists**
   - Display a detailed table of your playlists, including track counts and total playback time.
   - Refresh playlist data to get the latest information from Spotify.

### 5. **Spotify Authentication**
   - Securely authenticate with Spotify using OAuth.
   - Clear cached authentication tokens for re-authentication when needed.

## ⚙️ How It Works

Playlist Architect interacts with the Spotify API to fetch and manage your playlists. Here's a quick overview of the workflow:

1. **Authentication**: The app uses Spotify's OAuth2 flow to authenticate users.
2. **Credential and permission request**: It ask for the credentials and permission needed to operates with the indicated Spotify account. 
3. **Playlist Retrieval**: It fetches all your playlists, including details like track count, duration, and owner.
4. **Instant reflect**: Every successfully accomplished action performed by the app is immediately seen in the Spotify account.

## 🤔 Why Use Playlist Architect?

- **Time-Saving**: Quickly create playlists with custom time blocks instead of manually adding tracks.
- **Flexibility**: Mix and match tracks from different playlists to create unique listening experiences.
- **Backup Security**: Safeguard your playlists by exporting them to a file, ensuring you never lose your favorite collections.
- **User-Friendly**: The app features a simple, menu-driven interface that makes playlist management intuitive and accessible.

## ➡️ Usage Instructions

### **1.Prerequisites**

- A Spotify account.
- Python 3.9 or higher installed on your system.
### **2. Clone the Repository**

To get started, clone the repository to your local machine:
```bash
git clone https://github.com/damoscodehub/PlaylistArchitect.git
cd PlaylistArchitect
```

### **3. Install Dependencies**

You can install the required dependencies using either **Poetry** or **pip**.
#### **Option A: Using Poetry (Recommended)**

1. Install Poetry if you don’t already have it:
```bash
pip install poetry
```    

2. Install dependencies:
```bash
poetry install
```

3. Activate the virtual environment:
```bash
poetry shell
```
#### **Option B: Using pip**

1. Install dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### **4. Run the Program**

1. Start the application:
```bash
poetry run python src/playlistarchitect/main.py
```
 
If you’re using `pip` instead of Poetry, simply run:
```bash
python src/playlistarchitect/main.py
```
2. Follow the on-screen instructions to authenticate with Spotify and start managing your playlists.

## 🥗 Miscellaneous

To resolve imports during development try adding the following to your `.env` file:
```bash
PYTHONPATH=./src
```

## 🚨 Known issues

### Within our reach (maybe)
> (we will solve them as soon as we can)

⬛ **Dialog window (tkinter)**: When it pops up (in Backup options), it is not automatically focused.
⬛ **Folders**: As far as we know, Spotify API does not allow access to user-created folders.
    We may found a workaround somewhere here:
    - "Folders are not returned through the Web API, nor can be created using it." https://developer.spotify.com/documentation/web-api/concepts/playlists
		- May be a text-tree can be saved to have a visual reference of how the original tree was.
    - see https://github.com/mikez/spotify-folders/blob/master/README.md (last paragraph) "The Spotify Web API does currently not support getting the folder hierarchy. However, one can (as of this writing) find it in the local Spotify cache. This script extracts the data from the cache and returns it in a JSON-formatted way."

### Out of our reach
❌ **Featured playlists**: As far as we know, Spotify API does not allow access to featured playlists (created and managed by Spotify itself)
❌ **Final playback mismatch**: The total playback time of a new playlist may be slightly different from the stated time, as the time you allocate to each block is an estimate to fill it with tracks. So, ultimately, it depends on which tracks the app randomly picks. The more blocks you make, the greater the difference in total playback time will likely be.

## ✅ To-do

⬛ Bulk block edition options. 1: Total playback time (for each block). 2: Total sum playback time (evenly divided).
⬛ Option and instructions to revoke app access to Spotify account.
⬛ Test "b" (back) and "c" (cancel) inputs. Allow them where they are still missing.
⬛ Remove > Select playlists to keep (remove the rest).
⬛ New playlist > Add custom time of silence (fixed/random places)
⬛ Merge playlists
⬛ Split playlists
⬛ User configurations
	⬛ Refresh playlist data at start.
	⬛ Delete playlist data on exit.
	⬛ Delete authentication data on exit.

## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](https://LICENSE) file for details.