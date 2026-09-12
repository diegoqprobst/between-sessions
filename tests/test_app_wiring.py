"""Estos tests existen porque `brief_agent` faltaba en app.py y nada lo detectó:
los tests unitarios no llamaban a las rutas, así que el NameError solo salió en producción."""
import ast, pytest
from fastapi.testclient import TestClient

def test_no_undefined_names_in_app():
    """Cada nombre con punto usado en app.py debe estar importado o definido allí."""
    src = open("server/app.py").read()
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.update(a.asname or a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.Import):
            imported.update(a.asname or a.name.split(".")[0] for a in node.names)
    defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    params = {a.arg for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
              for a in n.args.args + n.args.kwonlyargs}
    assigned = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                for t in n.targets if isinstance(t, ast.Name)}
    known = imported | defined | assigned | params | set(dir(__builtins__)) | {"self", "app"}
    used = {n.value.id for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    missing = {u for u in used if u not in known}
    assert not missing, f"nombres usados sin importar en app.py: {sorted(missing)}"

@pytest.fixture
def client(tmp_path, monkeypatch):
    from server import config, store
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.sqlite"))
    store.init_db()
    p = store.get_or_create_patient("slack:U1")
    store.set_patient(p["id"], ref="ana", name="Ana", stage="active")
    store.add_plan(p["id"], {"session_date": "2026-09-06", "next_session_date": "2026-09-13",
                             "watch": ["sueño"], "homework": "caminar"})
    from server import channels
    monkeypatch.setattr(channels, "send", lambda to, body: "stub")
    from server.app import app
    return TestClient(app)

def test_brief_route_reaches_the_agent(client, monkeypatch):
    """No comprobamos el texto, solo que la ruta llega al agente sin romperse."""
    from server.agent import brief as brief_agent
    monkeypatch.setattr(brief_agent, "compose", lambda *a, **k: "## Riesgo\nSin señales.")
    r = client.post("/brief", headers={"x-therapist-key": "dev-therapist-key"},
                    json={"patient_id": 1, "force": True})
    assert r.status_code == 200, r.text
    assert r.json()["results"][0]["status"] in ("sent", "awaiting_whatsapp", "denied")

def test_checkin_route_reaches_the_agent(client, monkeypatch):
    from server.agent import checkin as checkin_agent
    monkeypatch.setattr(checkin_agent, "open_question", lambda *a, **k: "¿Cómo dormiste?")
    r = client.post("/checkin", headers={"x-therapist-key": "dev-therapist-key"},
                    json={"patient_id": 1, "trigger": "sleep_drop"})
    assert r.status_code == 200, r.text
    assert r.json()["sent"] is True
