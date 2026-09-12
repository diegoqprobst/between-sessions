import json
from server.signals.health import normalize

def load():
    return json.load(open("fixtures/health_sample.json"))

def test_seven_days():
    rows = normalize(load())
    assert [r["date"] for r in rows] == [f"2026-09-{d:02d}" for d in range(6, 13)]

def test_short_night_and_low_mood():
    by = {r["date"]: r for r in normalize(load())}
    assert by["2026-09-12"]["sleep_h"] == 5.1
    assert by["2026-09-12"]["hrv_ms"] == 36
    assert by["2026-09-12"]["mood_valence"] == -0.6
    assert by["2026-09-12"]["mood_labels"] == ["Anxious"]
    assert by["2026-09-07"]["mood_valence"] is None

def test_minutes_are_converted():
    payload = {"data": {"metrics": [{"name": "sleep_analysis", "units": "min",
               "data": [{"date": "2026-09-01 07:00:00 -0400", "asleep": 420}]}]}}
    assert normalize(payload)[0]["sleep_h"] == 7.0
