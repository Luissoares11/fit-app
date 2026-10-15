import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import records
from ..auth import require_token
from ..db import get_db
from ..schemas import SetPatch, SetsLogIn

router = APIRouter(dependencies=[Depends(require_token)])


def _exercise_sets(conn: sqlite3.Connection, exercise_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT ws.id, ws.workout_id, ws.set_order, ws.weight_kg, ws.reps, w.date
        FROM workout_sets ws
        JOIN workouts w ON w.id = ws.workout_id
        WHERE ws.exercise_id = ?
        ORDER BY ws.id
        """,
        (exercise_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/exercises/{exercise_id}/sets", status_code=201)
def log_sets(exercise_id: int, body: SetsLogIn, conn: sqlite3.Connection = Depends(get_db)):
    if conn.execute("SELECT 1 FROM exercises WHERE id = ?", (exercise_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    day = body.date.isoformat()
    history = _exercise_sets(conn, exercise_id)  # everything logged before this request

    with conn:  # the workout and its sets are saved together or not at all
        existing = conn.execute(
            "SELECT id FROM workouts WHERE date = ? ORDER BY id DESC LIMIT 1", (day,)
        ).fetchone()
        if existing:
            workout_id = existing["id"]
        else:
            workout_id = conn.execute("INSERT INTO workouts (date) VALUES (?)", (day,)).lastrowid

        last_order = conn.execute(
            "SELECT COALESCE(MAX(set_order), 0) FROM workout_sets WHERE workout_id = ? AND exercise_id = ?",
            (workout_id, exercise_id),
        ).fetchone()[0]

        logged = []
        for offset, s in enumerate(body.sets, start=1):
            cur = conn.execute(
                "INSERT INTO workout_sets (workout_id, exercise_id, set_order, weight_kg, reps) "
                "VALUES (?, ?, ?, ?, ?)",
                (workout_id, exercise_id, last_order + offset, s.weight_kg, s.reps),
            )
            logged.append({"id": cur.lastrowid, "date": day, "weight_kg": s.weight_kg, "reps": s.reps})

    return {
        "workout_id": workout_id,
        "set_ids": [s["id"] for s in logged],
        "new_prs": records.evaluate(history, logged),
    }


@router.get("/exercises/{exercise_id}/records")
def exercise_records(exercise_id: int, conn: sqlite3.Connection = Depends(get_db)):
    if conn.execute("SELECT 1 FROM exercises WHERE id = ?", (exercise_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    sets = _exercise_sets(conn, exercise_id)

    heavy = records.heaviest(sets)
    e1rm = records.best_e1rm(sets)
    by_reps = records.best_by_reps(sets)

    grouped: dict[str, list[dict]] = {}
    for s in sorted(sets, key=lambda s: (s["workout_id"], s["set_order"])):
        grouped.setdefault(s["date"], []).append({"id": s["id"], "weight_kg": s["weight_kg"], "reps": s["reps"]})

    return {
        "exercise_id": exercise_id,
        "heaviest": (
            {"weight_kg": heavy["weight_kg"], "reps": heavy["reps"], "date": heavy["date"]} if heavy else None
        ),
        "best_e1rm": (
            {
                "value": round(e1rm["raw"], 1),
                "weight_kg": e1rm["set"]["weight_kg"],
                "reps": e1rm["set"]["reps"],
                "date": e1rm["set"]["date"],
            }
            if e1rm
            else None
        ),
        "by_reps": [
            {"reps": reps, "weight_kg": by_reps[reps]["weight_kg"], "date": by_reps[reps]["date"]}
            for reps in sorted(by_reps)
        ],
        "most_reps": records.most_reps(sets),
        "history": [
            {"date": day, "sets": grouped[day]} for day in sorted(grouped, reverse=True)
        ],
    }


@router.patch("/sets/{set_id}")
def update_set(set_id: int, body: SetPatch, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute(
        "SELECT id, workout_id, exercise_id, weight_kg, reps FROM workout_sets WHERE id = ?", (set_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Set not found")

    changes = body.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise HTTPException(status_code=422, detail="Weight and reps cannot be empty")

    weight = changes.get("weight_kg", row["weight_kg"])
    reps = changes.get("reps", row["reps"])
    conn.execute("UPDATE workout_sets SET weight_kg = ?, reps = ? WHERE id = ?", (weight, reps, set_id))
    return {
        "id": set_id,
        "workout_id": row["workout_id"],
        "exercise_id": row["exercise_id"],
        "weight_kg": weight,
        "reps": reps,
    }


@router.delete("/sets/{set_id}", status_code=204)
def delete_set(set_id: int, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute("SELECT workout_id FROM workout_sets WHERE id = ?", (set_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Set not found")

    with conn:
        conn.execute("DELETE FROM workout_sets WHERE id = ?", (set_id,))
        left = conn.execute(
            "SELECT COUNT(*) FROM workout_sets WHERE workout_id = ?", (row["workout_id"],)
        ).fetchone()[0]
        if left == 0:
            conn.execute("DELETE FROM workouts WHERE id = ?", (row["workout_id"],))
