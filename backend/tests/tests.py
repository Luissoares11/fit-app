import io
import os
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path

# Configure before the app package is imported (config reads env at import time).
DATA = Path(tempfile.mkdtemp(prefix="fit-data-"))
os.environ["DATA_DIR"] = str(DATA)
os.environ["APP_TOKEN"] = "test-token-123"
os.environ["FRONTEND_DIR"] = str(Path(__file__).resolve().parents[2] / "frontend")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app import config  # noqa: E402
from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


def make_jpeg(size=(800, 600), color=(200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def authed(client):
    r = client.post("/api/login", json={"token": "test-token-123"})
    assert r.status_code == 200
    return client


def test_db_schema_created():
    conn = sqlite3.connect(DATA / "fitness.db")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"sessions", "photos"} <= tables


def test_api_requires_auth(client):
    assert client.get("/api/sessions").status_code == 401
    assert client.get("/api/weights").status_code == 401
    assert client.post("/api/sessions", json={"date": "2026-01-01", "weight_kg": 80}).status_code == 401


def test_login_bad_token(client):
    r = client.post("/api/login", json={"token": "nope"})
    assert r.status_code == 401


def test_login_sets_cookie_and_cookie_grants_access(client):
    r = client.post("/api/login", json={"token": "test-token-123"})
    assert r.status_code == 200
    assert "fit_session" in r.cookies
    assert r.cookies["fit_session"] != "test-token-123"  # the raw token is never stored in the browser
    assert client.get("/api/sessions").status_code == 200


def test_foreign_cookie_named_token_does_not_grant_access(client):
    # Another app on the same host might set a cookie called "token"
    client.cookies.set("token", "test-token-123")
    assert client.get("/api/sessions").status_code == 401


def test_header_token_grants_access(client):
    r = client.get("/api/sessions", headers={"X-Token": "test-token-123"})
    assert r.status_code == 200


def test_logout(authed):
    r = authed.post("/api/logout")
    assert r.status_code == 200


def test_create_and_list_sessions(authed):
    r = authed.post("/api/sessions", json={"date": "2026-02-01", "weight_kg": 82.5, "note": "leg day"})
    assert r.status_code == 201
    sid = r.json()["id"]
    assert isinstance(sid, int)

    authed.post("/api/sessions", json={"date": "2026-02-10", "weight_kg": 81.0})
    rows = authed.get("/api/sessions").json()
    dates = [s["date"] for s in rows]
    assert dates == sorted(dates, reverse=True)
    first = next(s for s in rows if s["id"] == sid)
    assert first["weight_kg"] == 82.5
    assert first["note"] == "leg day"
    assert first["angles"] == []


def test_duplicate_date_is_409(authed):
    authed.post("/api/sessions", json={"date": "2026-03-01", "weight_kg": 80})
    r = authed.post("/api/sessions", json={"date": "2026-03-01", "weight_kg": 80})
    assert r.status_code == 409


@pytest.mark.parametrize("weight", [20, 400, -5, "abc"])
def test_invalid_weight_rejected(authed, weight):
    r = authed.post("/api/sessions", json={"date": "2026-04-01", "weight_kg": weight})
    assert r.status_code == 422


def test_invalid_date_rejected(authed):
    r = authed.post("/api/sessions", json={"date": "not-a-date", "weight_kg": 80})
    assert r.status_code == 422


def test_weights_endpoint(authed):
    authed.post("/api/sessions", json={"date": "2026-05-01", "weight_kg": 90})
    authed.post("/api/sessions", json={"date": "2026-05-02", "weight_kg": 89.5})
    rows = authed.get("/api/weights").json()
    assert rows == sorted(rows, key=lambda r: r["date"])
    assert {"date": "2026-05-01", "weight_kg": 90.0} in rows
    assert {"date": "2026-05-02", "weight_kg": 89.5} in rows


def test_photo_upload_get_and_thumb(authed):
    sid = authed.post("/api/sessions", json={"date": "2026-06-01", "weight_kg": 85}).json()["id"]

    # Session missing -> 404
    assert authed.post("/api/sessions/9999/photos/front", files={"file": ("a.jpg", make_jpeg(), "image/jpeg")}).status_code == 404

    # Bad angle -> 422
    assert authed.post(f"/api/sessions/{sid}/photos/top", files={"file": ("a.jpg", make_jpeg(), "image/jpeg")}).status_code == 422

    # Not an image -> 400
    r = authed.post(f"/api/sessions/{sid}/photos/front", files={"file": ("a.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 400

    # Valid upload -> 201
    r = authed.post(f"/api/sessions/{sid}/photos/front", files={"file": ("a.jpg", make_jpeg((3000, 2000)), "image/jpeg")})
    assert r.status_code == 201, r.text

    files_dir = DATA / "photos" / "2026-06-01"
    assert (files_dir / "front.jpg").exists()
    assert (files_dir / "front_thumb.jpg").exists()
    with Image.open(files_dir / "front.jpg") as im:
        assert max(im.size) <= 2000
    with Image.open(files_dir / "front_thumb.jpg") as im:
        assert max(im.size) <= 400

    full = authed.get(f"/api/sessions/{sid}/photos/front")
    assert full.status_code == 200
    assert full.headers["content-type"] == "image/jpeg"
    thumb = authed.get(f"/api/sessions/{sid}/photos/front", params={"thumb": True})
    assert thumb.status_code == 200
    assert len(thumb.content) < len(full.content)

    sessions = authed.get("/api/sessions").json()
    row = next(s for s in sessions if s["id"] == sid)
    assert row["angles"] == ["front"]


def test_reupload_replaces_and_keeps_single_row(authed):
    sid = authed.post("/api/sessions", json={"date": "2026-06-02", "weight_kg": 85}).json()["id"]
    assert authed.post(f"/api/sessions/{sid}/photos/side", files={"file": ("a.jpg", make_jpeg(), "image/jpeg")}).status_code == 201
    assert authed.post(f"/api/sessions/{sid}/photos/side", files={"file": ("a.jpg", make_jpeg(color=(0, 0, 255)), "image/jpeg")}).status_code == 201
    row = next(s for s in authed.get("/api/sessions").json() if s["id"] == sid)
    assert row["angles"] == ["side"]


def test_get_missing_photo_404(authed):
    sid = authed.post("/api/sessions", json={"date": "2026-06-03", "weight_kg": 85}).json()["id"]
    assert authed.get(f"/api/sessions/{sid}/photos/back").status_code == 404


def test_heic_path_is_registered():
    # pillow-heif should be registered so Pillow can open HEIC; just verify the opener loaded.
    from PIL import Image as PILImage
    assert ".heic" in PILImage.registered_extensions() or ".heif" in PILImage.registered_extensions()


def test_delete_session_removes_photos_and_files(authed):
    sid = authed.post("/api/sessions", json={"date": "2026-07-01", "weight_kg": 80}).json()["id"]
    authed.post(f"/api/sessions/{sid}/photos/front", files={"file": ("a.jpg", make_jpeg(), "image/jpeg")})
    assert (DATA / "photos" / "2026-07-01" / "front.jpg").exists()

    assert authed.delete(f"/api/sessions/{sid}").status_code == 204
    assert not (DATA / "photos" / "2026-07-01").exists()
    assert authed.get(f"/api/sessions/{sid}/photos/front").status_code == 404
    assert authed.delete(f"/api/sessions/{sid}").status_code == 404


def test_delete_cascades_photo_rows_in_db(authed):
    sid = authed.post("/api/sessions", json={"date": "2026-07-02", "weight_kg": 80}).json()["id"]
    authed.post(f"/api/sessions/{sid}/photos/back", files={"file": ("a.jpg", make_jpeg(), "image/jpeg")})
    authed.delete(f"/api/sessions/{sid}")
    conn = sqlite3.connect(DATA / "fitness.db")
    n = conn.execute("SELECT COUNT(*) FROM photos WHERE session_id = ?", (sid,)).fetchone()[0]
    conn.close()
    assert n == 0


def test_frontend_root_served(client):
    # Frontend dir is currently empty; the mount should still not break /api routes.
    assert client.get("/api/sessions").status_code == 401


def test_profile_defaults_then_save(authed):
    r = authed.get("/api/profile")
    assert r.status_code == 200
    assert r.json()["checkin_weekday"] == 0
    assert r.json()["checkin_every_weeks"] == 1
    assert r.json()["name"] is None

    body = {
        "name": "Luis", "start_weight_kg": 90, "goal_weight_kg": 80, "height_cm": 180, "age": 30,
        "start_date": "2025-09-01", "checkin_weekday": 2, "checkin_every_weeks": 2,
    }
    assert authed.put("/api/profile", json=body).json() == body
    assert authed.get("/api/profile").json() == body
    assert authed.put("/api/profile", json={**body, "start_date": "2025-02-30"}).status_code == 422  # not a real date

    # Saving again overwrites the single row instead of adding one
    authed.put("/api/profile", json={**body, "goal_weight_kg": 78})
    assert authed.get("/api/profile").json()["goal_weight_kg"] == 78
    conn = sqlite3.connect(DATA / "fitness.db")
    assert conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0] == 1
    conn.close()


@pytest.mark.parametrize(
    "field,value",
    [("height_cm", 10), ("age", 200), ("checkin_weekday", 7), ("checkin_weekday", -1), ("checkin_every_weeks", 0), ("checkin_every_weeks", 5), ("goal_weight_kg", 500)],
)
def test_profile_rejects_out_of_range(authed, field, value):
    assert authed.put("/api/profile", json={field: value}).status_code == 422


def test_profile_migrates_old_schema(tmp_path, monkeypatch):
    # A database made before the weekday schedule existed must upgrade in place
    old = tmp_path / "old.db"
    conn = sqlite3.connect(old)
    conn.executescript(
        """
        CREATE TABLE profile (
            id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT, start_weight_kg REAL,
            goal_weight_kg REAL, height_cm REAL, age INTEGER,
            checkin_every_days INTEGER NOT NULL DEFAULT 7
        );
        INSERT INTO profile (id, name, checkin_every_days) VALUES (1, 'Old', 14);
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(config, "DB_PATH", old)
    init_db()

    conn = sqlite3.connect(old)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(profile)")}
    row = conn.execute("SELECT name, checkin_weekday, checkin_every_weeks FROM profile").fetchone()
    conn.close()
    assert "checkin_every_days" not in cols
    assert row == ("Old", 0, 1)


# ---- Gym: library and plan (phase 1) ----

GYM_ROUTES = [
    ("get", "/api/muscle-groups"),
    ("post", "/api/muscle-groups"),
    ("patch", "/api/muscle-groups/1"),
    ("delete", "/api/muscle-groups/1"),
    ("get", "/api/exercises"),
    ("post", "/api/exercises"),
    ("patch", "/api/exercises/1"),
        ("delete", "/api/exercises/1"),
    ("get", "/api/plan"),
    ("put", "/api/plan"),
]


@pytest.mark.parametrize("method,path", GYM_ROUTES)
def test_gym_routes_require_auth(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def _group_ids(client):
    return {g["name"]: g["id"] for g in client.get("/api/muscle-groups").json()}


def _count(table):
    conn = sqlite3.connect(DATA / "fitness.db")
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    conn.close()
    return n


def _count_where(table, clause, value):
    conn = sqlite3.connect(DATA / "fitness.db")
    n = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {clause}", (value,)).fetchone()[0]
    conn.close()
    return n


def test_seed_is_idempotent(authed):
    groups_before, exercises_before = _count("muscle_groups"), _count("exercises")
    assert groups_before == 9
    assert exercises_before >= 20
    init_db()
    init_db()
    assert _count("muscle_groups") == groups_before
    assert _count("exercises") == exercises_before


def test_muscle_groups_in_order(authed):
    names = [g["name"] for g in authed.get("/api/muscle-groups").json()]
    assert names[:3] == ["chest", "back", "shoulders"]
    assert "forearms" in names


def test_exercise_create_list_rename_move(authed):
    groups = _group_ids(authed)
    r = authed.post("/api/exercises", json={"name": "  Test bench  ", "muscle_group_id": groups["chest"]})
    assert r.status_code == 201
    ex = r.json()
    assert ex["name"] == "Test bench"

    listed = authed.get("/api/exercises", params={"muscle_group_id": groups["chest"]}).json()
    assert any(e["id"] == ex["id"] for e in listed)
    assert all(e["muscle_group_id"] == groups["chest"] for e in listed)

    r = authed.patch(f"/api/exercises/{ex['id']}", json={"name": "Test bench inclinado"})
    assert r.json()["name"] == "Test bench inclinado"
    r = authed.patch(f"/api/exercises/{ex['id']}", json={"muscle_group_id": groups["triceps"]})
    assert r.json()["muscle_group_id"] == groups["triceps"]

    assert authed.delete(f"/api/exercises/{ex['id']}").status_code == 204
    assert all(e["id"] != ex["id"] for e in authed.get("/api/exercises").json())


def test_archive_is_gone(authed):
    assert authed.post("/api/exercises/1/archive").status_code in (404, 405)
    conn = sqlite3.connect(DATA / "fitness.db")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(exercises)")}
    conn.close()
    assert "archived" not in cols


def test_delete_unused_exercise(authed):
    groups = _group_ids(authed)
    ex = authed.post("/api/exercises", json={"name": "Test delete me", "muscle_group_id": groups["abs"]}).json()
    assert authed.delete(f"/api/exercises/{ex['id']}").status_code == 204
    assert _count_where("exercises", "id = ?", ex["id"]) == 0  # really gone
    assert authed.delete(f"/api/exercises/{ex['id']}").status_code == 404
    assert authed.delete("/api/exercises/999999").status_code == 404


def test_delete_exercise_with_history_removes_its_sets(authed):
    a = _exercise(authed, "Test deadlift history")
    b = _exercise(authed, "Test curl history")
    solo = authed.post(f"/api/exercises/{a}/sets", json={"date": "2025-05-01", "sets": [{"weight_kg": 100, "reps": 3}]})
    shared = authed.post(
        "/api/workouts",
        json={
            "date": "2025-05-02",
            "sets": [
                {"exercise_id": a, "weight_kg": 90, "reps": 5},
                {"exercise_id": b, "weight_kg": 12, "reps": 10},
            ],
        },
    )
    assert shared.status_code == 201

    assert authed.delete(f"/api/exercises/{a}").status_code == 204
    assert _count_where("exercises", "id = ?", a) == 0
    assert _count_where("workouts", "id = ?", solo.json()["workout_id"]) == 0  # only held the deleted exercise
    assert _count_where("workouts", "id = ?", shared.json()["id"]) == 1  # still has curls
    assert authed.get(f"/api/exercises/{b}/records").json()["history"][0]["sets"][0]["reps"] == 10


def test_create_muscle_group(authed):
    r = authed.post("/api/muscle-groups", json={"name": "  Calves  "})
    assert r.status_code == 201
    assert r.json()["name"] == "calves"
    assert "calves" in [g["name"] for g in authed.get("/api/muscle-groups").json()]
    assert authed.post("/api/muscle-groups", json={"name": "CALVES"}).status_code == 409
    assert authed.post("/api/muscle-groups", json={"name": "chest"}).status_code == 409
    assert authed.post("/api/muscle-groups", json={"name": "   "}).status_code == 422
    assert authed.post("/api/muscle-groups", json={"name": "x" * 41}).status_code == 422

    # A new group can hold exercises straight away
    ex = authed.post("/api/exercises", json={"name": "Test seated calf raise", "muscle_group_id": r.json()["id"]})
    assert ex.status_code == 201


def test_rename_muscle_group(authed):
    grp = authed.post("/api/muscle-groups", json={"name": "Test rename"}).json()
    ex = authed.post("/api/exercises", json={"name": "Test renamed lift", "muscle_group_id": grp["id"]}).json()

    r = authed.patch(f"/api/muscle-groups/{grp['id']}", json={"name": "  Test renamed  "})
    assert r.status_code == 200
    assert r.json() == {"id": grp["id"], "name": "test renamed"}
    listed = authed.get("/api/exercises", params={"muscle_group_id": grp["id"]}).json()
    assert [e["id"] for e in listed] == [ex["id"]]  # exercises follow the group by id

    assert authed.patch(f"/api/muscle-groups/{grp['id']}", json={"name": "chest"}).status_code == 409
    assert authed.patch(f"/api/muscle-groups/{grp['id']}", json={"name": "  "}).status_code == 422
    assert authed.patch("/api/muscle-groups/999999", json={"name": "Nope"}).status_code == 404


def test_delete_muscle_group(authed):
    empty = authed.post("/api/muscle-groups", json={"name": "Test empty"}).json()["id"]
    assert authed.delete(f"/api/muscle-groups/{empty}").status_code == 204
    assert _count_where("muscle_groups", "id = ?", empty) == 0
    assert authed.delete(f"/api/muscle-groups/{empty}").status_code == 404

    used = authed.post("/api/muscle-groups", json={"name": "Test used"}).json()["id"]
    ex = authed.post("/api/exercises", json={"name": "Test used lift", "muscle_group_id": used}).json()["id"]
    r = authed.delete(f"/api/muscle-groups/{used}")
    assert r.status_code == 409
    assert "exercises" in r.json()["detail"]

    # An exercise with logged sets blocks the delete too
    authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-07-01", "sets": [{"weight_kg": 20, "reps": 5}]})
    assert authed.delete(f"/api/muscle-groups/{used}").status_code == 409
    assert _count_where("muscle_groups", "id = ?", used) == 1


def test_delete_muscle_group_in_plan_is_refused(authed):
    grp = authed.post("/api/muscle-groups", json={"name": "Test planned"}).json()["id"]
    plan = authed.get("/api/plan").json()
    authed.put("/api/plan", json={"days": plan["days"] + [{"weekday": 6, "muscle_group_ids": [grp]}]})
    r = authed.delete(f"/api/muscle-groups/{grp}")
    assert r.status_code == 409
    assert "plan" in r.json()["detail"]

    authed.put("/api/plan", json=plan)  # restore the plan for later tests
    assert authed.delete(f"/api/muscle-groups/{grp}").status_code == 204


def test_deleted_or_renamed_group_does_not_come_back_on_restart(authed):
    grp = authed.post("/api/muscle-groups", json={"name": "Test restart"}).json()
    authed.patch(f"/api/muscle-groups/{grp['id']}", json={"name": "Test restart renamed"})
    groups_before = _count("muscle_groups")
    init_db()
    init_db()
    assert _count("muscle_groups") == groups_before
    assert _count_where("muscle_groups", "name = ?", "test restart") == 0
    assert _count_where("muscle_groups", "name = ?", "chest") == 1  # defaults are not duplicated either


def test_duplicate_exercise_name_per_group(authed):
    groups = _group_ids(authed)
    body = {"name": "Test curl", "muscle_group_id": groups["biceps"]}
    assert authed.post("/api/exercises", json=body).status_code == 201
    assert authed.post("/api/exercises", json=body).status_code == 409
    # Same name in another group is allowed
    other = {"name": "Test curl", "muscle_group_id": groups["forearms"]}
    assert authed.post("/api/exercises", json=other).status_code == 201


def test_exercise_rename_into_duplicate_is_409(authed):
    groups = _group_ids(authed)
    a = authed.post("/api/exercises", json={"name": "Test A", "muscle_group_id": groups["shoulders"]}).json()
    authed.post("/api/exercises", json={"name": "Test B", "muscle_group_id": groups["shoulders"]})
    assert authed.patch(f"/api/exercises/{a['id']}", json={"name": "Test B"}).status_code == 409


def test_exercise_unknown_group_and_blank_name_are_422(authed):
    groups = _group_ids(authed)
    assert authed.post("/api/exercises", json={"name": "Test X", "muscle_group_id": 9999}).status_code == 422
    assert authed.post("/api/exercises", json={"name": "   ", "muscle_group_id": groups["chest"]}).status_code == 422
    ex = authed.post("/api/exercises", json={"name": "Test Y", "muscle_group_id": groups["chest"]}).json()
    assert authed.patch(f"/api/exercises/{ex['id']}", json={"muscle_group_id": 9999}).status_code == 422
    assert authed.patch(f"/api/exercises/{ex['id']}", json={"name": None}).status_code == 422
    assert authed.patch("/api/exercises/999999", json={"name": "Z"}).status_code == 404


def test_plan_round_trip_and_replace(authed):
    g = _group_ids(authed)
    plan = {
        "days": [
            {"weekday": 0, "muscle_group_ids": [g["chest"], g["triceps"]]},
            {"weekday": 1, "muscle_group_ids": [g["back"], g["biceps"]]},
            {"weekday": 4, "muscle_group_ids": [g["chest"]]},
        ]
    }
    assert authed.put("/api/plan", json=plan).status_code == 200
    assert authed.get("/api/plan").json() == plan

    replacement = {"days": [{"weekday": 6, "muscle_group_ids": [g["legs"]]}]}
    authed.put("/api/plan", json=replacement)
    assert authed.get("/api/plan").json() == replacement


@pytest.mark.parametrize(
    "days",
    [
        [{"weekday": 0, "muscle_group_ids": [1]}, {"weekday": 0, "muscle_group_ids": [2]}],  # duplicate weekday
        [{"weekday": 7, "muscle_group_ids": [1]}],  # out of range
        [{"weekday": 0, "muscle_group_ids": []}],  # empty training day
        [{"weekday": 0, "muscle_group_ids": [1, 1]}],  # duplicate group in a day
    ],
)
def test_plan_invalid_shapes_are_422(authed, days):
    assert authed.put("/api/plan", json={"days": days}).status_code == 422


def test_plan_unknown_group_is_422_and_keeps_old_plan(authed):
    g = _group_ids(authed)
    good = {"days": [{"weekday": 2, "muscle_group_ids": [g["shoulders"]]}]}
    authed.put("/api/plan", json=good)
    bad = {"days": [{"weekday": 3, "muscle_group_ids": [g["shoulders"], 9999]}]}
    assert authed.put("/api/plan", json=bad).status_code == 422
    assert authed.get("/api/plan").json() == good


# ---- Gym: records and quick log (phase 2) ----

from app import records  # noqa: E402


def S(id, date, weight, reps):
    return {"id": id, "date": date, "weight_kg": weight, "reps": reps}


def test_epley_and_e1rm_limit():
    assert round(records.epley(100, 10), 1) == 133.3
    sets = [S(1, "2026-01-01", 100, 12), S(2, "2026-01-02", 200, 13)]
    best = records.best_e1rm(sets)
    assert best["set"]["id"] == 1  # 13 reps is above the 12 rep limit
    assert round(best["raw"], 1) == 140.0


def test_heaviest_ties_prefer_reps_then_recent_date():
    assert records.heaviest([S(1, "2026-01-01", 100, 3), S(2, "2026-01-02", 100, 5)])["id"] == 2
    assert records.heaviest([S(1, "2026-01-01", 100, 3), S(2, "2026-01-05", 100, 3)])["id"] == 2
    assert records.heaviest([S(1, "2026-01-01", 0, 30)]) is None  # bodyweight is not "heaviest"


def test_best_by_reps_keeps_recent_date_on_equal_weight():
    sets = [S(1, "2026-01-01", 80, 8), S(2, "2026-01-09", 80, 8), S(3, "2026-01-05", 75, 8), S(4, "2026-01-03", 60, 12)]
    best = records.best_by_reps(sets)
    assert best[8]["id"] == 2
    assert best[12]["weight_kg"] == 60


def test_most_reps_only_from_bodyweight_sets():
    assert records.most_reps([S(1, "2026-01-01", 0, 15), S(2, "2026-01-01", 50, 30)]) == 15
    assert records.most_reps([S(1, "2026-01-01", 50, 30)]) is None


def test_first_set_reports_no_prs():
    assert records.evaluate([], [S(1, "2026-01-01", 100, 5)]) == []
    assert records.evaluate([], [S(1, "2026-01-01", 0, 10)]) == []


def test_ties_are_not_prs():
    history = [S(1, "2026-01-01", 100, 5)]
    assert records.evaluate(history, [S(2, "2026-01-02", 100, 5)]) == []


def test_heaviest_and_rep_best_and_e1rm():
    history = [S(1, "2026-01-01", 100, 5)]
    prs = records.evaluate(history, [S(2, "2026-01-02", 105, 5)])
    types = {p["type"] for p in prs}
    assert types == {"heaviest", "rep_best", "e1rm"}
    assert {"type": "heaviest", "weight_kg": 105, "reps": 5} in prs
    assert {"type": "rep_best", "reps": 5, "weight_kg": 105} in prs


def test_first_time_a_rep_count_is_not_rep_best():
    history = [S(1, "2026-01-01", 100, 5)]
    prs = records.evaluate(history, [S(2, "2026-01-02", 90, 3)])
    assert all(p["type"] != "rep_best" for p in prs)


def test_most_reps_needs_an_earlier_bodyweight_set():
    assert records.evaluate([S(1, "2026-01-01", 0, 10)], [S(2, "2026-01-02", 0, 12)]) == [
        {"type": "most_reps", "reps": 12}
    ]
    assert records.evaluate([], [S(1, "2026-01-01", 0, 10)]) == []


def test_sets_in_one_request_are_evaluated_in_order():
    history = [S(1, "2026-01-01", 100, 5)]
    new = [S(2, "2026-01-02", 105, 3), S(3, "2026-01-02", 110, 3)]
    prs = records.evaluate(history, new)
    heavy = [p for p in prs if p["type"] == "heaviest"]
    assert heavy == [
        {"type": "heaviest", "weight_kg": 105, "reps": 3},
        {"type": "heaviest", "weight_kg": 110, "reps": 3},
    ]


def _exercise(client, name):
    groups = _group_ids(client)
    return client.post("/api/exercises", json={"name": name, "muscle_group_id": groups["legs"]}).json()["id"]


def test_quick_log_creates_then_appends_to_same_day(authed):
    ex = _exercise(authed, "Test squat log")
    first = authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-03-01", "sets": [{"weight_kg": 60, "reps": 8}]})
    assert first.status_code == 201
    assert first.json()["new_prs"] == []  # very first set ever

    second = authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-03-01", "sets": [{"weight_kg": 60, "reps": 6}, {"weight_kg": 60, "reps": 5}]})
    assert second.json()["workout_id"] == first.json()["workout_id"]

    rec = authed.get(f"/api/exercises/{ex}/records").json()
    day = rec["history"][0]
    assert day["date"] == "2025-03-01"
    assert [s["reps"] for s in day["sets"]] == [8, 6, 5]

    conn = sqlite3.connect(DATA / "fitness.db")
    orders = [r[0] for r in conn.execute("SELECT set_order FROM workout_sets WHERE workout_id = ? AND exercise_id = ? ORDER BY set_order", (first.json()["workout_id"], ex))]
    conn.close()
    assert orders == [1, 2, 3]


def test_quick_log_returns_new_pr_banner_data(authed):
    ex = _exercise(authed, "Test bench pr")
    authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-04-01", "sets": [{"weight_kg": 80, "reps": 5}]})
    r = authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-04-02", "sets": [{"weight_kg": 85, "reps": 5}]})
    types = {p["type"] for p in r.json()["new_prs"]}
    assert {"heaviest", "rep_best", "e1rm"} <= types


def test_quick_log_rejects_future_and_bad_values_and_saves_nothing(authed):
    from datetime import timedelta
    from datetime import date as d

    ex = _exercise(authed, "Test validation")
    tomorrow = (d.today() + timedelta(days=1)).isoformat()
    assert authed.post(f"/api/exercises/{ex}/sets", json={"date": tomorrow, "sets": [{"weight_kg": 50, "reps": 5}]}).status_code == 422
    assert authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-05-01", "sets": [{"weight_kg": -1, "reps": 5}]}).status_code == 422
    assert authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-05-01", "sets": [{"weight_kg": 50, "reps": 0}]}).status_code == 422
    assert authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-05-01", "sets": []}).status_code == 422

    # One bad set in a batch means nothing is saved
    before = authed.get(f"/api/exercises/{ex}/records").json()["history"]
    r = authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-05-01", "sets": [{"weight_kg": 50, "reps": 5}, {"weight_kg": 50, "reps": 500}]})
    assert r.status_code == 422
    assert authed.get(f"/api/exercises/{ex}/records").json()["history"] == before


def test_quick_log_past_date_and_bodyweight_accepted(authed):
    ex = _exercise(authed, "Test pull-up")
    r = authed.post(f"/api/exercises/{ex}/sets", json={"date": "2019-06-01", "sets": [{"weight_kg": 0, "reps": 12}]})
    assert r.status_code == 201
    assert authed.get(f"/api/exercises/{ex}/records").json()["most_reps"] == 12


def test_quick_log_missing_exercise_is_404(authed):
    ex = _exercise(authed, "Test deleted log")
    authed.delete(f"/api/exercises/{ex}")
    body = {"date": "2025-06-01", "sets": [{"weight_kg": 40, "reps": 10}]}
    assert authed.post(f"/api/exercises/{ex}/sets", json=body).status_code == 404
    assert authed.post("/api/exercises/999999/sets", json=body).status_code == 404


def test_records_empty_state(authed):
    ex = _exercise(authed, "Test empty")
    rec = authed.get(f"/api/exercises/{ex}/records").json()
    assert rec == {"exercise_id": ex, "heaviest": None, "best_e1rm": None, "by_reps": [], "most_reps": None, "history": []}
    assert authed.get("/api/exercises/999999/records").status_code == 404


def test_records_populated_and_history_newest_first(authed):
    ex = _exercise(authed, "Test full")
    authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-07-01", "sets": [{"weight_kg": 100, "reps": 3}, {"weight_kg": 80, "reps": 8}]})
    authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-07-08", "sets": [{"weight_kg": 90, "reps": 8}]})
    rec = authed.get(f"/api/exercises/{ex}/records").json()
    assert rec["heaviest"] == {"weight_kg": 100, "reps": 3, "date": "2025-07-01"}
    # 90 x 8 = 114.0 beats 100 x 3 = 110.0
    assert rec["best_e1rm"] == {"value": 114.0, "weight_kg": 90, "reps": 8, "date": "2025-07-08"}
    assert rec["by_reps"] == [
        {"reps": 3, "weight_kg": 100, "date": "2025-07-01"},
        {"reps": 8, "weight_kg": 90, "date": "2025-07-08"},
    ]
    assert rec["most_reps"] is None
    assert [h["date"] for h in rec["history"]] == ["2025-07-08", "2025-07-01"]
    assert [s["weight_kg"] for s in rec["history"][1]["sets"]] == [100, 80]


def test_edit_set_validates_and_updates_records(authed):
    ex = _exercise(authed, "Test edit")
    r = authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-08-01", "sets": [{"weight_kg": 60, "reps": 8}]})
    set_id = authed.get(f"/api/exercises/{ex}/records").json()["history"][0]["sets"][0]["id"]

    assert authed.patch(f"/api/sets/{set_id}", json={"reps": 0}).status_code == 422
    assert authed.patch(f"/api/sets/{set_id}", json={"weight_kg": None}).status_code == 422
    assert authed.patch("/api/sets/999999", json={"reps": 5}).status_code == 404

    updated = authed.patch(f"/api/sets/{set_id}", json={"weight_kg": 65}).json()
    assert updated["weight_kg"] == 65 and updated["reps"] == 8
    assert authed.get(f"/api/exercises/{ex}/records").json()["heaviest"]["weight_kg"] == 65


def test_deleting_last_set_removes_workout_but_one_of_many_keeps_it(authed):
    ex = _exercise(authed, "Test delete")
    r = authed.post(f"/api/exercises/{ex}/sets", json={"date": "2025-09-01", "sets": [{"weight_kg": 50, "reps": 5}, {"weight_kg": 50, "reps": 5}]})
    workout_id = r.json()["workout_id"]
    first, second = r.json()["set_ids"]

    assert authed.delete(f"/api/sets/{first}").status_code == 204
    conn = sqlite3.connect(DATA / "fitness.db")
    assert conn.execute("SELECT COUNT(*) FROM workouts WHERE id = ?", (workout_id,)).fetchone()[0] == 1
    conn.close()

    assert authed.delete(f"/api/sets/{second}").status_code == 204
    conn = sqlite3.connect(DATA / "fitness.db")
    assert conn.execute("SELECT COUNT(*) FROM workouts WHERE id = ?", (workout_id,)).fetchone()[0] == 0
    conn.close()
    assert authed.delete(f"/api/sets/{second}").status_code == 404


GYM_LOG_ROUTES = [
    ("post", "/api/exercises/1/sets"),
    ("get", "/api/exercises/1/records"),
    ("patch", "/api/sets/1"),
    ("delete", "/api/sets/1"),
]


@pytest.mark.parametrize("method,path", GYM_LOG_ROUTES)
def test_log_routes_require_auth(client, method, path):
    assert getattr(client, method)(path).status_code == 401


# ---- Gym: guided workout (phase 3) ----


def _set_rows(client, exercise_id):
    conn = sqlite3.connect(DATA / "fitness.db")
    rows = conn.execute(
        "SELECT ws.workout_id, ws.set_order, ws.weight_kg, ws.reps FROM workout_sets ws "
        "WHERE ws.exercise_id = ? ORDER BY ws.id",
        (exercise_id,),
    ).fetchall()
    conn.close()
    return rows


def test_workout_routes_require_auth(client):
    assert client.post("/api/workouts", json={"date": "2025-01-01", "sets": []}).status_code == 401
    assert client.get("/api/exercises/last-sets", params={"exercise_ids": "1"}).status_code == 401


def test_last_sets_is_not_captured_by_id_routes(authed):
    r = authed.get("/api/exercises/last-sets", params={"exercise_ids": ""})
    assert r.status_code == 200
    assert r.json() == {}


def test_last_sets_rejects_non_numeric_ids(authed):
    assert authed.get("/api/exercises/last-sets", params={"exercise_ids": "1,abc"}).status_code == 422


def test_last_sets_uses_most_recent_workout_and_omits_never_logged(authed):
    logged = _exercise(authed, "Test last sets")
    never = _exercise(authed, "Test never used")
    authed.post(f"/api/exercises/{logged}/sets", json={"date": "2025-11-01", "sets": [{"weight_kg": 60, "reps": 8}, {"weight_kg": 60, "reps": 7}]})
    authed.post(f"/api/exercises/{logged}/sets", json={"date": "2025-11-08", "sets": [{"weight_kg": 65, "reps": 6}]})

    r = authed.get("/api/exercises/last-sets", params={"exercise_ids": f"{logged},{never}"}).json()
    assert r == {str(logged): {"date": "2025-11-08", "sets": [{"weight_kg": 65, "reps": 6}]}}


def test_workout_saves_everything_with_order_per_exercise(authed):
    a = _exercise(authed, "Test workout A")
    b = _exercise(authed, "Test workout B")
    r = authed.post("/api/workouts", json={
        "date": "2025-12-01",
        "note": "workout",
        "sets": [
            {"exercise_id": a, "weight_kg": 60, "reps": 8},
            {"exercise_id": b, "weight_kg": 20, "reps": 10},
            {"exercise_id": a, "weight_kg": 60, "reps": 7},
        ],
    })
    assert r.status_code == 201
    assert r.json()["new_prs"] == {}  # first ever sets

    workout_id = r.json()["id"]
    assert [(w, o, wt, reps) for w, o, wt, reps in _set_rows(authed, a)][-2:] == [
        (workout_id, 1, 60, 8),
        (workout_id, 2, 60, 7),
    ]
    assert _set_rows(authed, b)[-1] == (workout_id, 1, 20, 10)


def test_workout_new_prs_grouped_per_exercise(authed):
    a = _exercise(authed, "Test pr group A")
    b = _exercise(authed, "Test pr group B")
    authed.post(f"/api/exercises/{a}/sets", json={"date": "2025-12-02", "sets": [{"weight_kg": 100, "reps": 5}]})
    r = authed.post("/api/workouts", json={
        "date": "2025-12-03",
        "sets": [
            {"exercise_id": a, "weight_kg": 105, "reps": 5},
            {"exercise_id": b, "weight_kg": 20, "reps": 10},
        ],
    })
    prs = r.json()["new_prs"]
    assert set(prs) == {str(a)}  # B has no earlier set, so no PRs
    assert {p["type"] for p in prs[str(a)]} == {"heaviest", "rep_best", "e1rm"}


def test_workout_is_all_or_nothing(authed):
    ex = _exercise(authed, "Test workout validation")
    before = sqlite3.connect(DATA / "fitness.db").execute("SELECT COUNT(*) FROM workouts").fetchone()[0]

    unknown = {"date": "2025-12-04", "sets": [{"exercise_id": ex, "weight_kg": 50, "reps": 5}, {"exercise_id": 999999, "weight_kg": 50, "reps": 5}]}
    assert authed.post("/api/workouts", json=unknown).status_code == 422

    bad_set = {"date": "2025-12-04", "sets": [{"exercise_id": ex, "weight_kg": 50, "reps": 5}, {"exercise_id": ex, "weight_kg": 50, "reps": 0}]}
    assert authed.post("/api/workouts", json=bad_set).status_code == 422

    after = sqlite3.connect(DATA / "fitness.db").execute("SELECT COUNT(*) FROM workouts").fetchone()[0]
    assert after == before


def test_workout_rejects_future_empty_and_accepts_existing_exercise(authed):
    from datetime import date as d, timedelta

    ex = _exercise(authed, "Test workout exercise")
    tomorrow = (d.today() + timedelta(days=1)).isoformat()
    assert authed.post("/api/workouts", json={"date": tomorrow, "sets": [{"exercise_id": ex, "weight_kg": 50, "reps": 5}]}).status_code == 422
    assert authed.post("/api/workouts", json={"date": "2025-12-05", "sets": []}).status_code == 422

    r = authed.post("/api/workouts", json={"date": "2025-12-05", "sets": [{"exercise_id": ex, "weight_kg": 50, "reps": 5}]})
    assert r.status_code == 201


def test_legacy_portuguese_names_are_renamed_once(tmp_path, monkeypatch):
    # A database seeded before the English rename keeps its rows, just with new names
    old = tmp_path / "legacy.db"
    conn = sqlite3.connect(old)
    conn.executescript(
        """
        CREATE TABLE muscle_groups (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE);
        CREATE TABLE exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            muscle_group_id INTEGER NOT NULL REFERENCES muscle_groups(id), archived INTEGER NOT NULL DEFAULT 0,
            UNIQUE (name, muscle_group_id));
        INSERT INTO muscle_groups (id, name) VALUES (1, 'peito'), (2, 'tríceps');
        INSERT INTO exercises (name, muscle_group_id) VALUES ('Supino reto com barra', 1), ('Mergulhos', 2);
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(config, "DB_PATH", old)
    init_db()
    init_db()  # second run must not rename or duplicate anything

    conn = sqlite3.connect(old)
    groups = [r[0] for r in conn.execute("SELECT name FROM muscle_groups ORDER BY id")]
    exercises = sorted(r[0] for r in conn.execute("SELECT name FROM exercises"))
    conn.close()
    assert groups[:2] == ["chest", "triceps"]
    assert len(groups) == 9 and len(set(groups)) == 9
    assert "Flat barbell bench press" in exercises and "Dips" in exercises
    assert "Supino reto com barra" not in exercises
