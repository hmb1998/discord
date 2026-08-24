from pathlib import Path

def test_youtube_cookie_file_configured():
    config = Path("config.py").read_text(encoding="utf-8")
    main = Path("main.py").read_text(encoding="utf-8")
    fly = Path("fly.toml").read_text(encoding="utf-8")
    assert "YOUTUBE_COOKIE_FILE" in config
    assert "YOUTUBE_COOKIE_FILE" in main
    assert 'guest_path = "/app/cookies.txt"' in fly
    assert 'secret_name = "YOUTUBE_COOKIE_FILE"' in fly
