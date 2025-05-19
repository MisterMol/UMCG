import os
import json
from pathlib import Path
from datetime import datetime

SESSIE_PAD = Path.home() / ".secure_sessions"
SESSIE_BESTAND = SESSIE_PAD / "sessions.json"

def _load_sessions():
    if not SESSIE_BESTAND.exists():
        return {}
    with open(SESSIE_BESTAND, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_sessions(data):
    SESSIE_PAD.mkdir(parents=True, exist_ok=True)
    with open(SESSIE_BESTAND, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_session(site, username):
    data = _load_sessions()
    return data.get(site, {}).get(username)

def save_session(site, username, sessie_data):
    data = _load_sessions()
    if site not in data:
        data[site] = {}
    data[site][username] = {
        **sessie_data,
        "timestamp": datetime.now().isoformat()
    }
    _save_sessions(data)

def session_exists(site, username):
    data = _load_sessions()
    return site in data and username in data[site]
