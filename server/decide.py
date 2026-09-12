"""Reglas de disparo puras. Sin I/O, sin modelo."""
from datetime import datetime, timedelta, date
from statistics import median
from zoneinfo import ZoneInfo

QUIET_START, QUIET_END = 22, 8      # hora local del paciente
ANTISPAM_HOURS = 20
SILENCE_HOURS = 48
MIN_BASELINE_DAYS = 3
BASELINE_WINDOW = 14

def _baseline(history: list[dict], key: str) -> float | None:
    vals = [r[key] for r in history[-BASELINE_WINDOW:] if r.get(key) is not None]
    return median(vals) if len(vals) >= MIN_BASELINE_DAYS else None

def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

def triggers(signals: list[dict], plan: dict | None, last_checkin_at: str | None,
             now: datetime, tz: str) -> list[str]:
    local = now.astimezone(ZoneInfo(tz))
    if local.hour >= QUIET_START or local.hour < QUIET_END:
        return []
    if last_checkin_at and now - _parse(last_checkin_at) < timedelta(hours=ANTISPAM_HOURS):
        return []
    out: list[str] = []
    if not signals:
        return ["silence"]
    today, history = signals[-1], signals[:-1]
    last_day = date.fromisoformat(today["date"])
    if (local.date() - last_day) >= timedelta(hours=SILENCE_HOURS):
        return ["silence"]
    sleep_base = _baseline(history, "sleep_h")
    if sleep_base is not None and today.get("sleep_h") is not None and today["sleep_h"] < sleep_base - 1.5:
        out.append("sleep_drop")
    hrv_base = _baseline(history, "hrv_ms")
    if hrv_base is not None and today.get("hrv_ms") is not None and today["hrv_ms"] < 0.8 * hrv_base:
        out.append("hrv_drop")
    if today.get("mood_valence") is not None and today["mood_valence"] <= -0.5:
        out.append("low_mood")
    if plan and plan.get("homework") and plan.get("session_date"):
        days_since = (local.date() - date.fromisoformat(plan["session_date"])).days
        if days_since > 0 and days_since % 2 == 0:
            out.append("homework_day")
    return out
