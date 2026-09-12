import pytest
from server.guard import parse_llama_guard

def test_safe():
    assert parse_llama_guard("safe") == {"ok": True, "risk": False, "categories": []}

def test_self_harm_is_risk():
    r = parse_llama_guard("unsafe\nS11")
    assert r["ok"] and r["risk"] and r["categories"] == ["S11"]

def test_other_category_is_not_risk():
    r = parse_llama_guard("unsafe\nS6,S7")
    assert r["ok"] and not r["risk"]

def test_garbage_has_no_verdict():
    assert parse_llama_guard("I think this is fine")["ok"] is False
    assert parse_llama_guard("")["ok"] is False


def test_guard_fails_closed_without_provider(monkeypatch):
    from server import guard, llm
    monkeypatch.setattr(llm, "configured", lambda: False)
    assert guard.assess("cualquier cosa") == {"ok": False, "risk": None, "categories": []}


RIESGO = [
    "ya no quiero seguir viviendo", "quiero matarme", "pienso en hacerme daño",
    "me quiero morir", "he pensado en quitarme la vida", "no vale la pena vivir",
    "I don't want to live anymore", "I want to kill myself", "thinking about hurting myself",
    "YA NO QUIERO SEGUIR VIVIENDO",
]
BENIGNO = [
    "me muero de sueño, dormí fatal", "me muero de hambre", "me voy a matar a trabajar esta semana",
    "dormí mal pero bien por lo demás", "hoy me sentí triste pero se me pasó",
    "tuve una entrega y me acosté a las 2",
]

@pytest.mark.parametrize("texto", RIESGO)
def test_phrase_net_catches_ideation(texto):
    from server.guard import matches_ideation
    assert matches_ideation(texto), texto

@pytest.mark.parametrize("texto", BENIGNO)
def test_phrase_net_ignores_idioms_and_normal_talk(texto):
    from server.guard import matches_ideation
    assert not matches_ideation(texto), texto

def test_phrase_net_decides_without_any_model(monkeypatch):
    from server import guard, llm
    monkeypatch.setattr(llm, "configured", lambda: False)
    v = guard.assess("ya no quiero seguir viviendo")
    assert v["ok"] and v["risk"] and v["source"] == "phrase"

def test_model_cannot_override_phrase_net(monkeypatch):
    from server import guard
    monkeypatch.setattr(guard, "_classify", lambda t: {"ok": True, "risk": False, "categories": []})
    assert guard.assess("quiero matarme")["risk"] is True
