# test.py
from playlistarchitect.utils.formatting_helpers import format_duration, truncate
from playlistarchitect.auth.spotify_auth import check_env_file, setup_spotify_credentials
import os

def test_format_duration():
    assert format_duration(3661000) == "01:01:01"  # 1 hour, 1 minute, 1 second
    assert format_duration(60000) == "00:01:00"    # 1 minute
    assert format_duration(0) == "00:00:00"        # 0 milliseconds

def test_truncate():
    assert truncate("Hello, World!", 5) == "He..."  # Truncate to 5 characters
    assert truncate("Hello, World!", 20) == "Hello, World!"  # No truncation needed
    assert truncate("", 10) == ""  # Empty string

def test_check_env_file(tmp_path):
    # Create a temporary .env file with required credentials
    env_file = tmp_path / ".env"
    env_file.write_text("SPOTIPY_CLIENT_ID=test_id\nSPOTIPY_CLIENT_SECRET=test_secret\n")

    # Temporarily change the working directory to the temporary directory
    original_dir = os.getcwd()
    os.chdir(tmp_path)

    try:
        assert check_env_file() is True  # File exists and has required credentials
    finally:
        # Restore the original working directory
        os.chdir(original_dir)

def test_setup_spotify_credentials(tmp_path, monkeypatch):
    # Simulate user input in sequence
    inputs = ["test_id", "test_secret", ""]  # Client ID, Client Secret, Default Redirect URI
    monkeypatch.setattr("builtins.input", lambda _: inputs.pop(0))

    # Temporarily change the working directory to the temporary directory
    original_dir = os.getcwd()
    os.chdir(tmp_path)

    try:
        setup_spotify_credentials()  # Run the function
        assert (tmp_path / ".env").exists()  # Check if .env file was created
        with open(tmp_path / ".env", "r") as f:
            content = f.read()
            assert "SPOTIPY_CLIENT_ID=test_id" in content
            assert "SPOTIPY_CLIENT_SECRET=test_secret" in content
            assert "SPOTIPY_REDIRECT_URI=http://localhost:8888/callback" in content
    finally:
        # Restore the original working directory
        os.chdir(original_dir)
        
def test_check_environment_variables(monkeypatch):
    # Simulate all required environment variables being set
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")

    # The function should not raise an exception
    from playlistarchitect.auth.spotify_auth import check_environment_variables
    check_environment_variables()

    # Simulate missing environment variables
    monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
    from pytest import raises
    with raises(EnvironmentError):
        check_environment_variables()
        
def test_create_spotify_oauth(monkeypatch):
    # Simulate required environment variables
    monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id")
    monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")

    from playlistarchitect.auth.spotify_auth import create_spotify_oauth
    auth_manager = create_spotify_oauth()

    # Verify the auth_manager is created with the correct credentials
    assert auth_manager.client_id == "test_id"
    assert auth_manager.client_secret == "test_secret"
    assert auth_manager.redirect_uri == "http://localhost:8888/callback"        