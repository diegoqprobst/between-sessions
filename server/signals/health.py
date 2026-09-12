"""Health Auto Export (REST automation) JSON → filas diarias normalizadas."""
from collections import defaultdict

KEYS = ("sleep_h", "hrv_ms", "resting_hr", "steps", "mood_valence", "mood_labels")

def _day(value: str | None) -> str | None:
    if not value or len(value) < 10:
        return None
    return value[:10]

def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def normalize(payload: dict) -> list[dict]:
    data = payload.get("data", payload)
    days: dict[str, dict] = defaultdict(dict)
    for metric in data.get("metrics", []):
        name = (metric.get("name") or "").lower().replace(" ", "_")
        units = (metric.get("units") or "").lower()
        for p in metric.get("data", []):
            day = _day(p.get("sleepEnd") or p.get("date"))
            if not day:
                continue
            if name == "sleep_analysis":
                hrs = _num(p.get("asleep") if p.get("asleep") is not None else p.get("totalSleep", p.get("qty")))
                if hrs is not None:
                    days[day]["sleep_h"] = round(hrs / 60, 2) if units.startswith("min") else round(hrs, 2)
            elif name == "heart_rate_variability":
                days[day]["hrv_ms"] = _num(p.get("qty"))
            elif name == "resting_heart_rate":
                days[day]["resting_hr"] = _num(p.get("qty"))
            elif name in ("step_count", "steps"):
                days[day]["steps"] = (days[day].get("steps") or 0) + (_num(p.get("qty")) or 0)
    for s in data.get("stateOfMind", []):
        day = _day(s.get("start") or s.get("date"))
        v = _num(s.get("valence"))
        if not day or v is None:
            continue
        current = days[day].get("mood_valence")
        if current is None or v < current:  # nos quedamos con el peor momento del día
            days[day]["mood_valence"] = v
            days[day]["mood_labels"] = list(s.get("labels") or [])
    out = []
    for day in sorted(days):
        row = {"date": day}
        for k in KEYS:
            row[k] = days[day].get(k)
        out.append(row)
    return out
