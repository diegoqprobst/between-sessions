import json, pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.sqlite"))
    from server import config, store
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.sqlite"))
    store.init_db()
    p = store.get_or_create_patient("slack:U1")
    store.set_patient(p["id"], ref="ana", name="Ana", stage="active", excluded_signals=["sueño"])
    store.add_plan(p["id"], {"session_date": "2026-09-06", "next_session_date": "2026-09-13",
                             "watch": ["sueño"], "homework": "caminar"})
    store.add_checkin(p["id"], {"trigger": "sleep_drop", "mood_1_5": 2, "note": "n"})
    store.add_brief(p["id"], "## Riesgo\nSin señales.")
    from server.app import app
    return TestClient(app)

def test_list_hides_contact_details(client):
    body = client.get("/api/patients").json()
    assert body["patients"][0]["name"] == "Ana"
    assert body["patients"][0]["channel"] == "slack"
    assert "phone" not in body["patients"][0]

def test_patient_includes_plan_and_consent(client):
    body = client.get("/api/patients/1").json()
    assert body["plan"]["homework"] == "caminar"
    assert body["consent"]["excluded_signals"] == ["sueño"]

def test_checkins_drop_internal_ids(client):
    c = client.get("/api/patients/1/checkins").json()["checkins"][0]
    assert c["mood_1_5"] == 2 and "patient_id" not in c

def test_brief_reports_approval_state(client):
    b = client.get("/api/patients/1/brief").json()
    assert b["approved"] is False and "Riesgo" in b["content"]

def test_unknown_patient_is_404(client):
    assert client.get("/api/patients/99").status_code == 404
