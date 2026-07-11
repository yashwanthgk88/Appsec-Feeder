"""SQLite store for indexes and briefings."""
import json
import sqlite3
import time
import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS feed_index (
  feed TEXT, generated_at INTEGER, items_json TEXT,
  PRIMARY KEY (feed)
);
CREATE TABLE IF NOT EXISTS briefings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  feed TEXT, kind TEXT, topic TEXT, content_md TEXT, generated_at INTEGER
);
CREATE TABLE IF NOT EXISTS usage (
  day TEXT PRIMARY KEY, ondemand_count INTEGER
);
"""

def db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.executescript(SCHEMA)
    return conn

def save_index(feed: str, items: list[dict]):
    with db() as conn:
        conn.execute("REPLACE INTO feed_index (feed, generated_at, items_json) VALUES (?,?,?)",
                     (feed, int(time.time()), json.dumps(items)))

def get_index(feed: str):
    with db() as conn:
        row = conn.execute("SELECT generated_at, items_json FROM feed_index WHERE feed=?", (feed,)).fetchone()
    return {"generated_at": row[0], "items": json.loads(row[1])} if row else None

def save_briefing(feed: str, kind: str, topic: str, content_md: str) -> int:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO briefings (feed, kind, topic, content_md, generated_at) VALUES (?,?,?,?,?)",
            (feed, kind, topic, content_md, int(time.time())))
        return cur.lastrowid

def find_briefing(feed: str, kind: str, topic: str):
    with db() as conn:
        row = conn.execute(
            "SELECT id, content_md, generated_at FROM briefings WHERE feed=? AND kind=? AND topic=? ORDER BY id DESC LIMIT 1",
            (feed, kind, topic)).fetchone()
    return {"id": row[0], "content_md": row[1], "generated_at": row[2]} if row else None

def get_briefing(bid: int):
    with db() as conn:
        row = conn.execute(
            "SELECT id, feed, kind, topic, content_md, generated_at FROM briefings WHERE id=?", (bid,)).fetchone()
    if not row:
        return None
    return dict(zip(["id", "feed", "kind", "topic", "content_md", "generated_at"], row))

def bump_ondemand(day: str) -> int:
    with db() as conn:
        conn.execute("INSERT INTO usage (day, ondemand_count) VALUES (?,0) ON CONFLICT(day) DO NOTHING", (day,))
        conn.execute("UPDATE usage SET ondemand_count = ondemand_count + 1 WHERE day=?", (day,))
        return conn.execute("SELECT ondemand_count FROM usage WHERE day=?", (day,)).fetchone()[0]
