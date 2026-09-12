from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from server.decide import triggers

TZ = "America/New_York"
NOON = datetime(2026, 9, 10, 12, 0, tzinfo=ZoneInfo(TZ))

def rows(*sleep):
    base = datetime(2026, 9, 1)
    return [{"date": (base + timedelta(days=i)).strftime("%Y-%m-%d"), "sleep_h": s, "hrv_ms": 50,
             "resting_hr": 58, "steps": 6000, "mood_valence": None, "mood_labels": None}
            for i, s in enumerate(sleep)]

def test_sleep_drop_fires_against_median():
    r = rows(7.0, 7.1, 6.9, 7.2, 7.0, 6.8, 7.0, 7.1, 7.0, 5.1)
    assert "sleep_drop" in triggers(r, None, None, NOON, TZ)

def test_no_baseline_no_sleep_trigger():
    r = rows(7.0, 5.0)
    assert "sleep_drop" not in triggers(r, None, None, NOON, TZ)

def test_low_mood():
    r = rows(*[7.0] * 10)  # última fila = 2026-09-10, mismo día que NOON
    r[-1]["mood_valence"] = -0.6
    assert "low_mood" in triggers(r, None, None, NOON, TZ)

def test_silence_after_48h():
    r = rows(7.0, 7.0, 7.0)  # último dato 2026-09-03
    assert triggers(r, None, None, NOON, TZ) == ["silence"]

def test_antispam_20h():
    r = rows(7.0, 7.1, 6.9, 7.2, 7.0, 6.8, 7.0, 7.1, 7.0, 5.1)
    recent = (NOON - timedelta(hours=5)).astimezone(timezone.utc).isoformat(timespec="seconds")
    assert triggers(r, None, recent, NOON, TZ) == []

def test_quiet_hours():
    r = rows(7.0, 7.1, 6.9, 7.2, 7.0, 6.8, 7.0, 7.1, 7.0, 5.1)
    night = NOON.replace(hour=23)
    assert triggers(r, None, None, night, TZ) == []

def test_homework_day():
    r = rows(7.0, 7.0, 7.0, 7.0, 7.0, 7.0, 7.0, 7.0, 7.0, 7.0)
    plan = {"session_date": "2026-09-08", "homework": "Respiración 4-7-8"}
    assert "homework_day" in triggers(r, plan, None, NOON, TZ)
