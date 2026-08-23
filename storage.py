"""Small SQLite persistence layer for HMB GLOBAL.

The bot keeps live voice/player objects in memory, while user/server data is
persisted in SQLite so restarts do not erase playlists, favorites, history,
queue state, warnings, or security settings.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


def _json_default(value: Any):
    if isinstance(value, set):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class SQLiteStorage:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("CREATE TABLE IF NOT EXISTS bot_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.conn.commit()

    def _put(self, key: str, value: Any):
        payload = json.dumps(value, ensure_ascii=False, default=_json_default)
        self.conn.execute(
            "INSERT INTO bot_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, payload),
        )

    def _get(self, key: str, default: Any):
        row = self.conn.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return default

    def save_from(self, bot):
        with self.lock:
            # Convert integer-keyed dictionaries to JSON-safe string keys.
            state = {
                "history": {str(k): v for k, v in bot.history.items()},
                "favorites": {str(k): v for k, v in bot.favorites.items()},
                "playlists": {str(k): v for k, v in bot.playlists.items()},
                "warnings": {f"{k[0]}:{k[1]}": v for k, v in bot.warnings.items()},
                "security_settings": {str(k): v for k, v in bot.security_settings.items()},
                "loop_mode": {str(k): v for k, v in bot.loop_mode.items()},
                "shuffle_mode": {str(k): v for k, v in bot.shuffle_mode.items()},
                "eq_presets": {str(k): v for k, v in bot.eq_presets.items()},
                "song_skiplist": {str(k): v for k, v in bot.song_skiplist.items()},
            }
            for key, value in state.items():
                self._put(key, value)
            self.conn.commit()

    def load_into(self, bot):
        with self.lock:
            history = self._get("history", {})
            favorites = self._get("favorites", {})
            playlists = self._get("playlists", {})
            warnings = self._get("warnings", {})
            security = self._get("security_settings", {})
            loop_mode = self._get("loop_mode", {})
            shuffle_mode = self._get("shuffle_mode", {})
            eq_presets = self._get("eq_presets", {})
            skiplist = self._get("song_skiplist", {})

            bot.history.update({int(k): v for k, v in history.items() if str(k).isdigit()})
            bot.favorites.update({int(k): v for k, v in favorites.items() if str(k).isdigit()})
            bot.playlists.update({int(k): v for k, v in playlists.items() if str(k).isdigit()})
            for key, value in warnings.items():
                try:
                    guild_id, user_id = key.split(":", 1)
                    bot.warnings[(int(guild_id), int(user_id))] = value
                except ValueError:
                    continue
            bot.security_settings.update({int(k): v for k, v in security.items() if str(k).isdigit()})
            bot.loop_mode.update({int(k): v for k, v in loop_mode.items() if str(k).isdigit()})
            bot.shuffle_mode.update({int(k): bool(v) for k, v in shuffle_mode.items() if str(k).isdigit()})
            bot.eq_presets.update({int(k): v for k, v in eq_presets.items() if str(k).isdigit()})
            bot.song_skiplist.update({int(k): v for k, v in skiplist.items() if str(k).isdigit()})

    def close(self):
        with self.lock:
            self.conn.close()
