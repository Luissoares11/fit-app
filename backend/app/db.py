import sqlite3

from . import config

SCHEMA = """
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
    checkin_weekday INTEGER NOT NULL DEFAULT 0,
    checkin_every_weeks INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS muscle_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    muscle_group_id INTEGER NOT NULL REFERENCES muscle_groups(id),
    archived INTEGER NOT NULL DEFAULT 0,
    UNIQUE (name, muscle_group_id)
);
CREATE TABLE IF NOT EXISTS plan_days (
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
    muscle_group_id INTEGER NOT NULL REFERENCES muscle_groups(id),
    PRIMARY KEY (weekday, muscle_group_id)
);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS workout_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    set_order INTEGER NOT NULL,
    weight_kg REAL NOT NULL,
    reps INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workout_sets_exercise ON workout_sets(exercise_id);
CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date);
"""

MUSCLE_GROUPS = [
    "chest",
    "back",
    "shoulders",
    "biceps",
    "triceps",
    "legs",
    "glutes",
    "abs",
    "forearms",
]

STARTER_EXERCISES = {
    "chest": ["Flat barbell bench press", "Incline dumbbell press", "Cable crossover"],
    "back": ["Lat pulldown", "Seated cable row", "Bent-over barbell row"],
    "shoulders": ["Dumbbell shoulder press", "Lateral raise", "Face pull"],
    "biceps": ["Barbell curl", "Alternating dumbbell curl", "Hammer curl"],
    "triceps": ["Triceps pushdown", "EZ-bar skull crusher", "Dips"],
    "legs": ["Squat", "Leg press", "Lying leg curl", "Calf raise"],
    "glutes": ["Hip thrust"],
    "abs": ["Plank", "Leg raise"],
}

# Names used by databases seeded before the English rename; renamed on startup
LEGACY_NAMES = {
    "peito": "chest",
    "costas": "back",
    "ombros": "shoulders",
    "bíceps": "biceps",
    "tríceps": "triceps",
    "pernas": "legs",
    "glúteos": "glutes",
    "abdominais": "abs",
    "antebraços": "forearms",
    "Supino reto com barra": "Flat barbell bench press",
    "Supino inclinado com halteres": "Incline dumbbell press",
    "Crucifixo no cabo": "Cable crossover",
    "Puxada na polia alta": "Lat pulldown",
    "Remada sentada na polia": "Seated cable row",
    "Remada curvada com barra": "Bent-over barbell row",
    "Press de ombros com halteres": "Dumbbell shoulder press",
    "Elevações laterais": "Lateral raise",
    "Rosca direta com barra": "Barbell curl",
    "Rosca alternada com halteres": "Alternating dumbbell curl",
    "Rosca martelo": "Hammer curl",
    "Extensão de tríceps na polia": "Triceps pushdown",
    "Tríceps testa com barra EZ": "EZ-bar skull crusher",
    "Mergulhos": "Dips",
    "Agachamento": "Squat",
    "Prensa de pernas": "Leg press",
    "Leg curl deitado": "Lying leg curl",
    "Elevação de gémeos": "Calf raise",
    "Prancha": "Plank",
    "Elevação de pernas": "Leg raise",
}


def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.DB_PATH) as conn:
        conn.executescript(SCHEMA)
        _migrate_profile(conn)
        _rename_legacy(conn)
        _seed_gym(conn)


def _migrate_profile(conn: sqlite3.Connection) -> None:
    # Older databases had a "days between check-ins" column; it is replaced by weekday + weeks
    cols = {r[1] for r in conn.execute("PRAGMA table_info(profile)")}
    if "checkin_every_days" in cols:
        conn.execute("ALTER TABLE profile DROP COLUMN checkin_every_days")
    if "checkin_weekday" not in cols:
        conn.execute("ALTER TABLE profile ADD COLUMN checkin_weekday INTEGER NOT NULL DEFAULT 0")
    if "checkin_every_weeks" not in cols:
        conn.execute("ALTER TABLE profile ADD COLUMN checkin_every_weeks INTEGER NOT NULL DEFAULT 1")


def _rename_legacy(conn: sqlite3.Connection) -> None:
    # Idempotent: after the first rename, no row matches an old name anymore
    for old, new in LEGACY_NAMES.items():
        conn.execute("UPDATE muscle_groups SET name = ? WHERE name = ?", (new, old))
        conn.execute("UPDATE exercises SET name = ? WHERE name = ?", (new, old))


def _seed_gym(conn: sqlite3.Connection) -> None:
    # Runs once per database. Later starts must not re-add default groups or starter exercises,
    # otherwise a renamed or deleted default would come back on the next restart.
    conn.execute("CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    if conn.execute("SELECT 1 FROM app_meta WHERE key = 'gym_seeded'").fetchone():
        return
    conn.executemany(
        "INSERT OR IGNORE INTO muscle_groups (name) VALUES (?)", [(g,) for g in MUSCLE_GROUPS]
    )
    if conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0] == 0:
        for group, names in STARTER_EXERCISES.items():
            group_id = conn.execute("SELECT id FROM muscle_groups WHERE name = ?", (group,)).fetchone()[0]
            conn.executemany(
                "INSERT INTO exercises (name, muscle_group_id) VALUES (?, ?)",
                [(name, group_id) for name in names],
            )
    conn.execute("INSERT INTO app_meta (key, value) VALUES ('gym_seeded', '1')")


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
