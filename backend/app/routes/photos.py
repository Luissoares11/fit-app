import sqlite3

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import config
from ..auth import require_token
from ..db import get_db
from ..images import InvalidImage, save_photo
from ..schemas import Angle

router = APIRouter(dependencies=[Depends(require_token)])


@router.post("/sessions/{session_id}/photos/{angle}", status_code=201)
def upload_photo(
    session_id: int,
    angle: Angle,
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(get_db),
):
    row = conn.execute("SELECT date FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        save_photo(file.file, config.PHOTO_DIR / row["date"], angle)
    except InvalidImage:
        raise HTTPException(status_code=400, detail="Not a valid image")

    # Re-uploading the same angle replaces the old photo
    conn.execute(
        "INSERT INTO photos (session_id, angle) VALUES (?, ?) "
        "ON CONFLICT(session_id, angle) DO UPDATE SET created_at = CURRENT_TIMESTAMP",
        (session_id, angle),
    )
    return {"ok": True}


@router.get("/sessions/{session_id}/photos/{angle}")
def get_photo(
    session_id: int,
    angle: Angle,
    thumb: bool = False,
    conn: sqlite3.Connection = Depends(get_db),
):
    row = conn.execute(
        """
        SELECT s.date FROM photos p
        JOIN sessions s ON s.id = p.session_id
        WHERE p.session_id = ? AND p.angle = ?
        """,
        (session_id, angle),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Photo not found")
    name = f"{angle}_thumb.jpg" if thumb else f"{angle}.jpg"
    return FileResponse(config.PHOTO_DIR / row["date"] / name, media_type="image/jpeg")