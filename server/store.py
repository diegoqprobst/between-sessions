import json, sqlite3, secrets
from datetime import datetime, timezone
from server import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
  id INTEGER PRIMARY KEY, phone TEXT UNIQUE NOT NULL, ref TEXT, name TEXT,
  therapist_email TEXT, auth0_sub TEXT, health_token TEXT UNIQUE,
  paused INTEGER DEFAULT 0, excluded_signals TEXT DEFAULT '[]',
  pending_trigger TEXT, pending_token TEXT, turns INTEGER DEFAULT 0,
  stage TEXT DEFAULT 'new', awaiting_brief INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY, patient_id INTEGER, session_num INTEGER, session_date TEXT,
  next_session_date TEXT, watch TEXT, homework TEXT, next_focus TEXT, risk_baseline TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY, patient_id INTEGER, date TEXT, sleep_h REAL, hrv_ms REAL,
  resting_hr REAL, steps REAL, mood_valence REAL, mood_labels TEXT, UNIQUE(patient_id, date));
CREATE TABLE IF NOT EXISTS checkins (
  id INTEGER PRIMARY KEY, patient_id INTEGER, at TEXT, trigger TEXT, question TEXT,
  mood_1_5 INTEGER, homework_done INTEGER, note TEXT, wants_to_discuss TEXT,
  risk_flag INTEGER DEFAULT 0, status TEXT);
CREATE TABLE IF NOT EXISTS briefs (
  id INTEGER PRIMARY KEY, patient_id INTEGER, at TEXT, content TEXT, approved INTEGER, sent INTEGER);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY, patient_id INTEGER, at TEXT, direction TEXT, body TEXT);
"""

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def connect() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db() -> None:
    with connect() as con:
        con.executescript(SCHEMA)

def _row(r) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    for k in ("excluded_signals", "watch", "mood_labels"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except ValueError:
                pass
    return d

def get_or_create_patient(phone: str) -> dict:
    with connect() as con:
        r = con.execute("SELECT * FROM patients WHERE phone=?", (phone,)).fetchone()
        if r:
            return _row(r)
        con.execute("INSERT INTO patients(phone, health_token, created_at) VALUES (?,?,?)",
                    (phone, secrets.token_urlsafe(12), now()))
        return _row(con.execute("SELECT * FROM patients WHERE phone=?", (phone,)).fetchone())

def get_patient(pid: int) -> dict | None:
    with connect() as con:
        return _row(con.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone())

def patient_by_token(token: str) -> dict | None:
    with connect() as con:
        return _row(con.execute("SELECT * FROM patients WHERE health_token=?", (token,)).fetchone())

def patient_by_ref(ref: str) -> dict | None:
    with connect() as con:
        return _row(con.execute("SELECT * FROM patients WHERE lower(ref)=lower(?)", (ref,)).fetchone())

def list_patients() -> list[dict]:
    with connect() as con:
        return [_row(r) for r in con.execute("SELECT * FROM patients ORDER BY id")]

def set_patient(pid: int, **fields) -> None:
    if not fields:
        return
    vals = [json.dumps(v) if isinstance(v, (list, dict)) else v for v in fields.values()]
    sets = ", ".join(f"{k}=?" for k in fields)
    with connect() as con:
        con.execute(f"UPDATE patients SET {sets} WHERE id=?", (*vals, pid))

def upsert_signal(pid: int, row: dict) -> None:
    with connect() as con:
        con.execute("""INSERT INTO signals(patient_id,date,sleep_h,hrv_ms,resting_hr,steps,mood_valence,mood_labels)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(patient_id,date) DO UPDATE SET
              sleep_h=COALESCE(excluded.sleep_h, signals.sleep_h),
              hrv_ms=COALESCE(excluded.hrv_ms, signals.hrv_ms),
              resting_hr=COALESCE(excluded.resting_hr, signals.resting_hr),
              steps=COALESCE(excluded.steps, signals.steps),
              mood_valence=COALESCE(excluded.mood_valence, signals.mood_valence),
              mood_labels=COALESCE(excluded.mood_labels, signals.mood_labels)""",
            (pid, row["date"], row.get("sleep_h"), row.get("hrv_ms"), row.get("resting_hr"),
             row.get("steps"), row.get("mood_valence"),
             json.dumps(row["mood_labels"]) if row.get("mood_labels") is not None else None))

def signals_since(pid: int, days: int) -> list[dict]:
    with connect() as con:
        return [_row(r) for r in con.execute(
            "SELECT * FROM signals WHERE patient_id=? AND date >= date('now', ?) ORDER BY date",
            (pid, f"-{days} days"))]

def add_plan(pid: int, plan: dict) -> None:
    with connect() as con:
        con.execute("""INSERT INTO plans(patient_id,session_num,session_date,next_session_date,watch,homework,next_focus,risk_baseline,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (pid, plan.get("session_num"), plan.get("session_date"), plan.get("next_session_date"),
             json.dumps(plan.get("watch", [])), plan.get("homework"), plan.get("next_focus"),
             plan.get("risk_baseline", "none"), now()))

def latest_plan(pid: int) -> dict | None:
    with connect() as con:
        return _row(con.execute("SELECT * FROM plans WHERE patient_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone())

def add_checkin(pid: int, d: dict) -> int:
    with connect() as con:
        cur = con.execute("""INSERT INTO checkins(patient_id,at,trigger,question,mood_1_5,homework_done,note,wants_to_discuss,risk_flag,status)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (pid, now(), d.get("trigger"), d.get("question"), d.get("mood_1_5"),
             None if d.get("homework_done") is None else int(d["homework_done"]),
             d.get("note"), d.get("wants_to_discuss"), int(bool(d.get("risk_flag"))), d.get("status", "done")))
        return cur.lastrowid

def checkins_since(pid: int, days: int) -> list[dict]:
    with connect() as con:
        return [_row(r) for r in con.execute(
            "SELECT * FROM checkins WHERE patient_id=? AND at >= datetime('now', ?) ORDER BY at",
            (pid, f"-{days} days"))]

def last_checkin_at(pid: int) -> str | None:
    with connect() as con:
        r = con.execute("SELECT at FROM checkins WHERE patient_id=? ORDER BY at DESC LIMIT 1", (pid,)).fetchone()
        return r["at"] if r else None

def add_message(pid: int, direction: str, body: str) -> None:
    with connect() as con:
        con.execute("INSERT INTO messages(patient_id,at,direction,body) VALUES (?,?,?,?)", (pid, now(), direction, body))

def recent_messages(pid: int, n: int = 8) -> list[dict]:
    with connect() as con:
        rows = con.execute("SELECT * FROM messages WHERE patient_id=? ORDER BY id DESC LIMIT ?", (pid, n)).fetchall()
        return [dict(r) for r in reversed(rows)]

def add_brief(pid: int, content: str) -> int:
    with connect() as con:
        return con.execute("INSERT INTO briefs(patient_id,at,content,approved,sent) VALUES (?,?,?,0,0)",
                           (pid, now(), content)).lastrowid

def latest_brief(pid: int) -> dict | None:
    with connect() as con:
        return _row(con.execute("SELECT * FROM briefs WHERE patient_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone())

def set_brief(bid: int, **fields) -> None:
    sets = ", ".join(f"{k}=?" for k in fields)
    with connect() as con:
        con.execute(f"UPDATE briefs SET {sets} WHERE id=?", (*fields.values(), bid))

def delete_patient_data(pid: int) -> None:
    with connect() as con:
        for t in ("signals", "checkins", "messages", "briefs"):
            con.execute(f"DELETE FROM {t} WHERE patient_id=?", (pid,))
