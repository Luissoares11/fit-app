import sqlite3

from fastapi import APIRouter, Depends

from ..auth import require_token
from ..db import get_db

router = APIRouter(dependencies=[Depends(require_token)])


@router.get("/weights")
def weights(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute("SELECT date, weight_kg FROM sessions ORDER BY date").fetchall()
    return [dict(r) for r in rows]