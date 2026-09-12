from server import channels
from server.channels import twilio, slack
from server.channels.twilio import parse_command, parse_self_plan

def test_router_dispatches_by_prefix(monkeypatch):
    calls = []
    monkeypatch.setattr(slack, "send", lambda to, body: calls.append(("slack", to)) or "s")
    monkeypatch.setattr(twilio, "send", lambda to, body: calls.append(("twilio", to)) or "t")
    channels.send("slack:U1", "x"); channels.send("whatsapp:+1", "x")
    assert calls == [("slack", "slack:U1"), ("twilio", "whatsapp:+1")]

def test_plan_command():
    assert parse_command("plan: dormir 7h; cortar a las 6 | tarea: caminar") == ("plan", "dormir 7h; cortar a las 6 | tarea: caminar")
    assert parse_command("plan:") is None

def test_parse_self_plan():
    sp = parse_self_plan("dormir 7h; cortar a las 6 | tarea: caminar 20 min")
    assert sp == {"watch": ["dormir 7h", "cortar a las 6"], "homework": "caminar 20 min"}
    assert parse_self_plan("dormir 7h") == {"watch": ["dormir 7h"], "homework": ""}
