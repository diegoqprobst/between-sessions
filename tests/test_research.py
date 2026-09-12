from server import research

RESULTS = [
    {"title": "Sleep and mental health", "url": "https://www.nih.gov/sleep", "text": "..."},
    {"title": "Remote work boundaries", "url": "https://apa.org/remote", "text": "..."},
    {"title": "More sleep", "url": "https://www.nih.gov/sleep2", "text": "..."},
]

def test_sources_are_unique_hosts_without_www():
    assert research.sources(RESULTS) == ["nih.gov", "apa.org"]

def test_format_reply_lists_options_and_sources():
    msg = research.format_reply(["dormir 7 horas", "cortar a las 6"], ["nih.gov", "apa.org"])
    assert "1. dormir 7 horas" in msg and "2. cortar a las 6" in msg
    assert "nih.gov, apa.org" in msg
    assert "plan:" in msg

def test_format_reply_without_focus_falls_back_to_self_plan():
    msg = research.format_reply([], [])
    assert "plan:" in msg and "No pude traer sugerencias" in msg

def test_format_reply_caps_at_four():
    msg = research.format_reply([f"foco {i}" for i in range(9)], [])
    assert "4. foco 3" in msg and "5. foco 4" not in msg


def test_local_prompt_disables_thinking(monkeypatch):
    """Un modelo local de razonamiento gastaba todo el presupuesto pensando y devolvía
    contenido vacío, así que `sugerir` siempre caía al mensaje de reserva."""
    from server import llm
    monkeypatch.setattr(llm, "is_local", lambda: True)
    assert research._system_prompt().startswith("/no_think")
    monkeypatch.setattr(llm, "is_local", lambda: False)
    assert not research._system_prompt().startswith("/no_think")

def test_suggest_falls_back_when_model_returns_nothing(monkeypatch):
    from server import llm
    monkeypatch.setattr(research, "enabled", lambda: True)
    monkeypatch.setattr(research, "search", lambda *a, **k: [{"url": "https://nih.gov/x", "title": "t", "text": ""}])
    class Msg:  content = ""
    class Choice: message = Msg()
    class Res: choices = [Choice()]
    class Chat:
        class completions:
            @staticmethod
            def create(**kw): return Res()
    class Client: chat = Chat()
    monkeypatch.setattr(llm, "sync_client", lambda: Client())
    assert "No pude traer sugerencias" in research.suggest()
