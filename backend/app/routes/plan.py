import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_token
from ..db import get_db
from ..schemas import PlanIn

router = APIRouter(dependencies=[Depends(require_token)])


def _read_plan(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT weekday, muscle_group_id FROM plan_days ORDER BY weekday, muscle_group_id"
    ).fetchall()
    days: dict[int, list[int]] = {}
    for r in rows:
        days.setdefault(r["weekday"], []).append(r["muscle_group_id"])
    return {"days": [{"weekday": w, "muscle_group_ids": ids} for w, ids in sorted(days.items())]}


@router.get("/plan")
def get_plan(conn: sqlite3.Connection = Depends(get_db)):
    return _read_plan(conn)


@router.put("/plan")
def save_plan(body: PlanIn, conn: sqlite3.Connection = Depends(get_db)):
    # Check everything before touching the table, so a bad plan never half-applies
    group_ids = {g for day in body.days for g in day.muscle_group_ids}
    if group_ids:
        placeholders = ", ".join("?" * len(group_ids))
        found = conn.execute(
            f"SELECT COUNT(*) FROM muscle_groups WHERE id IN ({placeholders})", tuple(group_ids)
        ).fetchone()[0]
        if found != len(group_ids):
            raise HTTPException(status_code=422, detail="Unknown muscle group")

    with conn:  # one transaction: replace the whole plan or nothing
        conn.execute("DELETE FROM plan_days")
        conn.executemany(
            "INSERT INTO plan_days (weekday, muscle_group_id) VALUES (?, ?)",
            [(day.weekday, g) for day in body.days for g in day.muscle_group_ids],
        )
    return _read_plan(conn)
