<div align="center">

# 🎵 Playlist Architect 📐

</div>

**Playlist Architect** is a Python-based application designed to help Spotify users manage their playlists. It gives a creative way of creating new playlist based on other playlists, besides other useful functionalities such as backup and bulk delete playlists.

It was born as a final project for the CS50’s course **`Introduction to Programming with Python`**.

## ▶️ Video Demo: https://youtu.be/Zz_8-q6o6sw

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

---

## ⚙️ How It Works

Playlist Architect interacts with the Spotify API to fetch and manage your playlists. Here's a quick overview of the workflow:

1. **Authentication**: The app uses Spotify's OAuth2 flow to authenticate users.
2. **Credential and permission request**: It ask for the credentials and permission needed to operates with the indicated Spotify account. 
3. **Playlist Retrieval**: It fetches all your playlists, including details like track count, duration, and owner.
4. **Instant reflect**: Every successfully accomplished action performed by the app is immediately seen in the Spotify account.
---

## 🤔 Why Use Playlist Architect?

- **Time-Saving**: Quickly create playlists with custom time blocks instead of manually adding tracks.
- **Flexibility**: Mix and match tracks from different playlists to create unique listening experiences.
- **Backup Security**: Safeguard your playlists by exporting them to a file, ensuring you never lose your favorite collections.
- **User-Friendly**: The app features a simple, menu-driven interface that makes playlist management intuitive and accessible.

---
## 🔒 Limitations

- **API level**: At the time of this project's publication, the Spotify API does not allow access to either featured playlists (created and managed by Spotify itself) or user-created folders, so they can't be at all view or managed by this app.
- **Logic level**: playback time target set for each block is only an estimation. The app will try to fill that time with random tracks. The final time will depends on what tracks it finally pick.

---

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
---
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
---
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

---
## 🥗 Miscellaneous

To resolve imports during development try adding the following to your `.env` file:
```bash
PYTHONPATH=./src
```
---
## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](https://LICENSE) file for details.