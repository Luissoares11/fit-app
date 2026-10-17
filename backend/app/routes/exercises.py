import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from ..auth import require_token
from ..db import get_db
from ..importer import ImportFileError, read_rows
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
    # Exercises and plan days point at the group, so refuse rather than orphan them
    if conn.execute("SELECT 1 FROM exercises WHERE muscle_group_id = ? LIMIT 1", (group_id,)).fetchone():
        raise HTTPException(
            status_code=409, detail="This muscle group still has exercises. Move or delete them first"
        )
    if conn.execute("SELECT 1 FROM plan_days WHERE muscle_group_id = ? LIMIT 1", (group_id,)).fetchone():
        raise HTTPException(status_code=409, detail="This muscle group is in your weekly plan. Remove it from the plan first")
    conn.execute("DELETE FROM muscle_groups WHERE id = ?", (group_id,))


@router.get("/exercises")
def list_exercises(muscle_group_id: int | None = None, conn: sqlite3.Connection = Depends(get_db)):
    sql = "SELECT id, name, muscle_group_id FROM exercises"
    params: tuple = ()
    if muscle_group_id is not None:
        sql += " WHERE muscle_group_id = ?"
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


@router.delete("/exercises/{exercise_id}", status_code=204)
def delete_exercise(exercise_id: int, conn: sqlite3.Connection = Depends(get_db)):
    if conn.execute("SELECT 1 FROM exercises WHERE id = ?", (exercise_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    # The exercise's logged sets go with it (the app warns before this is called).
    # A workout left with no sets is removed too, as delete_set does.
    with conn:
        workout_ids = [
            r[0] for r in conn.execute("SELECT DISTINCT workout_id FROM workout_sets WHERE exercise_id = ?", (exercise_id,))
        ]
        conn.execute("DELETE FROM workout_sets WHERE exercise_id = ?", (exercise_id,))
        for workout_id in workout_ids:
            left = conn.execute("SELECT COUNT(*) FROM workout_sets WHERE workout_id = ?", (workout_id,)).fetchone()[0]
            if left == 0:
                conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
        conn.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))


EXERCISE_IMPORT_REQUIRED = ("exercise", "muscle_group")


@router.post("/exercises/import")
async def import_exercises(file: UploadFile, confirm: bool = Form(False), conn: sqlite3.Connection = Depends(get_db)):
    """Preview an exercises CSV (confirm=false) or import it (confirm=true). Unknown muscle groups are created on import."""
    content = await file.read()
    try:
        rows = read_rows(content, EXERCISE_IMPORT_REQUIRED)
    except ImportFileError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)

    group_ids = {r[0].lower(): r[1] for r in conn.execute("SELECT name, id FROM muscle_groups")}
    existing = {
        (r[0].lower(), r[1].lower())
        for r in conn.execute("SELECT e.name, g.name FROM exercises e JOIN muscle_groups g ON g.id = e.muscle_group_id")
    }
    seen: set[tuple[str, str]] = set()
    to_add, skipped, invalid = [], [], []
    new_groups: list[str] = []

    for line, row in rows:
        name, group = row["exercise"], row["muscle_group"].lower()
        if not name:
            invalid.append({"line": line, "reason": "exercise name is empty"})
            continue
        if not group:
            invalid.append({"line": line, "name": name, "reason": "muscle group is empty"})
            continue
        if len(name) > 80 or len(group) > 40:
            invalid.append({"line": line, "name": name, "reason": "name or muscle group is too long"})
            continue

        key = (name.lower(), group)
        if key in existing:
            skipped.append({"line": line, "name": name, "reason": f"already in {group}"})
            continue
        if key in seen:
            skipped.append({"line": line, "name": name, "reason": "repeated in this file"})
            continue
        seen.add(key)

        if group not in group_ids and group not in new_groups:
            new_groups.append(group)
        to_add.append({"name": name, "group": group})

    if confirm:
        with conn:
            for group in new_groups:
                cur = conn.execute("INSERT INTO muscle_groups (name) VALUES (?)", (group,))
                group_ids[group] = cur.lastrowid
            for exercise in to_add:
                conn.execute(
                    "INSERT INTO exercises (name, muscle_group_id) VALUES (?, ?)",
                    (exercise["name"], group_ids[exercise["group"]]),
                )
        return {"added": len(to_add), "skipped": len(skipped), "invalid": len(invalid), "new_muscle_groups": new_groups}

    return {"to_add": len(to_add), "skipped": skipped, "invalid": invalid, "new_muscle_groups": new_groups}
