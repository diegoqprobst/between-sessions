from server.agent.brief import strip_fences, homework_summary

def test_strip_fences_removes_markdown_wrapper():
    assert strip_fences("```markdown\n## Riesgo\nNada.\n```") == "## Riesgo\nNada."
    assert strip_fences("```\n## A\n```") == "## A"

def test_strip_fences_leaves_plain_markdown_alone():
    assert strip_fences("## Riesgo\nNada.") == "## Riesgo\nNada."

def test_homework_summary_resolves_to_one_state():
    assert "No la hizo" in homework_summary([{"homework_done": False, "note": "n"}])
    assert "La hizo" in homework_summary([{"homework_done": True, "note": "n"}])
    assert "Parcial" in homework_summary([{"homework_done": True}, {"homework_done": False}])

def test_homework_summary_when_never_discussed():
    assert "No se habló" in homework_summary([{"homework_done": None}, {}])
