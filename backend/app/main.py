from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .auth import router as auth_router
from .db import init_db
from .routes import photos, sessions, weights

config.PHOTO_DIR.mkdir(parents=True, exist_ok=True)
init_db()

app = FastAPI(title="Fitness tracker")

app.include_router(auth_router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(photos.router, prefix="/api")
app.include_router(weights.router, prefix="/api")

# Serves the frontend at / once it exists. Mounted last so /api and /docs win.
if config.FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")