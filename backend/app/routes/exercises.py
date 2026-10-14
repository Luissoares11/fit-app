import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_token
from ..db import get_db
from ..schemas import ExerciseIn, ExercisePatch, MuscleGroupIn

router = APIRouter(dependencies=[Depends(require_token)])


def _group_exists(conn: sqlite3.Connection, group_id: int) -> bool:
    return conn.execute("SELECT 1 FROM muscle_groups WHERE id = ?", (group_id,)).fetchone() is not None


def _exercise(conn: sqlite3.Connection, exercise_id: int) -> dict:
    row = conn.execute(
        "SELECT id, name, muscle_group_id FROM exercises WHERE id = ?", (exercise_id,)
    ).fetchone()
    return dict(row)


@router.get("/muscle-groups")
def list_muscle_groups(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute("SELECT id, name FROM muscle_groups ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@router.post("/muscle-groups", status_code=201)
def create_muscle_group(body: MuscleGroupIn, conn: sqlite3.Connection = Depends(get_db)):
    try:
        cur = conn.execute("INSERT INTO muscle_groups (name) VALUES (?)", (body.name,))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="That muscle group already exists")
    return dict(conn.execute("SELECT id, name FROM muscle_groups WHERE id = ?", (cur.lastrowid,)).fetchone())


@router.patch("/muscle-groups/{group_id}")
def update_muscle_group(group_id: int, body: MuscleGroupIn, conn: sqlite3.Connection = Depends(get_db)):
    if not _group_exists(conn, group_id):
        raise HTTPException(status_code=404, detail="Muscle group not found")
    try:
        conn.execute("UPDATE muscle_groups SET name = ? WHERE id = ?", (body.name, group_id))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="That muscle group already exists")
    return dict(conn.execute("SELECT id, name FROM muscle_groups WHERE id = ?", (group_id,)).fetchone())


@router.delete("/muscle-groups/{group_id}", status_code=204)
def delete_muscle_group(group_id: int, conn: sqlite3.Connection = Depends(get_db)):
    if not _group_exists(conn, group_id):
        raise HTTPException(status_code=404, detail="Muscle group not found")
    # Exercises (archived ones too) and plan days point at the group, so refuse rather than orphan them
    if conn.execute("SELECT 1 FROM exercises WHERE muscle_group_id = ? LIMIT 1", (group_id,)).fetchone():
        raise HTTPException(
            status_code=409, detail="This muscle group still has exercises. Move or delete them first"
        )
    if conn.execute("SELECT 1 FROM plan_days WHERE muscle_group_id = ? LIMIT 1", (group_id,)).fetchone():
        raise HTTPException(status_code=409, detail="This muscle group is in your weekly plan. Remove it from the plan first")
    conn.execute("DELETE FROM muscle_groups WHERE id = ?", (group_id,))


@router.get("/exercises")
def list_exercises(muscle_group_id: int | None = None, conn: sqlite3.Connection = Depends(get_db)):
    sql = "SELECT id, name, muscle_group_id FROM exercises WHERE archived = 0"
    params: tuple = ()
    if muscle_group_id is not None:
        sql += " AND muscle_group_id = ?"
        params = (muscle_group_id,)
    rows = conn.execute(sql + " ORDER BY id", params).fetchall()
    return [dict(r) for r in rows]


@router.get("/exercises/last-sets")
def last_sets(exercise_ids: str, conn: sqlite3.Connection = Depends(get_db)):
    # Declared before /exercises/{id} routes so "last-sets" is never read as an id
    try:
        ids = [int(x) for x in exercise_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="exercise_ids must be comma-separated numbers")

    result = {}
    for exercise_id in ids:
        latest = conn.execute(
            """
            SELECT w.id, w.date FROM workouts w
            JOIN workout_sets ws ON ws.workout_id = w.id
            WHERE ws.exercise_id = ?
            ORDER BY w.date DESC, w.id DESC
            LIMIT 1
            """,
            (exercise_id,),
        ).fetchone()
        if latest is None:
            continue
        sets = conn.execute(
            "SELECT weight_kg, reps FROM workout_sets WHERE workout_id = ? AND exercise_id = ? ORDER BY set_order",
            (latest["id"], exercise_id),
        ).fetchall()
        result[str(exercise_id)] = {"date": latest["date"], "sets": [dict(s) for s in sets]}
    return result


@router.post("/exercises", status_code=201)
def create_exercise(body: ExerciseIn, conn: sqlite3.Connection = Depends(get_db)):
    if not _group_exists(conn, body.muscle_group_id):
        raise HTTPException(status_code=422, detail="Unknown muscle group")
    try:
        cur = conn.execute(
            "INSERT INTO exercises (name, muscle_group_id) VALUES (?, ?)",
            (body.name, body.muscle_group_id),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="That exercise already exists in this group")
    return _exercise(conn, cur.lastrowid)


@router.patch("/exercises/{exercise_id}")
def update_exercise(exercise_id: int, body: ExercisePatch, conn: sqlite3.Connection = Depends(get_db)):
    current = conn.execute(
        "SELECT name, muscle_group_id FROM exercises WHERE id = ?", (exercise_id,)
    ).fetchone()
    if current is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    changes = body.model_dump(exclude_unset=True)
    if any(v is None for k, v in changes.items() if k in ("name", "muscle_group_id")):
        raise HTTPException(status_code=422, detail="Name and muscle group cannot be empty")

    name = changes.get("name", current["name"])
    group_id = changes.get("muscle_group_id", current["muscle_group_id"])
    if not _group_exists(conn, group_id):
        raise HTTPException(status_code=422, detail="Unknown muscle group")
    try:
        conn.execute(
            "UPDATE exercises SET name = ?, muscle_group_id = ? WHERE id = ?",
            (name, group_id, exercise_id),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="That exercise already exists in this group")
    return _exercise(conn, exercise_id)


@router.post("/exercises/{exercise_id}/archive", status_code=204)
def archive_exercise(exercise_id: int, conn: sqlite3.Connection = Depends(get_db)):
    # Archived, not deleted: keeps the history of an exercise that has logged sets
    cur = conn.execute("UPDATE exercises SET archived = 1 WHERE id = ?", (exercise_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Exercise not found")


@router.delete("/exercises/{exercise_id}", status_code=204)
def delete_exercise(exercise_id: int, conn: sqlite3.Connection = Depends(get_db)):
    if conn.execute("SELECT 1 FROM exercises WHERE id = ?", (exercise_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    # Logged sets would be lost with it, so only exercises without history can be deleted
    if conn.execute("SELECT 1 FROM workout_sets WHERE exercise_id = ? LIMIT 1", (exercise_id,)).fetchone():
        raise HTTPException(status_code=409, detail="This exercise has logged sets. Archive it instead")
    conn.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
