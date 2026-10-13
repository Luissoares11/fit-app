import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import records
from ..auth import require_token
from ..db import get_db
from ..schemas import WorkoutIn
from .sets import _exercise_sets

router = APIRouter(dependencies=[Depends(require_token)])


@router.post("/workouts", status_code=201)
def create_workout(body: WorkoutIn, conn: sqlite3.Connection = Depends(get_db)):
    exercise_ids = {s.exercise_id for s in body.sets}
    placeholders = ", ".join("?" * len(exercise_ids))
    found = conn.execute(
        f"SELECT COUNT(*) FROM exercises WHERE id IN ({placeholders})", tuple(exercise_ids)
    ).fetchone()[0]
    if found != len(exercise_ids):
        raise HTTPException(status_code=422, detail="Unknown exercise")

    day = body.date.isoformat()
    # Everything logged before this workout, per exercise, for PR checks
    histories = {eid: _exercise_sets(conn, eid) for eid in exercise_ids}

    logged: dict[int, list[dict]] = {}
    order: dict[int, int] = {}
    with conn:  # the workout and all its sets are saved together or not at all
        workout_id = conn.execute(
            "INSERT INTO workouts (date, note) VALUES (?, ?)", (day, body.note)
        ).lastrowid
        for s in body.sets:
            # set_order follows array order, counted per exercise
            order[s.exercise_id] = order.get(s.exercise_id, 0) + 1
            cur = conn.execute(
                "INSERT INTO workout_sets (workout_id, exercise_id, set_order, weight_kg, reps) "
                "VALUES (?, ?, ?, ?, ?)",
                (workout_id, s.exercise_id, order[s.exercise_id], s.weight_kg, s.reps),
            )
            logged.setdefault(s.exercise_id, []).append(
                {"id": cur.lastrowid, "date": day, "weight_kg": s.weight_kg, "reps": s.reps}
            )

    new_prs = {}
    for eid, sets in logged.items():
        prs = records.evaluate(histories[eid], sets)
        if prs:
            new_prs[str(eid)] = prs
    return {"id": workout_id, "new_prs": new_prs}
