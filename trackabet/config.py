"""Configuration management."""
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".trackabet"
CONFIG_FILE = CONFIG_DIR / "config.json"
DB_FILE = CONFIG_DIR / "bets.db"


def get_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> dict:
    defaults = {
        "api_base_url": "https://trackabet.bettingiscool.com",
        "session_email": "",
        "session_token": "",
        "default_bookmaker": "bet365",
        "bookmakers": [
            "bet365", "pinnacle", "draftkings", "fanduel",
            "betmgm", "caesars", "pointsbet", "unibet",
            "william-hill", "betfred", "skybet", "other",
        ],
        "recent_sports": [
            "football", "basketball", "tennis", "baseball",
            "american-football", "hockey", "darts", "boxing-mma",
            "rugby", "cricket",
        ],
        "web_port": 6789,
        "web_host": "127.0.0.1",
    }
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text())
            defaults.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return defaults


def save_config(config: dict):
    get_config_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_db_path() -> str:
    get_config_dir()
    return str(DB_FILE)
