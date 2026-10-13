import sqlite3

from . import config


def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                weight_kg REAL NOT NULL,
                note TEXT
            );
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                angle TEXT NOT NULL CHECK (angle IN ('front', 'back', 'side')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (session_id, angle)
            );
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT,
                start_weight_kg REAL,
                goal_weight_kg REAL,
                height_cm REAL,
                age INTEGER,
                checkin_every_days INTEGER NOT NULL DEFAULT 7
            );
            """
        )


def get_db():
    # FastAPI may open and close this connection on different threads; each request has its own
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()