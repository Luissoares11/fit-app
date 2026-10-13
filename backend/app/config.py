import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
PHOTO_DIR = DATA_DIR / "photos"
DB_PATH = DATA_DIR / "fitness.db"
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "../frontend"))
APP_TOKEN = os.environ["APP_TOKEN"]
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"