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
