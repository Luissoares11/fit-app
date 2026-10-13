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
    assert "token" in r.cookies
    assert client.get("/api/sessions").status_code == 200


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
    assert r.json()["checkin_every_days"] == 7
    assert r.json()["name"] is None

    body = {"name": "Luis", "start_weight_kg": 90, "goal_weight_kg": 80, "height_cm": 180, "age": 30, "checkin_every_days": 14}
    assert authed.put("/api/profile", json=body).json() == body
    assert authed.get("/api/profile").json() == body

    # Saving again overwrites the single row instead of adding one
    authed.put("/api/profile", json={**body, "goal_weight_kg": 78})
    assert authed.get("/api/profile").json()["goal_weight_kg"] == 78
    conn = sqlite3.connect(DATA / "fitness.db")
    assert conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0] == 1
    conn.close()


@pytest.mark.parametrize("field,value", [("height_cm", 10), ("age", 200), ("checkin_every_days", 0), ("goal_weight_kg", 500)])
def test_profile_rejects_out_of_range(authed, field, value):
    assert authed.put("/api/profile", json={field: value}).status_code == 422
