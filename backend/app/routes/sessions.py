import shutil
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import config
from ..auth import require_token
from ..db import get_db
from ..schemas import SessionIn

router = APIRouter(dependencies=[Depends(require_token)])


@router.post("/sessions", status_code=201)
def create_session(body: SessionIn, conn: sqlite3.Connection = Depends(get_db)):
    try:
        cur = conn.execute(
            "INSERT INTO sessions (date, weight_kg, note) VALUES (?, ?, ?)",
            (body.date.isoformat(), body.weight_kg, body.note),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A session for this date already exists")
    return {"id": cur.lastrowid}


@router.get("/sessions")
def list_sessions(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        """
        SELECT s.id, s.date, s.weight_kg, s.note, GROUP_CONCAT(p.angle) AS angles
        FROM sessions s
        LEFT JOIN photos p ON p.session_id = s.id
        GROUP BY s.id
        ORDER BY s.date DESC
        """
    ).fetchall()
    return [
        {**dict(r), "angles": r["angles"].split(",") if r["angles"] else []}
        for r in rows
    ]


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute("SELECT date FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    shutil.rmtree(config.PHOTO_DIR / row["date"], ignore_errors=True)