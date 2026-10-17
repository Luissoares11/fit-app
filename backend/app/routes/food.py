import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile

from ..auth import require_token
from ..db import get_db
from ..importer import KCAL_MAX, KCAL_WARN, ImportFileError, read_rows, to_number
from ..nutrition import WEIGHT_LOSS_PACES, bmr, daily_deficit, intake_status, kcal, tdee
from ..schemas import FoodIn, FoodPatch, FoodPlanIn, FoodPlanNameIn, WeekdayPlansIn

router = APIRouter(prefix="/food", dependencies=[Depends(require_token)])

FOOD_COLUMNS = "id, name, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g"


def _food(conn: sqlite3.Connection, food_id: int) -> dict:
    row = conn.execute(
        f"SELECT {FOOD_COLUMNS}, (SELECT COUNT(*) FROM plan_items WHERE food_id = foods.id) AS plan_uses "
        "FROM foods WHERE id = ?",
        (food_id,),
    ).fetchone()
    return dict(row)


def _plan_exists(conn: sqlite3.Connection, plan_id: int) -> bool:
    return conn.execute("SELECT 1 FROM food_plans WHERE id = ?", (plan_id,)).fetchone() is not None


def _read_plan(conn: sqlite3.Connection, plan_id: int) -> dict:
    """One plan: its meals with items, and the kcal per item, per meal and for the whole day."""
    meals = conn.execute(
        "SELECT id, position, name FROM plan_meals WHERE plan_id = ? ORDER BY position", (plan_id,)
    ).fetchall()
    items = conn.execute(
        """
        SELECT pi.id, pi.plan_meal_id, pi.food_id, f.name AS food_name, f.kcal_per_100g, pi.grams
        FROM plan_items pi
        JOIN plan_meals pm ON pm.id = pi.plan_meal_id
        JOIN foods f ON f.id = pi.food_id
        WHERE pm.plan_id = ?
        ORDER BY pi.id
        """,
        (plan_id,),
    ).fetchall()

    by_meal: dict[int, list[dict]] = {}
    for it in items:
        by_meal.setdefault(it["plan_meal_id"], []).append(
            {
                "id": it["id"],
                "food_id": it["food_id"],
                "food_name": it["food_name"],
                "grams": it["grams"],
                "kcal": round(kcal(it["kcal_per_100g"], it["grams"]), 1),
            }
        )

    out, day_total = [], 0.0
    for m in meals:
        meal_items = by_meal.get(m["id"], [])
        meal_kcal = sum(i["kcal"] for i in meal_items)
        day_total += meal_kcal
        out.append({"id": m["id"], "position": m["position"], "name": m["name"], "items": meal_items, "kcal": round(meal_kcal, 1)})
    return {"meals": out, "kcal": round(day_total, 1)}


def _day_plan(conn: sqlite3.Connection, weekday: int) -> dict:
    row = conn.execute(
        "SELECT w.plan_id, p.name FROM food_weekdays w LEFT JOIN food_plans p ON p.id = w.plan_id WHERE w.weekday = ?",
        (weekday,),
    ).fetchone()
    if row is None or row["plan_id"] is None:
        return {"weekday": weekday, "plan_id": None, "plan_name": None, "meals": [], "kcal": 0.0}
    return {"weekday": weekday, "plan_id": row["plan_id"], "plan_name": row["name"], **_read_plan(conn, row["plan_id"])}


# ---- Food library ----

