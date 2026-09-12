import pytest
from server import workspace, config

def test_disabled_without_key(monkeypatch):
    monkeypatch.setattr(config, "AMBIGUOUS_API_KEY", "")
    assert workspace.enabled() is False
    assert workspace.deliver_brief("Ana", "x", None) == {"enabled": False}

def test_delivery_reports_document_failure_without_raising(monkeypatch):
    """Si el espacio de trabajo falla, el brief ya salió por correo: se informa, no se revienta."""
    monkeypatch.setattr(config, "AMBIGUOUS_API_KEY", "ak_test")
    monkeypatch.setattr(workspace, "call", lambda *a, **k: (500, {"error": "boom"}))
    out = workspace.deliver_brief("Ana", "x", "2026-09-13")
    assert out["document"]["ok"] is False and "task" not in out

def test_delivery_creates_document_then_task(monkeypatch):
    monkeypatch.setattr(config, "AMBIGUOUS_API_KEY", "ak_test")
    seen = []
    def fake(method, path, payload=None, as_agent=False):
        seen.append(path)
        if path == "/documents":
            return 201, {"id": "d1", "owner_username": "between"}
        return 201, {"task": {"task_key": "TASK-002"}}
    monkeypatch.setattr(workspace, "call", fake)
    out = workspace.deliver_brief("Ana", "x", "2026-09-13")
    assert seen == ["/documents", "/tasks"]
    assert out["document"]["owner"] == "between" and out["task"]["key"] == "TASK-002"
