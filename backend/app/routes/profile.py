import sqlite3

from fastapi import APIRouter, Depends

from ..auth import require_token
from ..db import get_db
from ..schemas import ProfileIn

router = APIRouter(dependencies=[Depends(require_token)])

FIELDS = (
    "name",
    "start_weight_kg",
    "goal_weight_kg",
    "height_cm",
    "age",
    "start_date",
    "checkin_weekday",
    "checkin_every_weeks",
)


def _read(conn: sqlite3.Connection) -> dict:
    row = conn.execute(f"SELECT {', '.join(FIELDS)} FROM profile WHERE id = 1").fetchone()
    if row is None:
        # Nothing saved yet: every field empty except the check-in schedule defaults
        return {**dict.fromkeys(FIELDS, None), "checkin_weekday": 0, "checkin_every_weeks": 1}
    return dict(row)


@router.get("/profile")
def get_profile(conn: sqlite3.Connection = Depends(get_db)):
    return _read(conn)


@router.put("/profile")
def save_profile(body: ProfileIn, conn: sqlite3.Connection = Depends(get_db)):
    data = body.model_dump()
    data["start_date"] = data["start_date"].isoformat() if data["start_date"] else None
    conn.execute(
        f"""
        INSERT INTO profile (id, {', '.join(FIELDS)}) VALUES (1, {', '.join(f':{f}' for f in FIELDS)})
        ON CONFLICT(id) DO UPDATE SET {', '.join(f'{f} = excluded.{f}' for f in FIELDS)}
        """,
        data,
    )
    return _read(conn)