@router.get("/foods")
def list_foods(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        f"SELECT {FOOD_COLUMNS}, (SELECT COUNT(*) FROM plan_items WHERE food_id = foods.id) AS plan_uses "
        "FROM foods ORDER BY name COLLATE NOCASE"
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/foods", status_code=201)
def create_food(body: FoodIn, conn: sqlite3.Connection = Depends(get_db)):
    try:
        cur = conn.execute(
            "INSERT INTO foods (name, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g) VALUES (?, ?, ?, ?, ?)",
            (body.name, body.kcal_per_100g, body.protein_per_100g, body.carbs_per_100g, body.fat_per_100g),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A food with this name already exists")
    return _food(conn, cur.lastrowid)


@router.patch("/foods/{food_id}")
def update_food(food_id: int, body: FoodPatch, conn: sqlite3.Connection = Depends(get_db)):
    if conn.execute("SELECT 1 FROM foods WHERE id = ?", (food_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Food not found")
    changes = body.model_dump(exclude_unset=True)
    if any(v is None for k, v in changes.items() if k in ("name", "kcal_per_100g")):
        raise HTTPException(status_code=422, detail="Name and kcal cannot be empty")
    if changes:
        assignments = ", ".join(f"{column} = ?" for column in changes)
        try:
            conn.execute(f"UPDATE foods SET {assignments} WHERE id = ?", (*changes.values(), food_id))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="A food with this name already exists")
    return _food(conn, food_id)


@router.delete("/foods/{food_id}", status_code=204)
def delete_food(food_id: int, conn: sqlite3.Connection = Depends(get_db)):
    if conn.execute("SELECT 1 FROM foods WHERE id = ?", (food_id,)).fetchone() is None:
        raise HTTPException(status_code=404, detail="Food not found")
    # Confirmed in the app first: the food is removed from every meal of every plan it appears in
    with conn:
        conn.execute("DELETE FROM plan_items WHERE food_id = ?", (food_id,))
        conn.execute("DELETE FROM foods WHERE id = ?", (food_id,))


# ---- Plans ----

@router.get("/plans")
def list_plans(conn: sqlite3.Connection = Depends(get_db)):
    plans = conn.execute("SELECT id, name FROM food_plans ORDER BY name COLLATE NOCASE").fetchall()
    out = []
    for p in plans:
        read = _read_plan(conn, p["id"])
        weekdays = [
            r[0] for r in conn.execute("SELECT weekday FROM food_weekdays WHERE plan_id = ? ORDER BY weekday", (p["id"],))
        ]
        out.append({
            "id": p["id"],
            "name": p["name"],
            "meal_count": len(read["meals"]),
            "kcal": read["kcal"],
            "weekdays": weekdays,
        })
    return out


@router.post("/plans", status_code=201)
def create_plan(body: FoodPlanNameIn, conn: sqlite3.Connection = Depends(get_db)):
    try:
        cur = conn.execute("INSERT INTO food_plans (name) VALUES (?)", (body.name,))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A plan with this name already exists")
    return {"id": cur.lastrowid, "name": body.name, **_read_plan(conn, cur.lastrowid)}


@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute("SELECT id, name FROM food_plans WHERE id = ?", (plan_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"id": row["id"], "name": row["name"], **_read_plan(conn, plan_id)}


@router.patch("/plans/{plan_id}")
def rename_plan(plan_id: int, body: FoodPlanNameIn, conn: sqlite3.Connection = Depends(get_db)):
    if not _plan_exists(conn, plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    try:
        conn.execute("UPDATE food_plans SET name = ? WHERE id = ?", (body.name, plan_id))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A plan with this name already exists")
    return {"id": plan_id, "name": body.name, **_read_plan(conn, plan_id)}


@router.delete("/plans/{plan_id}", status_code=204)
def delete_plan(plan_id: int, conn: sqlite3.Connection = Depends(get_db)):
    if not _plan_exists(conn, plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    # Its meals go with it (cascade); weekdays that used it fall back to no plan
    conn.execute("DELETE FROM food_plans WHERE id = ?", (plan_id,))


@router.put("/plans/{plan_id}/meals")
def save_plan_meals(plan_id: int, body: FoodPlanIn, conn: sqlite3.Connection = Depends(get_db)):
    if not _plan_exists(conn, plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    # Check everything before touching the plan, so a bad plan never half-applies
    food_ids = {item.food_id for meal in body.meals for item in meal.items}
    if food_ids:
        placeholders = ", ".join("?" * len(food_ids))
        found = conn.execute(f"SELECT COUNT(*) FROM foods WHERE id IN ({placeholders})", tuple(food_ids)).fetchone()[0]
        if found != len(food_ids):
            raise HTTPException(status_code=422, detail="Unknown food")

    with conn:  # one transaction: replace this plan's meals or nothing
        conn.execute("DELETE FROM plan_meals WHERE plan_id = ?", (plan_id,))  # items go with them (cascade)
        for position, meal in enumerate(body.meals, start=1):
            cur = conn.execute(
                "INSERT INTO plan_meals (plan_id, position, name) VALUES (?, ?, ?)", (plan_id, position, meal.name)
            )
            conn.executemany(
                "INSERT INTO plan_items (plan_meal_id, food_id, grams) VALUES (?, ?, ?)",
                [(cur.lastrowid, item.food_id, item.grams) for item in meal.items],
            )
    return {"id": plan_id, **_read_plan(conn, plan_id)}


# ---- Weekdays ----

@router.get("/weekdays")
def get_weekdays(conn: sqlite3.Connection = Depends(get_db)):
    rows = {
        r["weekday"]: r
        for r in conn.execute(
            "SELECT w.weekday, w.plan_id, p.name FROM food_weekdays w LEFT JOIN food_plans p ON p.id = w.plan_id"
        ).fetchall()
    }
    return {"days": [
        {"weekday": d, "plan_id": rows[d]["plan_id"] if d in rows else None, "plan_name": rows[d]["name"] if d in rows else None}
        for d in range(7)
    ]}


@router.put("/weekdays")
def save_weekdays(body: WeekdayPlansIn, conn: sqlite3.Connection = Depends(get_db)):
    plan_ids = {d.plan_id for d in body.days if d.plan_id is not None}
    if plan_ids:
        placeholders = ", ".join("?" * len(plan_ids))
        found = conn.execute(f"SELECT COUNT(*) FROM food_plans WHERE id IN ({placeholders})", tuple(plan_ids)).fetchone()[0]
        if found != len(plan_ids):
            raise HTTPException(status_code=422, detail="Unknown plan")
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO food_weekdays (weekday, plan_id) VALUES (?, ?)",
            [(d.weekday, d.plan_id) for d in body.days],
        )
    return get_weekdays(conn)


@router.get("/today")
def today_plan(weekday: int | None = Query(None, ge=0, le=6), conn: sqlite3.Connection = Depends(get_db)):
    return _day_plan(conn, date.today().weekday() if weekday is None else weekday)


# ---- Overview ----

@router.get("/overview")
def overview(weekday: int | None = Query(None, ge=0, le=6), conn: sqlite3.Connection = Depends(get_db)):
    row = conn.execute(
        "SELECT sex, height_cm, age, weight_loss_pace, goal_weight_kg, start_weight_kg FROM profile WHERE id = 1"
    ).fetchone()
    profile = dict(row) if row else {}

    checkin = conn.execute("SELECT weight_kg FROM sessions ORDER BY date DESC LIMIT 1").fetchone()
    if checkin:
        weight, weight_source = checkin["weight_kg"], "checkin"
    elif profile.get("start_weight_kg"):
        weight, weight_source = profile["start_weight_kg"], "profile_start"
    else:
        weight, weight_source = None, None

    training_days = conn.execute("SELECT COUNT(DISTINCT weekday) FROM plan_days").fetchone()[0]

    missing = []
    if not profile.get("sex"):
        missing.append("sex")
    if not profile.get("height_cm"):
        missing.append("height")
    if not profile.get("age"):
        missing.append("age")
    if weight is None:
        missing.append("weight")
    if not profile.get("weight_loss_pace"):
        missing.append("weight loss pace")
    if not profile.get("goal_weight_kg"):
        missing.append("goal weight")

    bmr_kcal = tdee_kcal = goal_kcal = deficit = weeks_to_goal = None
    pace = profile.get("weight_loss_pace")
    weekly_loss = WEIGHT_LOSS_PACES.get(pace) if pace else None
    if not {"sex", "height", "age", "weight"} & set(missing):
        bmr_kcal = bmr(profile["sex"], weight, profile["height_cm"], profile["age"])
        tdee_kcal = tdee(bmr_kcal, training_days)
    if tdee_kcal is not None and weekly_loss is not None and profile.get("goal_weight_kg"):
        to_lose = weight - profile["goal_weight_kg"]
        if to_lose > 0:
            deficit = daily_deficit(weekly_loss)
            weeks_to_goal = to_lose / weekly_loss
        else:
            # Already at or below the goal weight: eat at maintenance
            deficit, weeks_to_goal = 0, 0
        goal_kcal = tdee_kcal - deficit

    day = _day_plan(conn, date.today().weekday() if weekday is None else weekday)

    # Average intake over the week, from the plan on each weekday. Needs a plan on all seven days.
    week = [_day_plan(conn, d) for d in range(7)]
    week_avg = intake_vs = status = week_days = None
    if all(d["plan_id"] is not None for d in week):
        week_avg = sum(d["kcal"] for d in week) / 7
        # Days whose planned kcal is under the weekly average
        week_days = [
            {"weekday": d["weekday"], "plan_name": d["plan_name"], "kcal": round(d["kcal"]), "below_average": d["kcal"] < week_avg}
            for d in week
        ]
        if goal_kcal is not None:
            intake_vs = week_avg - goal_kcal
            status = intake_status(week_avg, goal_kcal)
    else:
        missing.append("meal plan on every day")

    return {
        "weight_used": weight,
        "weight_source": weight_source,
        "bmr": round(bmr_kcal) if bmr_kcal is not None else None,
        "tdee": round(tdee_kcal) if tdee_kcal is not None else None,
        "weight_loss_pace": pace,
        "weekly_loss_kg": weekly_loss,
        "goal_weight_kg": profile.get("goal_weight_kg"),
        "weeks_to_goal": round(weeks_to_goal, 1) if weeks_to_goal is not None else None,
        "goal_kcal": round(goal_kcal) if goal_kcal is not None else None,
        "deficit": round(deficit) if deficit is not None else None,
        "training_days_per_week": training_days,
        "weekday": day["weekday"],
        "plan_name": day["plan_name"],
        "planned_meals": day["meals"],
        "day_kcal": day["kcal"],
        "week_kcal_avg": round(week_avg) if week_avg is not None else None,
        "intake_vs_goal": round(intake_vs) if intake_vs is not None else None,
        "intake_status": status,
        "week_days": week_days,
        "missing": missing,
    }


# ---- CSV import ----

FOOD_IMPORT_REQUIRED = ("name", "kcal_per_100g")
FOOD_MACROS = ("protein_per_100g", "carbs_per_100g", "fat_per_100g")


@router.post("/foods/import")
async def import_foods(file: UploadFile, confirm: bool = Form(False), conn: sqlite3.Connection = Depends(get_db)):
    """Preview a foods CSV (confirm=false) or import it (confirm=true). Invalid rows are skipped, the rest import."""
    content = await file.read()
    try:
        rows = read_rows(content, FOOD_IMPORT_REQUIRED)
    except ImportFileError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)

    existing = {r[0].lower() for r in conn.execute("SELECT name FROM foods")}
    seen: set[str] = set()
    to_add, skipped, invalid, warnings = [], [], [], []

    for line, row in rows:
        name = row["name"]
        if not name:
            invalid.append({"line": line, "reason": "name is empty"})
            continue
        if len(name) > 80:
            invalid.append({"line": line, "name": name, "reason": "name is longer than 80 characters"})
            continue
        try:
            kcal = to_number(row["kcal_per_100g"])
        except ValueError:
            invalid.append({"line": line, "name": name, "reason": "kcal is not a number"})
            continue
        if kcal is None:
            invalid.append({"line": line, "name": name, "reason": "kcal is empty"})
            continue
        if not 0 <= kcal <= KCAL_MAX:
            invalid.append({"line": line, "name": name, "reason": f"kcal must be between 0 and {KCAL_MAX} per 100 g"})
            continue

        macros, bad = {}, None
        for column in FOOD_MACROS:
            try:
                value = to_number(row.get(column, ""))
            except ValueError:
                bad = f"{column.split('_')[0]} is not a number"
                break
            if value is not None and not 0 <= value <= 100:
                bad = f"{column.split('_')[0]} must be between 0 and 100 g per 100 g"
                break
            macros[column] = value
        if bad:
            invalid.append({"line": line, "name": name, "reason": bad})
            continue

        key = name.lower()
        if key in existing:
            skipped.append({"line": line, "name": name, "reason": "already in your library"})
            continue
        if key in seen:
            skipped.append({"line": line, "name": name, "reason": "repeated in this file"})
            continue
        seen.add(key)

        if kcal > KCAL_WARN:
            warnings.append({"line": line, "name": name, "reason": f"{kcal:g} kcal is high for 100 g, check it is not per serving"})
        if sum(v or 0 for v in macros.values()) > 100:
            warnings.append({"line": line, "name": name, "reason": "protein + carbs + fat is more than 100 g per 100 g"})
        to_add.append({"name": name, "kcal_per_100g": kcal, **macros})

    if confirm:
        with conn:
            for food in to_add:
                conn.execute(
                    "INSERT INTO foods (name, kcal_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g) VALUES (?, ?, ?, ?, ?)",
                    (food["name"], food["kcal_per_100g"], food["protein_per_100g"], food["carbs_per_100g"], food["fat_per_100g"]),
                )
        return {"added": len(to_add), "skipped": len(skipped), "invalid": len(invalid)}

    return {"to_add": len(to_add), "skipped": skipped, "invalid": invalid, "warnings": warnings}
