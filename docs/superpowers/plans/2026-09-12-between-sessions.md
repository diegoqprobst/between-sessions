# Between Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un agente que vive entre sesiones de terapia: toma el plan de la nota local de Quinde, acompaña la semana por WhatsApp guiado por señales del Apple Watch, y la víspera de la sesión envía al terapeuta un brief que el paciente aprobó.

**Architecture:** Servidor FastAPI (Python 3.12) con toda la lógica: SQLite, normalización de Health Auto Export, reglas de disparo puras, guardrail, agentes con OpenAI Agents SDK, Twilio, Auth0 CIBA y correo. Trigger.dev (TypeScript) solo programa, espera con waitpoints y reintenta llamando al servidor por HTTP. Un puente local lee la nota de Quinde y sube únicamente el plan estructurado.

**Tech Stack:** Python 3.12 · uv · FastAPI · openai-agents · openai (moderation) · twilio · httpx · any-llm-sdk[ollama] · pytest · Trigger.dev v4 (`@trigger.dev/sdk`) · ngrok · Cloud Run (opcional)

**Spec:** `docs/superpowers/specs/2026-09-11-between-sessions-design.md`

## Global Constraints

- Python 3.12 gestionado por uv (`uv python install 3.12` ya hecho). Un solo `pyproject.toml` en la raíz.
- Toda la lógica de modelo, guardrail, datos, Twilio, Auth0 y correo vive en `server/`. `orchestrator/` no llama a ningún modelo.
- Nada de texto crudo del paciente sale de la Mac por el puente: el puente solo envía `plan.json` (§6 del spec).
- Datos 100 % sintéticos en repo, fixtures, video y post.
- Verbos permitidos en copy y README: "acompaña", "registra", "resume para el terapeuta". Prohibidos: "detecta", "diagnostica".
- Guardrail falla cerrado: sin veredicto, el mensaje no llega al modelo.
- Anti-spam: máximo un check-in por 20 h; nunca entre 22:00 y 08:00 hora del paciente (`PATIENT_TZ`, por defecto `America/New_York`).
- Commits pequeños y frecuentes con `git commit`; el historial es parte de la entrega.

## Horario del sábado (hora Miami)

| Hora | Tarea | Resultado visible |
|---|---|---|
| 11:15–11:40 | Task 0 | Servidor arriba, ngrok, "hola" por WhatsApp recibe respuesta |
| 11:40–12:10 | Tasks 1–2 | Señales del Watch entran y las reglas disparan (tests verdes) |
| 12:10–12:50 | Task 3 | Check-in conversacional real por WhatsApp con guardrail |
| 12:50–13:15 | Task 4 | Puente Quinde → plan en el servidor (Ollama local) |
| 13:15–13:45 | Task 5 | Trigger.dev: cron + waitpoint funcionando en dev |
| 13:45–14:30 | Task 6 | Brief + aprobación (CIBA o fallback WhatsApp) + correo al terapeuta |
| 14:30–15:00 | Task 7 | Semana sembrada, recorrido completo grabable, Cloud Run si hay billing |
| 15:00–15:30 | Task 8 | README, video de 2 min, post |
| 15:30–16:00 | — | Entrega en el portal |

**Recortes en orden si se atrasa:** Cloud Run → Auth0 CIBA (queda el "sí" por WhatsApp) → puente con Ollama (queda `seed_week.py` con plan fijo).

---

## Estructura de archivos

```
between-sessions/
├── pyproject.toml                 # deps y pytest
├── .env.example                   # todas las variables, sin valores
├── server/
│   ├── __init__.py
│   ├── config.py                  # lectura de .env, una constante por variable
│   ├── store.py                   # SQLite: esquema y funciones de acceso
│   ├── decide.py                  # reglas de disparo puras (sin I/O)
│   ├── guard.py                   # guardrail: OpenAI moderation, falla cerrado
│   ├── mail.py                    # SMTP al terapeuta
│   ├── signals/__init__.py
│   ├── signals/health.py          # Health Auto Export JSON → filas diarias
│   ├── channels/__init__.py
│   ├── channels/twilio.py         # envío, firma, comandos del paciente
│   ├── agent/__init__.py
│   ├── agent/checkin.py           # agente de check-in (OpenAI Agents SDK)
│   ├── agent/brief.py             # agente del brief
│   ├── auth/__init__.py
│   ├── auth/ciba.py               # Auth0 CIBA: pedir y sondear aprobación
│   ├── trigger_client.py          # completar waitpoints de Trigger.dev por REST
│   └── app.py                     # FastAPI: rutas y flujo de conversación
├── bridge/quinde_plan.py          # local: nota Quinde → plan.json → POST /plans
├── orchestrator/                  # Trigger.dev
│   ├── package.json
│   ├── trigger.config.ts
│   └── src/trigger/evaluate.ts    # cron 3h + task checkin con waitpoint
│   └── src/trigger/brief.ts       # cron 18:00 víspera
├── fixtures/health_sample.json    # 7 días sintéticos
├── fixtures/nota_quinde_ejemplo.json
├── fixtures/plan_ejemplo.json
├── scripts/twilio_inbound.sh      # simula el webhook
├── scripts/seed_week.py           # siembra la semana del demo
├── tests/test_health.py
├── tests/test_decide.py
├── tests/test_twilio_commands.py
├── Dockerfile
└── deploy.sh
```

---

### Task 0: Esqueleto, servidor vivo y WhatsApp de ida y vuelta

**Files:**
- Create: `pyproject.toml`, `.env.example`, `server/__init__.py`, `server/config.py`, `server/app.py`, `server/channels/__init__.py`, `server/channels/twilio.py`, `scripts/twilio_inbound.sh`, `server/signals/__init__.py`, `server/agent/__init__.py`, `server/auth/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Produces: `server.config.*` constantes; `server.channels.twilio.send(to: str, body: str) -> str` (sid); `server.channels.twilio.valid_signature(url, params, signature) -> bool`; ruta `POST /twilio/webhook` (form `From`, `Body`).

- [ ] **Step 1: pyproject y entorno**

```toml
# pyproject.toml
[project]
name = "between-sessions"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "fastapi", "uvicorn[standard]", "python-multipart",
  "openai-agents", "openai", "twilio", "httpx", "python-dotenv", "pydantic",
  "any-llm-sdk[ollama]",
]
[dependency-groups]
dev = ["pytest", "pytest-asyncio"]
[tool.pytest.ini_options]
testpaths = ["tests"]
[tool.uv]
package = false
```

Run: `cd ~/Code/between-sessions && uv python pin 3.12 && uv sync && uv run python -c "import fastapi, agents, twilio; print('ok')"`
Expected: `ok`

- [ ] **Step 2: `.env.example` y `.env`**

```bash
# .env.example
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM=whatsapp:+14155238886
TWILIO_VALIDATE=1
PUBLIC_URL=https://TU-DOMINIO.ngrok-free.app
THERAPIST_KEY=dev-therapist-key
THERAPIST_EMAIL=
DB_PATH=between.sqlite
PATIENT_TZ=America/New_York
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
TRIGGER_SECRET_KEY=
TRIGGER_API_URL=https://api.trigger.dev
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
OLLAMA_MODEL=qwen3:14b
```

Run: `cp .env.example .env` y rellenar con las credenciales de Diego (nunca se pegan en el chat).
Confirmar el nombre del modelo: `curl -s https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY" | grep -o '"id":"gpt-[^"]*"' | sort -u | head -20` y poner en `OPENAI_MODEL` el más barato con tool use del starter kit.

- [ ] **Step 3: config.py**

```python
# server/config.py
import os
from dotenv import load_dotenv

load_dotenv()

def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)

OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-5-mini")
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_FROM = env("TWILIO_FROM", "whatsapp:+14155238886")
TWILIO_VALIDATE = env("TWILIO_VALIDATE", "1") == "1"
PUBLIC_URL = env("PUBLIC_URL", "http://localhost:8000").rstrip("/")
THERAPIST_KEY = env("THERAPIST_KEY", "dev-therapist-key")
THERAPIST_EMAIL = env("THERAPIST_EMAIL", "")
DB_PATH = env("DB_PATH", "between.sqlite")
PATIENT_TZ = env("PATIENT_TZ", "America/New_York")
AUTH0_DOMAIN = env("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID = env("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET = env("AUTH0_CLIENT_SECRET", "")
TRIGGER_SECRET_KEY = env("TRIGGER_SECRET_KEY", "")
TRIGGER_API_URL = env("TRIGGER_API_URL", "https://api.trigger.dev").rstrip("/")
SMTP_HOST = env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER", "")
SMTP_PASS = env("SMTP_PASS", "")
OLLAMA_MODEL = env("OLLAMA_MODEL", "qwen3:14b")
```

- [ ] **Step 4: canal Twilio**

```python
# server/channels/twilio.py
import re
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from server import config

_client: Client | None = None

def client() -> Client:
    global _client
    if _client is None:
        _client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    return _client

def send(to: str, body: str) -> str:
    """to: 'whatsapp:+1305...' . Devuelve el SID del mensaje."""
    msg = client().messages.create(from_=config.TWILIO_FROM, to=to, body=body)
    return msg.sid

def valid_signature(url: str, params: dict, signature: str | None) -> bool:
    if not config.TWILIO_VALIDATE:
        return True
    return RequestValidator(config.TWILIO_AUTH_TOKEN).validate(url, params, signature or "")

_CMD = re.compile(r"^\s*(pausa|pause|reanudar|resume|borrar|delete|no compartas|don't share)\s*(.*)$", re.I)

def parse_command(text: str) -> tuple[str, str] | None:
    """Devuelve ('pause'|'resume'|'delete'|'exclude', argumento) o None."""
    m = _CMD.match(text or "")
    if not m:
        return None
    word, arg = m.group(1).lower(), m.group(2).strip().lower()
    if word in ("pausa", "pause"):
        return ("pause", "")
    if word in ("reanudar", "resume"):
        return ("resume", "")
    if word in ("borrar", "delete"):
        return ("delete", "")
    return ("exclude", arg)
```

- [ ] **Step 5: test de comandos**

```python
# tests/test_twilio_commands.py
from server.channels.twilio import parse_command

def test_pause_and_resume():
    assert parse_command("pausa") == ("pause", "")
    assert parse_command("Reanudar") == ("resume", "")

def test_exclude_signal():
    assert parse_command("no compartas sueño") == ("exclude", "sueño")

def test_plain_text_is_not_command():
    assert parse_command("hoy dormí fatal") is None
```

Run: `uv run pytest tests/test_twilio_commands.py -v` → Expected: 3 PASS

- [ ] **Step 6: app mínima con webhook eco**

```python
# server/app.py
from fastapi import FastAPI, Request, Header, HTTPException, Response
from server import config
from server.channels import twilio as wa

app = FastAPI(title="Between Sessions")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/twilio/webhook")
async def twilio_webhook(request: Request, x_twilio_signature: str | None = Header(default=None)):
    form = dict(await request.form())
    url = f"{config.PUBLIC_URL}/twilio/webhook"
    if not wa.valid_signature(url, form, x_twilio_signature):
        raise HTTPException(403, "bad signature")
    sender, body = form.get("From", ""), form.get("Body", "")
    reply = await handle_inbound(sender, body)
    if reply:
        wa.send(sender, reply)
    return Response(content="<Response/>", media_type="application/xml")

async def handle_inbound(sender: str, body: str) -> str | None:
    return f"Recibido: {body}"
```

```bash
# scripts/twilio_inbound.sh — simula el webhook (requiere TWILIO_VALIDATE=0 en .env para pruebas locales)
#!/usr/bin/env bash
# uso: scripts/twilio_inbound.sh "+13055550100" "hola"
curl -s -X POST "${SERVER:-http://localhost:8000}/twilio/webhook" \
  --data-urlencode "From=whatsapp:$1" --data-urlencode "Body=$2"
```

Run: `chmod +x scripts/twilio_inbound.sh && uv run uvicorn server.app:app --port 8000 --reload` (terminal 1) · `ngrok http --url=TU-DOMINIO.ngrok-free.app 8000` (terminal 2) · en la consola de Twilio, Sandbox → "When a message comes in" = `https://TU-DOMINIO.ngrok-free.app/twilio/webhook`.
Expected: mandar "hola" desde el WhatsApp de Diego al sandbox → recibe "Recibido: hola".

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: servidor FastAPI mínimo con webhook de WhatsApp y comandos del paciente"
```

---

### Task 1: Store y señales del Watch

**Files:**
- Create: `server/store.py`, `server/signals/health.py`, `fixtures/health_sample.json`, `tests/test_health.py`
- Modify: `server/app.py` (ruta `POST /health/{token}`)

**Interfaces:**
- Produces: `store.init_db()`, `store.get_or_create_patient(phone) -> dict`, `store.get_patient(pid) -> dict`, `store.patient_by_token(token) -> dict|None`, `store.patient_by_ref(ref) -> dict|None`, `store.set_patient(pid, **fields)`, `store.list_patients() -> list[dict]`, `store.upsert_signal(pid, row: dict)`, `store.signals_since(pid, days) -> list[dict]` (orden ascendente por fecha), `store.add_plan(pid, plan: dict)`, `store.latest_plan(pid) -> dict|None`, `store.add_checkin(pid, data: dict)`, `store.checkins_since(pid, days)`, `store.last_checkin_at(pid) -> str|None`, `store.add_message(pid, direction, body)`, `store.recent_messages(pid, n) -> list[dict]`, `store.add_brief(pid, content) -> int`, `store.set_brief(bid, **fields)`, `store.delete_patient_data(pid)`.
- Produces: `health.normalize(payload: dict) -> list[dict]` con claves `date, sleep_h, hrv_ms, resting_hr, steps, mood_valence, mood_labels`.

- [ ] **Step 1: store.py**

```python
# server/store.py
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
```

- [ ] **Step 2: fixture de Health Auto Export (7 días, con una noche corta y un ánimo negativo el día 5)**

```json
{
  "data": {
    "metrics": [
      {"name": "sleep_analysis", "units": "hr", "data": [
        {"date": "2026-09-06 07:10:00 -0400", "asleep": 7.2, "inBed": 7.8},
        {"date": "2026-09-07 07:05:00 -0400", "asleep": 6.9, "inBed": 7.4},
        {"date": "2026-09-08 06:50:00 -0400", "asleep": 7.0, "inBed": 7.6},
        {"date": "2026-09-09 07:20:00 -0400", "asleep": 6.8, "inBed": 7.3},
        {"date": "2026-09-10 06:40:00 -0400", "asleep": 5.1, "inBed": 6.9},
        {"date": "2026-09-11 07:00:00 -0400", "asleep": 6.7, "inBed": 7.2},
        {"date": "2026-09-12 07:15:00 -0400", "asleep": 7.1, "inBed": 7.5}
      ]},
      {"name": "heart_rate_variability", "units": "ms", "data": [
        {"date": "2026-09-06 08:00:00 -0400", "qty": 52},
        {"date": "2026-09-07 08:00:00 -0400", "qty": 49},
        {"date": "2026-09-08 08:00:00 -0400", "qty": 50},
        {"date": "2026-09-09 08:00:00 -0400", "qty": 47},
        {"date": "2026-09-10 08:00:00 -0400", "qty": 36},
        {"date": "2026-09-11 08:00:00 -0400", "qty": 45},
        {"date": "2026-09-12 08:00:00 -0400", "qty": 51}
      ]},
      {"name": "resting_heart_rate", "units": "count/min", "data": [
        {"date": "2026-09-06 08:00:00 -0400", "qty": 58},
        {"date": "2026-09-07 08:00:00 -0400", "qty": 59},
        {"date": "2026-09-08 08:00:00 -0400", "qty": 58},
        {"date": "2026-09-09 08:00:00 -0400", "qty": 60},
        {"date": "2026-09-10 08:00:00 -0400", "qty": 66},
        {"date": "2026-09-11 08:00:00 -0400", "qty": 61},
        {"date": "2026-09-12 08:00:00 -0400", "qty": 58}
      ]},
      {"name": "step_count", "units": "count", "data": [
        {"date": "2026-09-06 12:00:00 -0400", "qty": 6200},
        {"date": "2026-09-07 12:00:00 -0400", "qty": 7100},
        {"date": "2026-09-08 12:00:00 -0400", "qty": 5400},
        {"date": "2026-09-09 12:00:00 -0400", "qty": 6800},
        {"date": "2026-09-10 12:00:00 -0400", "qty": 2100},
        {"date": "2026-09-11 12:00:00 -0400", "qty": 5900},
        {"date": "2026-09-12 12:00:00 -0400", "qty": 6400}
      ]}
    ],
    "stateOfMind": [
      {"start": "2026-09-08 21:30:00 -0400", "kind": "dailyMood", "valence": 0.2, "valenceClassification": "slightlyPleasant", "labels": ["Calm"]},
      {"start": "2026-09-10 22:45:00 -0400", "kind": "momentaryEmotion", "valence": -0.6, "valenceClassification": "unpleasant", "labels": ["Anxious"], "associations": ["Work"]}
    ]
  }
}
```

Guardar en `fixtures/health_sample.json`.

- [ ] **Step 3: test de normalización (falla primero)**

```python
# tests/test_health.py
import json
from server.signals.health import normalize

def load():
    return json.load(open("fixtures/health_sample.json"))

def test_seven_days():
    rows = normalize(load())
    assert [r["date"] for r in rows] == [f"2026-09-{d:02d}" for d in range(6, 13)]

def test_short_night_and_low_mood():
    by = {r["date"]: r for r in normalize(load())}
    assert by["2026-09-10"]["sleep_h"] == 5.1
    assert by["2026-09-10"]["hrv_ms"] == 36
    assert by["2026-09-10"]["mood_valence"] == -0.6
    assert by["2026-09-10"]["mood_labels"] == ["Anxious"]
    assert by["2026-09-07"]["mood_valence"] is None

def test_minutes_are_converted():
    payload = {"data": {"metrics": [{"name": "sleep_analysis", "units": "min",
               "data": [{"date": "2026-09-01 07:00:00 -0400", "asleep": 420}]}]}}
    assert normalize(payload)[0]["sleep_h"] == 7.0
```

Run: `uv run pytest tests/test_health.py -v` → Expected: FAIL (`No module named server.signals.health`)

- [ ] **Step 4: normalizador**

```python
# server/signals/health.py
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
```

Run: `uv run pytest tests/test_health.py -v` → Expected: 3 PASS

- [ ] **Step 5: ruta de ingesta + init de BD en app.py**

Añadir a `server/app.py` (debajo de `app = FastAPI(...)`):

```python
from server import store
from server.signals import health as health_signals

@app.on_event("startup")
def _startup():
    store.init_db()

@app.post("/health/{token}")
async def ingest_health(token: str, request: Request):
    patient = store.patient_by_token(token)
    if not patient:
        raise HTTPException(404, "unknown token")
    payload = await request.json()
    rows = health_signals.normalize(payload)
    for row in rows:
        store.upsert_signal(patient["id"], row)
    return {"days": len(rows)}
```

Run: con el servidor arriba y un paciente creado (mandar "hola" por WhatsApp o `scripts/twilio_inbound.sh "+13055550100" hola`), obtener su token con `sqlite3 between.sqlite "select id, phone, health_token from patients"` y:
`curl -s -X POST localhost:8000/health/TOKEN -H 'content-type: application/json' --data @fixtures/health_sample.json`
Expected: `{"days":7}`

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: store SQLite y normalización de señales de Health Auto Export"
```

---

### Task 2: Reglas de disparo

**Files:**
- Create: `server/decide.py`, `tests/test_decide.py`
- Modify: `server/app.py` (ruta `POST /decide`)

**Interfaces:**
- Produces: `decide.triggers(signals: list[dict], plan: dict|None, last_checkin_at: str|None, now: datetime, tz: str) -> list[str]` — nombres posibles: `sleep_drop`, `hrv_drop`, `low_mood`, `silence`, `homework_day`. Lista vacía = no molestar.
- Produces: ruta `POST /decide` (header `X-Therapist-Key`) → `{"triggered": [{"patient_id": int, "trigger": str}]}`.

- [ ] **Step 1: test (falla primero)**

```python
# tests/test_decide.py
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
    r = rows(7.0, 7.0, 7.0, 7.0)
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
```

Run: `uv run pytest tests/test_decide.py -v` → Expected: FAIL (`No module named server.decide`)

- [ ] **Step 2: implementación**

```python
# server/decide.py
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
```

Run: `uv run pytest tests/test_decide.py -v` → Expected: 7 PASS

- [ ] **Step 3: ruta `/decide`**

Añadir a `server/app.py`:

```python
from datetime import datetime, timezone
from server import decide

def require_key(key: str | None):
    if key != config.THERAPIST_KEY:
        raise HTTPException(401, "bad key")

@app.post("/decide")
def decide_all(x_therapist_key: str | None = Header(default=None)):
    require_key(x_therapist_key)
    now = datetime.now(timezone.utc)
    out = []
    for p in store.list_patients():
        if p["paused"] or not p["ref"] or p["pending_trigger"]:
            continue
        t = decide.triggers(store.signals_since(p["id"], 16), store.latest_plan(p["id"]),
                            store.last_checkin_at(p["id"]), now, config.PATIENT_TZ)
        if t:
            out.append({"patient_id": p["id"], "trigger": t[0]})
    return {"triggered": out}
```

Run: `curl -s -X POST localhost:8000/decide -H "x-therapist-key: dev-therapist-key"` → Expected: `{"triggered":[...]}` (vacío hasta que el paciente tenga `ref`; se llena en Task 3).

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: reglas de disparo por señal con anti-spam y horas de silencio"
```

---

### Task 3: Guardrail, agente de check-in y conversación por WhatsApp

**Files:**
- Create: `server/guard.py`, `server/agent/checkin.py`, `server/trigger_client.py`
- Modify: `server/app.py` (reemplazar `handle_inbound`, añadir `POST /checkin`)

**Interfaces:**
- Consumes: `store.*`, `wa.send`, `wa.parse_command`, `decide` (no directamente).
- Produces: `guard.assess(text) -> dict(ok: bool, risk: bool|None, categories: list[str])`; `checkin.open_question(patient, plan, trigger, today) -> str`; `checkin.turn(patient, plan, trigger, history: list[dict]) -> Turn`; `trigger_client.complete(token_id, data: dict) -> bool`; ruta `POST /checkin` body `{"patient_id", "trigger", "waitpoint_token"?}`.

- [ ] **Step 1: guardrail (falla cerrado)**

```python
# server/guard.py
from openai import OpenAI
from server import config

RISK_PREFIXES = ("self-harm",)
RISK_REPLY = (
    "Gracias por contarme esto. No soy un servicio de emergencia. "
    "Si estás en peligro ahora mismo, llama o escribe al 988 (EE. UU.) o al 911. "
    "Voy a avisar a tu terapeuta como acordamos al inicio. ¿Estás en un lugar seguro en este momento?"
)
UNAVAILABLE_REPLY = "Ahora mismo no puedo leer mensajes. Si es urgente, llama al 988 o al 911. Te escribo en cuanto vuelva."

_client: OpenAI | None = None

def _oa() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client

def assess(text: str) -> dict:
    """ok=False significa 'sin veredicto': el mensaje NO debe llegar al modelo."""
    try:
        res = _oa().moderations.create(model="omni-moderation-latest", input=text)
    except Exception:
        return {"ok": False, "risk": None, "categories": []}
    r = res.results[0]
    cats = [k for k, v in r.categories.model_dump().items() if v]
    risk = any(c.startswith(RISK_PREFIXES) for c in cats)
    return {"ok": True, "risk": risk, "categories": cats}
```

- [ ] **Step 2: agente de check-in**

```python
# server/agent/checkin.py
from pydantic import BaseModel
from agents import Agent, Runner
from server import config

class Turn(BaseModel):
    reply: str
    done: bool
    mood_1_5: int | None = None
    homework_done: bool | None = None
    note: str = ""
    wants_to_discuss: str = ""

TRIGGER_TEXT = {
    "sleep_drop": "anoche durmió bastante menos que su promedio",
    "hrv_drop": "su cuerpo muestra más estrés que de costumbre (variabilidad cardíaca baja)",
    "low_mood": "registró un estado de ánimo negativo en su reloj",
    "silence": "hace dos días que no llega ninguna señal",
    "homework_day": "es día de revisar la tarea acordada con su terapeuta",
    "spontaneous": "escribió por su cuenta",
}

INSTRUCTIONS = """Eres el acompañante entre sesiones de un paciente de psicoterapia. Escribes por WhatsApp, en español, cálido y breve.
Reglas duras:
- Una sola pregunta por mensaje, máximo dos líneas. Nada de listas ni de consejos clínicos.
- No diagnosticas ni interpretas. Acompañas, registras, y preparas un resumen para su terapeuta, que el paciente aprueba.
- Anclas la pregunta al plan de la sesión (qué vigilar, la tarea) y al motivo del contacto.
- Cierras en máximo dos turnos del paciente: agradeces y dices que lo tendrás en cuenta para el resumen.
- Cuando cierras (done=true), extraes: mood_1_5 (1 muy mal, 5 muy bien), homework_done si se habló de la tarea, note (una frase objetiva), wants_to_discuss (lo que quiere tratar en sesión, en sus palabras, o vacío).
"""

_agent = Agent(name="checkin", instructions=INSTRUCTIONS, output_type=Turn, model=config.OPENAI_MODEL)

def _context(patient: dict, plan: dict | None, trigger: str, today: dict | None) -> str:
    watch = ", ".join(plan.get("watch", [])) if plan else "sin plan cargado"
    homework = plan.get("homework") if plan else "ninguna"
    signal = ""
    if today:
        signal = f"Señales de hoy: sueño {today.get('sleep_h')} h, HRV {today.get('hrv_ms')} ms, ánimo {today.get('mood_valence')}."
    return (f"Paciente: {patient.get('name') or patient.get('ref')}. Motivo del contacto: {TRIGGER_TEXT.get(trigger, trigger)}.\n"
            f"Plan de la sesión — vigilar: {watch}. Tarea: {homework}.\n{signal}")

def open_question(patient: dict, plan: dict | None, trigger: str, today: dict | None) -> str:
    prompt = _context(patient, plan, trigger, today) + "\nEscribe el primer mensaje: saluda por su nombre y haz UNA pregunta. done=false."
    return Runner.run_sync(_agent, prompt).final_output.reply

def turn(patient: dict, plan: dict | None, trigger: str, history: list[dict], force_close: bool) -> Turn:
    convo = "\n".join(f"{'Paciente' if m['direction']=='in' else 'Tú'}: {m['body']}" for m in history)
    tail = "Cierra ahora (done=true) y extrae los campos." if force_close else "Responde. Si ya tienes lo esencial, cierra (done=true) y extrae los campos."
    prompt = _context(patient, plan, trigger, None) + f"\nConversación hasta ahora:\n{convo}\n{tail}"
    return Runner.run_sync(_agent, prompt).final_output
```

- [ ] **Step 3: cliente de waitpoints de Trigger.dev**

```python
# server/trigger_client.py
import httpx
from server import config

def complete(token_id: str | None, data: dict) -> bool:
    """Completa un waitpoint token de Trigger.dev. Devuelve False si no hay token o falla."""
    if not token_id or not config.TRIGGER_SECRET_KEY:
        return False
    try:
        r = httpx.post(f"{config.TRIGGER_API_URL}/api/v1/waitpoints/tokens/{token_id}/complete",
                       headers={"Authorization": f"Bearer {config.TRIGGER_SECRET_KEY}"},
                       json={"data": data}, timeout=10)
        return r.status_code < 300
    except httpx.HTTPError:
        return False
```

- [ ] **Step 4: flujo de conversación y ruta `/checkin`**

Reemplazar `handle_inbound` en `server/app.py` y añadir la ruta:

```python
from pydantic import BaseModel
from server import guard, trigger_client
from server.agent import checkin as checkin_agent

WELCOME = ("Hola, soy tu acompañante entre sesiones. Te escribiré solo cuando tu reloj o tu plan lo justifiquen, "
           "y tu terapeuta recibirá un resumen antes de cada sesión únicamente si tú lo apruebas.\n"
           "Comandos: 'pausa', 'reanudar', 'borrar', 'no compartas sueño'.\n¿Cómo te llamas?")

async def handle_inbound(sender: str, body: str) -> str | None:
    p = store.get_or_create_patient(sender)
    pid = p["id"]
    store.add_message(pid, "in", body)
    text = (body or "").strip()

    cmd = wa.parse_command(text)
    if cmd:
        kind, arg = cmd
        if kind == "pause":
            store.set_patient(pid, paused=1); return "Listo, en pausa. Escribe 'reanudar' cuando quieras."
        if kind == "resume":
            store.set_patient(pid, paused=0); return "Reanudado. Aquí sigo."
        if kind == "delete":
            store.delete_patient_data(pid); return "Borré tus señales, conversaciones y resúmenes. Tu plan queda."
        excluded = list(p["excluded_signals"] or []) + [arg]
        store.set_patient(pid, excluded_signals=excluded); return f"De acuerdo: '{arg}' no irá en el resumen."

    if p["stage"] == "new":
        store.set_patient(pid, stage="ask_name"); return WELCOME
    if p["stage"] == "ask_name":
        name = text.split()[0].strip(".,!").title() if text else "Paciente"
        store.set_patient(pid, stage="active", name=name, ref=name.lower())
        return f"Gracias, {name}. Cuando tu terapeuta cargue el plan de la sesión, empiezo a acompañarte."

    if p.get("awaiting_brief") and text.lower() in ("sí", "si", "ok", "dale", "yes", "apruebo"):
        return await _send_brief_after_approval(p)

    verdict = guard.assess(text)
    if not verdict["ok"]:
        return guard.UNAVAILABLE_REPLY
    if verdict["risk"]:
        store.add_checkin(pid, {"trigger": p["pending_trigger"] or "spontaneous", "risk_flag": True, "note": "riesgo detectado por guardrail", "status": "risk"})
        _notify_therapist_risk(p)
        trigger_client.complete(p["pending_token"], {"status": "risk"})
        store.set_patient(pid, pending_trigger=None, pending_token=None, turns=0)
        return guard.RISK_REPLY

    trigger = p["pending_trigger"] or "spontaneous"
    turns = (p["turns"] or 0) + 1
    result = checkin_agent.turn(p, store.latest_plan(pid), trigger, store.recent_messages(pid, 8), force_close=turns >= 2)
    if result.done or turns >= 2:
        store.add_checkin(pid, {"trigger": trigger, "mood_1_5": result.mood_1_5, "homework_done": result.homework_done,
                                "note": result.note, "wants_to_discuss": result.wants_to_discuss, "status": "done"})
        trigger_client.complete(p["pending_token"], {"status": "done", "mood_1_5": result.mood_1_5})
        store.set_patient(pid, pending_trigger=None, pending_token=None, turns=0)
    else:
        store.set_patient(pid, turns=turns)
    store.add_message(pid, "out", result.reply)
    return result.reply

def _notify_therapist_risk(p: dict) -> None:
    from server import mail
    to = p.get("therapist_email") or config.THERAPIST_EMAIL
    if to:
        mail.send(to, f"[Between Sessions] Señal de riesgo — {p.get('name')}",
                  "El acompañante recibió un mensaje con indicadores de riesgo y respondió con recursos de emergencia. "
                  "No se incluye el texto del paciente. Contacta según tu protocolo.")

class CheckinIn(BaseModel):
    patient_id: int
    trigger: str
    waitpoint_token: str | None = None

@app.post("/checkin")
def start_checkin(body: CheckinIn, x_therapist_key: str | None = Header(default=None)):
    require_key(x_therapist_key)
    p = store.get_patient(body.patient_id)
    if not p or p["paused"]:
        raise HTTPException(404, "patient unavailable")
    sig = store.signals_since(p["id"], 1)
    q = checkin_agent.open_question(p, store.latest_plan(p["id"]), body.trigger, sig[-1] if sig else None)
    store.set_patient(p["id"], pending_trigger=body.trigger, pending_token=body.waitpoint_token, turns=0)
    store.add_message(p["id"], "out", q)
    wa.send(p["phone"], q)
    return {"sent": True, "question": q}
```

`_send_brief_after_approval` se define en Task 6; hasta entonces, añadir un stub que devuelva `"Gracias, lo envío."` para que el módulo importe.

`server/mail.py` (se usa ya aquí):

```python
# server/mail.py
import smtplib
from email.message import EmailMessage
from server import config

def send(to: str, subject: str, body: str) -> bool:
    if not (config.SMTP_USER and config.SMTP_PASS and to):
        print(f"[mail] (sin SMTP) → {to}: {subject}\n{body}")
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_USER, to, subject
    msg.set_content(body)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.starttls(); s.login(config.SMTP_USER, config.SMTP_PASS); s.send_message(msg)
    return True
```

- [ ] **Step 5: prueba manual de punta a punta por WhatsApp**

1. Reiniciar el servidor. Desde el WhatsApp de Diego: "hola" → WELCOME; "Ana" → confirmación.
2. Cargar un plan: `curl -s -X POST localhost:8000/plans -H "x-therapist-key: dev-therapist-key" -H 'content-type: application/json' --data @fixtures/plan_ejemplo.json` (ruta y fixture en Task 4; si aún no existe, saltar y usar `trigger: "spontaneous"`).
3. Ingerir señales (Task 1, paso 5) y lanzar: `curl -s -X POST localhost:8000/checkin -H "x-therapist-key: dev-therapist-key" -H 'content-type: application/json' -d '{"patient_id":1,"trigger":"sleep_drop"}'`
Expected: llega UNA pregunta al WhatsApp; se responde; el agente cierra en ≤ 2 turnos; `sqlite3 between.sqlite "select trigger,mood_1_5,note from checkins"` muestra la fila.
4. Escribir un mensaje con contenido de riesgo sintético → llega `RISK_REPLY` y se registra `status='risk'`.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: guardrail, agente de check-in y conversación por WhatsApp con cierre en dos turnos"
```

---

### Task 4: Puente Quinde → plan

**Files:**
- Create: `bridge/quinde_plan.py`, `fixtures/nota_quinde_ejemplo.json` (copiar de `~/Terapias/ejemplo/contenido_nota.json`), `fixtures/plan_ejemplo.json`
- Modify: `server/app.py` (ruta `POST /plans`)

**Interfaces:**
- Produces: ruta `POST /plans` (header `X-Therapist-Key`) con el JSON `plan.json` del spec §6; responde `{"patient_id": int}`.
- Produces: CLI `uv run python bridge/quinde_plan.py <nota.json> --next-session YYYY-MM-DD [--server URL]`.

- [ ] **Step 1: fixture de plan (lo que produce el puente para la nota de ejemplo)**

```json
{
  "patient_ref": "ana",
  "session_num": 3,
  "session_date": "2026-09-05",
  "next_session_date": "2026-09-13",
  "watch": ["sueño nocturno", "ansiedad anticipatoria antes de dormir", "culpa al poner límites"],
  "homework": "Respiración 4-7-8 y bitácora nocturna",
  "next_focus": "Revisar adherencia y explorar rutina de sueño",
  "risk_baseline": "none"
}
```

Guardar en `fixtures/plan_ejemplo.json`. Copiar la nota: `cp ~/Terapias/ejemplo/contenido_nota.json fixtures/nota_quinde_ejemplo.json`.

- [ ] **Step 2: ruta `/plans`**

```python
class PlanIn(BaseModel):
    patient_ref: str
    session_num: int | None = None
    session_date: str
    next_session_date: str
    watch: list[str] = []
    homework: str = ""
    next_focus: str = ""
    risk_baseline: str = "none"

@app.post("/plans")
def post_plan(plan: PlanIn, x_therapist_key: str | None = Header(default=None)):
    require_key(x_therapist_key)
    p = store.patient_by_ref(plan.patient_ref)
    if not p:
        raise HTTPException(404, f"no patient with ref {plan.patient_ref}; el paciente debe escribir 'hola' primero")
    store.add_plan(p["id"], plan.model_dump())
    return {"patient_id": p["id"]}
```

Run: `curl -s -X POST localhost:8000/plans -H "x-therapist-key: dev-therapist-key" -H 'content-type: application/json' --data @fixtures/plan_ejemplo.json` → Expected: `{"patient_id":1}` (el paciente "Ana" debe existir por WhatsApp).

- [ ] **Step 3: el puente (local, Ollama vía any-llm)**

```python
# bridge/quinde_plan.py
"""Lee la nota C-SOAP de Quinde y publica SOLO el plan estructurado. Corre en la Mac del terapeuta."""
import argparse, json, os, sys
import httpx
from pydantic import BaseModel
from any_llm import completion

class Plan(BaseModel):
    patient_ref: str
    session_num: int | None = None
    session_date: str
    next_session_date: str
    watch: list[str]
    homework: str
    next_focus: str
    risk_baseline: str = "none"

PROMPT = """Eres asistente de un psicólogo. A partir de la sección PLAN de una nota clínica, extrae en JSON:
- watch: 2 a 4 cosas concretas a vigilar durante la semana (frases cortas)
- homework: la tarea acordada, en una frase
- next_focus: qué se revisará en la próxima sesión
- session_date: la fecha de la sesión en formato YYYY-MM-DD (la fecha dada es '{fecha}')
No incluyas nada que el paciente haya dicho literalmente. Solo el plan.
Sección PLAN:
{plan}
"""

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("nota"); ap.add_argument("--next-session", required=True)
    ap.add_argument("--server", default=os.environ.get("SERVER", "http://localhost:8000"))
    ap.add_argument("--key", default=os.environ.get("THERAPIST_KEY", "dev-therapist-key"))
    ap.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen3:14b"))
    a = ap.parse_args()
    note = json.load(open(a.nota))
    plan_section = next(s for s in note["secciones"] if s.get("letra") == "P")
    prompt = PROMPT.format(fecha=note.get("fecha", ""), plan="\n".join(plan_section["contenido"]))
    class Extract(BaseModel):
        watch: list[str]; homework: str; next_focus: str; session_date: str
    res = completion(model=a.model, provider="ollama", messages=[{"role": "user", "content": prompt}],
                     response_format=Extract)
    data = json.loads(res.choices[0].message.content)
    plan = Plan(patient_ref=note["paciente"].strip().lower(), session_num=note.get("sesion_num"),
                next_session_date=a.next_session,
                risk_baseline="none" if str(note.get("riesgo", "")).lower().startswith("ning") else "flagged", **data)
    print(plan.model_dump_json(indent=2))
    r = httpx.post(f"{a.server}/plans", json=plan.model_dump(), headers={"x-therapist-key": a.key}, timeout=30)
    print(r.status_code, r.text)
    return 0 if r.status_code == 200 else 1

if __name__ == "__main__":
    sys.exit(main())
```

Run: `uv run python bridge/quinde_plan.py fixtures/nota_quinde_ejemplo.json --next-session 2026-09-13`
Expected: imprime el plan (watch con 2–4 ítems, homework "respiración 4-7-8…") y `200 {"patient_id":1}`. Si `response_format` con Pydantic no fuera aceptado por la versión instalada de any-llm, usar `response_format={"type": "json_object"}` y añadir al prompt "Responde solo JSON con claves watch, homework, next_focus, session_date".

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: puente local Quinde → plan estructurado vía Ollama (any-llm)"
```

---

### Task 5: Orquestación en Trigger.dev

**Files:**
- Create: `orchestrator/package.json`, `orchestrator/trigger.config.ts`, `orchestrator/src/trigger/evaluate.ts`, `orchestrator/src/trigger/brief.ts`, `orchestrator/.env.example`

**Interfaces:**
- Consumes: `POST /decide`, `POST /checkin` (con `waitpoint_token`), `POST /brief` (Task 6).
- Produces: tareas `evaluate-signals` (cron `0 */3 * * *`), `checkin` (con waitpoint 6 h), `nightly-brief` (cron `0 18 * * *` America/New_York).

- [ ] **Step 1: proyecto**

```bash
cd ~/Code/between-sessions && mkdir -p orchestrator/src/trigger && cd orchestrator
npm init -y >/dev/null && npm i @trigger.dev/sdk@^4 && npm i -D typescript @types/node
npx trigger.dev@latest init   # elige el proyecto creado en el dashboard; escribe trigger.config.ts con el project ref
```

Si `init` sobreescribe `trigger.config.ts`, dejar el generado y solo comprobar `dirs: ["./src/trigger"]`.

```json
// orchestrator/package.json (fragmento relevante)
{ "name": "between-sessions-orchestrator", "private": true, "type": "module",
  "scripts": { "dev": "trigger.dev dev", "deploy": "trigger.dev deploy" } }
```

```bash
# orchestrator/.env.example
SERVER_URL=https://TU-DOMINIO.ngrok-free.app
THERAPIST_KEY=dev-therapist-key
```

- [ ] **Step 2: evaluate.ts**

```ts
// orchestrator/src/trigger/evaluate.ts
import { schedules, task, wait, logger } from "@trigger.dev/sdk";

const SERVER = process.env.SERVER_URL!;
const KEY = process.env.THERAPIST_KEY!;
const headers = { "x-therapist-key": KEY, "content-type": "application/json" };

type Triggered = { patient_id: number; trigger: string };

export const evaluateSignals = schedules.task({
  id: "evaluate-signals",
  cron: "0 */3 * * *",
  run: async () => {
    const res = await fetch(`${SERVER}/decide`, { method: "POST", headers });
    if (!res.ok) throw new Error(`decide ${res.status}`);
    const { triggered } = (await res.json()) as { triggered: Triggered[] };
    logger.info("triggered", { count: triggered.length });
    for (const t of triggered) await checkin.trigger(t);
    return { count: triggered.length };
  },
});

export const checkin = task({
  id: "checkin",
  retry: { maxAttempts: 3, minTimeoutInMs: 5_000 },
  run: async (payload: Triggered) => {
    const token = await wait.createToken({ timeout: "6h", idempotencyKey: `checkin-${payload.patient_id}-${Date.now()}` });
    const res = await fetch(`${SERVER}/checkin`, {
      method: "POST", headers, body: JSON.stringify({ ...payload, waitpoint_token: token.id }),
    });
    if (!res.ok) throw new Error(`checkin ${res.status}`);
    const result = await wait.forToken<{ status: string; mood_1_5?: number }>(token);
    if (!result.ok) { logger.warn("no reply in 6h", payload); return { status: "no_reply" }; }
    return result.output;
  },
});
```

- [ ] **Step 3: brief.ts**

```ts
// orchestrator/src/trigger/brief.ts
import { schedules } from "@trigger.dev/sdk";

const SERVER = process.env.SERVER_URL!;
const headers = { "x-therapist-key": process.env.THERAPIST_KEY!, "content-type": "application/json" };

export const nightlyBrief = schedules.task({
  id: "nightly-brief",
  cron: { pattern: "0 18 * * *", timezone: "America/New_York" },
  run: async () => {
    const res = await fetch(`${SERVER}/brief`, { method: "POST", headers, body: JSON.stringify({}) });
    if (!res.ok) throw new Error(`brief ${res.status}`);
    return await res.json();
  },
});
```

- [ ] **Step 4: correr en dev y disparar a mano**

Run: `cd orchestrator && cp .env.example .env` (rellenar) `&& npx trigger.dev@latest dev`
En el dashboard de Trigger.dev → Test → `evaluate-signals` → Run. Expected: la tarea `checkin` se crea, la pregunta llega por WhatsApp, y al responder (Task 3) el servidor completa el token y la tarea termina con `{status:"done"}`. Copiar la **secret key** del entorno dev a `TRIGGER_SECRET_KEY` en el `.env` del servidor.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: orquestación Trigger.dev con cron de señales y waitpoints por check-in"
```

---

### Task 6: Brief con aprobación del paciente y correo al terapeuta

**Files:**
- Create: `server/agent/brief.py`, `server/auth/ciba.py`
- Modify: `server/app.py` (ruta `POST /brief`, `_send_brief_after_approval`)

**Interfaces:**
- Produces: `brief.compose(patient, plan, signals, checkins, excluded: list[str]) -> str` (markdown de una página).
- Produces: `ciba.request(sub, message) -> dict(auth_req_id, interval, expires_in)`, `ciba.poll(auth_req_id, interval, timeout_s) -> bool`.
- Produces: ruta `POST /brief` body `{"patient_id"?: int, "force"?: bool}` → `{"results": [{"patient_id", "status": "sent"|"awaiting_whatsapp"|"denied"|"skipped"}]}`.

- [ ] **Step 1: agente del brief**

```python
# server/agent/brief.py
from agents import Agent, Runner
from server import config

INSTRUCTIONS = """Redactas, para un psicólogo, el brief de una página previo a la sesión con su paciente. Español, sobrio, sin diagnosticar.
Formato exacto en markdown, en este orden y con estos títulos:
## Riesgo  (solo si hubo bandera; si no, escribe "Sin señales de riesgo esta semana.")
## Sueño  (tendencia en palabras, con el o los días más cortos)
## Tarea  (hecha o no, y cómo le fue, según los check-ins)
## Ánimo  (trayectoria y los 2–3 momentos de caída, con fecha)
## Quiere tratar  (en palabras del paciente; si no dijo nada, "No indicó temas.")
Usa solo los datos dados. No inventes. Si una señal está excluida por el paciente, no la menciones y no expliques por qué.
"""

_agent = Agent(name="brief", instructions=INSTRUCTIONS, model=config.OPENAI_MODEL)

EXCLUDE_MAP = {"sueño": ("sleep_h",), "sleep": ("sleep_h",), "ánimo": ("mood_valence", "mood_labels"),
               "animo": ("mood_valence", "mood_labels"), "corazón": ("hrv_ms", "resting_hr"), "hrv": ("hrv_ms",)}

def compose(patient: dict, plan: dict | None, signals: list[dict], checkins: list[dict], excluded: list[str]) -> str:
    drop = {k for e in excluded for k in EXCLUDE_MAP.get(e.strip().lower(), ())}
    clean = [{k: v for k, v in s.items() if k not in drop and k not in ("id", "patient_id")} for s in signals]
    risk = any(c.get("risk_flag") for c in checkins)
    data = (f"Paciente: {patient.get('name')}. Sesión previa: {plan.get('session_date') if plan else '?'}. "
            f"Plan — vigilar: {', '.join(plan.get('watch', [])) if plan else '-'}; tarea: {plan.get('homework') if plan else '-'}.\n"
            f"Hubo bandera de riesgo: {'sí' if risk else 'no'}.\nSeñales diarias: {clean}\n"
            f"Check-ins: {[{k: c.get(k) for k in ('at','trigger','mood_1_5','homework_done','note','wants_to_discuss')} for c in checkins]}")
    return Runner.run_sync(_agent, data).final_output
```

- [ ] **Step 2: Auth0 CIBA**

```python
# server/auth/ciba.py
"""Auth0 Asynchronous Authorization (CIBA): push de aprobación al celular del paciente."""
import json, time
import httpx
from server import config

def request(sub: str, message: str) -> dict:
    r = httpx.post(f"https://{config.AUTH0_DOMAIN}/bc-authorize", data={
        "client_id": config.AUTH0_CLIENT_ID, "client_secret": config.AUTH0_CLIENT_SECRET,
        "scope": "openid", "binding_message": message[:64],
        "login_hint": json.dumps({"format": "iss_sub", "iss": f"https://{config.AUTH0_DOMAIN}/", "sub": sub}),
    }, timeout=15)
    r.raise_for_status()
    return r.json()  # auth_req_id, expires_in, interval

def poll(auth_req_id: str, interval: int = 5, timeout_s: int = 120) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = httpx.post(f"https://{config.AUTH0_DOMAIN}/oauth/token", data={
            "grant_type": "urn:openid:params:grant-type:ciba", "auth_req_id": auth_req_id,
            "client_id": config.AUTH0_CLIENT_ID, "client_secret": config.AUTH0_CLIENT_SECRET}, timeout=15)
        if r.status_code == 200:
            return True
        err = r.json().get("error", "")
        if err in ("authorization_pending", "slow_down"):
            time.sleep(interval + (5 if err == "slow_down" else 0)); continue
        return False  # access_denied, expired_token, etc.
    return False

def enabled() -> bool:
    return bool(config.AUTH0_DOMAIN and config.AUTH0_CLIENT_ID and config.AUTH0_CLIENT_SECRET)
```

Requisitos en el tenant (hacer en paralelo al código): aplicación *Regular Web* con **CIBA habilitado** (Applications → tu app → Settings → Advanced → Grant Types: marcar "Client Initiated Backchannel Authentication"), **Guardian** activado como factor push, y el usuario del paciente (Diego, para el demo) enrolado en Guardian. El `auth0_sub` del paciente se obtiene con el login de Google en Auth0; para el demo, copiarlo desde Dashboard → User Management → Users y guardarlo: `sqlite3 between.sqlite "update patients set auth0_sub='google-oauth2|...' where id=1"`.

- [ ] **Step 3: ruta `/brief` y aprobación**

Añadir a `server/app.py` (y reemplazar el stub de `_send_brief_after_approval`):

```python
from datetime import date, timedelta
from server import mail
from server.auth import ciba
from server.agent import brief as brief_agent

class BriefIn(BaseModel):
    patient_id: int | None = None
    force: bool = False

def _deliver_brief(p: dict, content: str, bid: int) -> str:
    to = p.get("therapist_email") or config.THERAPIST_EMAIL
    ok = mail.send(to, f"[Between Sessions] Brief previo a sesión — {p.get('name')}", content)
    store.set_brief(bid, approved=1, sent=int(ok))
    wa.send(p["phone"], "Enviado a tu terapeuta. Gracias por esta semana.")
    return "sent"

async def _send_brief_after_approval(p: dict) -> str:
    b = store.latest_brief(p["id"])
    store.set_patient(p["id"], awaiting_brief=0)
    if not b:
        return "No tengo un resumen pendiente."
    _deliver_brief(p, b["content"], b["id"])
    return None  # _deliver_brief ya avisó por WhatsApp

@app.post("/brief")
def make_briefs(body: BriefIn, x_therapist_key: str | None = Header(default=None)):
    require_key(x_therapist_key)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    results = []
    patients = [store.get_patient(body.patient_id)] if body.patient_id else store.list_patients()
    for p in patients:
        if not p or p["paused"] or not p["ref"]:
            continue
        plan = store.latest_plan(p["id"])
        if not body.force and (not plan or plan.get("next_session_date") != tomorrow):
            results.append({"patient_id": p["id"], "status": "skipped"}); continue
        content = brief_agent.compose(p, plan, store.signals_since(p["id"], 7), store.checkins_since(p["id"], 7),
                                      p.get("excluded_signals") or [])
        bid = store.add_brief(p["id"], content)
        if ciba.enabled() and p.get("auth0_sub"):
            req = ciba.request(p["auth0_sub"], "Compartir brief con tu terapeuta")
            approved = ciba.poll(req["auth_req_id"], int(req.get("interval", 5)), 120)
            if approved:
                results.append({"patient_id": p["id"], "status": _deliver_brief(p, content, bid)})
            else:
                store.set_brief(bid, approved=0)
                mail.send(p.get("therapist_email") or config.THERAPIST_EMAIL,
                          f"[Between Sessions] {p.get('name')} no aprobó compartir esta semana", "Sin contenido.")
                results.append({"patient_id": p["id"], "status": "denied"})
        else:
            store.set_patient(p["id"], awaiting_brief=1)
            wa.send(p["phone"], "Preparé el resumen de tu semana para tu terapeuta. ¿Lo envío? Responde 'sí' o 'no'.")
            results.append({"patient_id": p["id"], "status": "awaiting_whatsapp"})
    return {"results": results}
```

- [ ] **Step 4: prueba manual**

Run: `curl -s -X POST localhost:8000/brief -H "x-therapist-key: dev-therapist-key" -H 'content-type: application/json' -d '{"patient_id":1,"force":true}'`
Expected con Auth0: push de Guardian en el celular → aprobar → correo en `THERAPIST_EMAIL` con las cinco secciones → WhatsApp "Enviado a tu terapeuta".
Expected sin Auth0: WhatsApp "¿Lo envío?" → responder "sí" → correo → confirmación.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: brief previo a sesión con aprobación del paciente (Auth0 CIBA o WhatsApp) y correo al terapeuta"
```

---

### Task 7: Semana sembrada, recorrido completo y despliegue

**Files:**
- Create: `scripts/seed_week.py`, `Dockerfile`, `deploy.sh`, `.dockerignore`

**Interfaces:**
- Consumes: `/health/{token}`, `/plans`, `/decide`, `/checkin`, `/brief`.

- [ ] **Step 1: seed_week.py**

```python
# scripts/seed_week.py
"""Siembra la semana del demo: señales sintéticas + plan fijo. Requiere que el paciente ya escribió 'hola' y su nombre."""
import json, os, sys, sqlite3
import httpx

SERVER = os.environ.get("SERVER", "http://localhost:8000")
KEY = os.environ.get("THERAPIST_KEY", "dev-therapist-key")
DB = os.environ.get("DB_PATH", "between.sqlite")
ref = sys.argv[1] if len(sys.argv) > 1 else "ana"

con = sqlite3.connect(DB)
row = con.execute("select id, health_token from patients where lower(ref)=lower(?)", (ref,)).fetchone()
if not row:
    sys.exit(f"no existe el paciente '{ref}': que escriba 'hola' y su nombre por WhatsApp primero")
pid, token = row
h = httpx.post(f"{SERVER}/health/{token}", json=json.load(open("fixtures/health_sample.json")), timeout=30)
print("health:", h.status_code, h.text)
plan = json.load(open("fixtures/plan_ejemplo.json")); plan["patient_ref"] = ref
p = httpx.post(f"{SERVER}/plans", json=plan, headers={"x-therapist-key": KEY}, timeout=30)
print("plan:", p.status_code, p.text)
d = httpx.post(f"{SERVER}/decide", headers={"x-therapist-key": KEY}, timeout=30)
print("decide:", d.status_code, d.text)
```

Run: `uv run python scripts/seed_week.py ana` → Expected: `health: 200 {"days":7}`, `plan: 200 {...}`, `decide: 200 {"triggered":[{"patient_id":1,"trigger":"sleep_drop"}]}` (si la hora local está fuera de 22–08 y no hubo check-in en 20 h; para forzar en horario de silencio, `sqlite3 between.sqlite "delete from checkins"` y probar de día).

- [ ] **Step 2: recorrido del video (ensayar dos veces antes de grabar)**

1. Pantalla partida: terminal con Quinde (`~/Terapias`) a la izquierda, WhatsApp Web a la derecha.
2. `uv run python bridge/quinde_plan.py fixtures/nota_quinde_ejemplo.json --next-session <mañana>` → se ve el plan; se dice "solo esto sube".
3. Health Auto Export en el iPhone → "Export now" (o `seed_week.py`) → `{"days":7}`.
4. Dashboard de Trigger.dev → Run `evaluate-signals` → llega la pregunta al WhatsApp (por el sueño corto).
5. Responder dos mensajes; el agente cierra.
6. Run `nightly-brief` (o curl `/brief` con `force`) → push de Guardian en el celular → aprobar → abrir el correo con el brief.
7. Cerrar con `pausa` y `no compartas sueño` en el chat: "el paciente manda".

- [ ] **Step 3: Cloud Run (solo si hay cuenta de facturación vinculada)**

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY server ./server
COPY fixtures ./fixtures
ENV PORT=8080 DB_PATH=/tmp/between.sqlite
CMD ["uv", "run", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080"]
```

```
# .dockerignore
.venv
orchestrator/node_modules
*.sqlite
.env
```

```bash
# deploy.sh
#!/usr/bin/env bash
set -euo pipefail
gcloud run deploy between-sessions --source . --region us-east1 --allow-unauthenticated \
  --set-env-vars "$(grep -v '^#' .env | grep -v '^$' | grep -v '^PUBLIC_URL=' | grep -v '^DB_PATH=' | tr '\n' ',' | sed 's/,$//')"
```

Run: `gcloud billing projects link between-sessions-2026 --billing-account=CUENTA && gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com && chmod +x deploy.sh && ./deploy.sh`
Expected: URL `https://between-sessions-....run.app`; actualizar `PUBLIC_URL` y el webhook de Twilio a esa URL. **Nota:** SQLite en `/tmp` no persiste entre instancias; para el demo basta con `--min-instances=1 --max-instances=1`.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: siembra de la semana del demo y despliegue a Cloud Run"
```

---

### Task 8: README, video y post

**Files:**
- Create: `README.md`, `docs/submission.md`

- [ ] **Step 1: README.md (inglés, estructura fija)**

```markdown
# Between Sessions

**The agent that lives between therapy sessions.** The session is documented locally (audio never leaves the therapist's Mac, via [quinde-clinica-local](https://github.com/diegoqprobst/quinde-clinica-local)). Only the structured *plan* goes to the cloud. During the week, a pocket agent on WhatsApp accompanies the patient, guided by Apple Watch signals: it asks one question when sleep, HRV or a logged mood justifies it — not on a schedule. The night before the next session, the therapist receives a one-page brief the patient approved with a push on their phone.

> Built in one day at *Agents, Everywhere* (AI Tinkerers × OpenAI, Miami, Sept 12 2026). All data in this repo, the video and the post is synthetic.

## Why the environment matters
- **Room → local.** Transcript and note never leave the Mac.
- **Cloud ← plan only.** A JSON of what to watch and the homework. Never what the patient said.
- **Pocket = consent.** Auth0 login; the patient decides what is shared and approves every brief with a push (Auth0 CIBA). `pause`, `delete`, `don't share sleep` work from the chat.
- **Watch decides when to talk.** Triggers: sleep drop vs. 14-day median, HRV drop, negative logged mood, 48 h silence, homework day. Max one check-in per 20 h, never 22:00–08:00.
- **Room ← signal.** The therapist gets structure, not raw text.

## How we used each partner
| Partner | What it does here | Where |
|---|---|---|
| OpenAI | Agents SDK for the check-in and brief agents; moderation as the safety guardrail | `server/agent/`, `server/guard.py` |
| Auth0 | Google login + Token Vault; CIBA push approval before anything reaches the therapist | `server/auth/` |
| Trigger.dev | 3-hourly signal evaluation, waitpoint tokens that pause until the patient replies, nightly brief | `orchestrator/src/trigger/` |
| Mozilla.ai | any-llm runs the local bridge on Ollama with the same call shape as the cloud | `bridge/quinde_plan.py` |
| Google Cloud Run | Hosts the FastAPI server | `Dockerfile`, `deploy.sh` |
| Twilio (not a sponsor) | WhatsApp Sandbox channel | `server/channels/twilio.py` |
| Health Auto Export (not a sponsor) | Pushes Apple Health JSON to our endpoint | `server/signals/health.py` |

## Run it
(comandos de Task 0, 1, 4, 5 en orden)

## Path to production (what a hackathon can't do in a day)
- WhatsApp via Twilio is not HIPAA-eligible; SMS is. Same code path.
- The agent is patient-owned (consumer health app → FTC Health Breach Notification Rule, state laws), not a HIPAA covered entity. A therapist-owned deployment needs BAAs (OpenAI: Enterprise + ZDR).
- Crisis handling: 988 (US) message + therapist notification per the plan consented at onboarding. This tool *accompanies, records and summarizes* — it does not detect or diagnose.
- Sandbox 24 h window: outside it, only approved templates (or SMS).
```

- [ ] **Step 2: guion del video (2 minutos)**

```
0:00 Título + una frase: "Los agentes esperan en un chat. Este vive entre sesiones de terapia."
0:10 Sala: Quinde local → puente → "solo esto sube" (plan JSON en pantalla).
0:35 Bolsillo: Watch → señal de sueño corto → Trigger.dev dispara → pregunta en WhatsApp → dos respuestas → cierre.
1:15 Control: 'no compartas sueño' + push de Auth0 en el celular → aprobar → correo con el brief.
1:45 Tesis: "Confidencialidad por control: quién ve qué está en la arquitectura." Logos de partners con qué hizo cada uno.
```

- [ ] **Step 3: post (LinkedIn/X)**

```
Built today at #AgentsEverywhere (@aitinkerers × @OpenAI, Miami): Between Sessions — the agent that lives *between* therapy sessions.
The session stays local. Only the plan goes up. An Apple Watch decides when to ask, WhatsApp is where it asks, and the patient approves with a push what the therapist gets to see.
Thanks @auth0 (consent + CIBA push), @triggerdotdev (waitpoints), @mozilla_ai (any-llm), @googlecloud (Cloud Run). Repo + 2-min demo: <link>
```

- [ ] **Step 4: Commit y push**

```bash
git add -A && git commit -m "docs: README, guion del video y post" && gh repo create between-sessions --public --source=. --push
```

---

## Self-review

**Spec coverage:** §2 tesis → README (T8) y arquitectura (T0–T6). §3 núcleo → T0 (WhatsApp), T1 (Watch), T4 (plan), T3+T5 (check-in por señal con waitpoint), T3 (guardrail), T6 (brief con CIBA y correo). Recortes documentados en el horario. §5.2 Token Vault para Gmail queda como recorte 2 (spec §3), no tiene tarea: el correo sale por SMTP (§7 permite fallback). §6 contratos → T1 (signal), T4 (plan), T3 (checkin). §7 brief → T6. §8 fallos → T3 (guardrail cerrado, riesgo), T5 (timeout 6 h), T6 (denegación), T3 (comandos), README (ventana 24 h). §9 pruebas → T0–T2 unitarias, T7 recorrido. §10 lenguaje → README. §11 sponsors → README. §12 entregables → T8.

**Placeholders:** ninguno; el único stub explícito (`_send_brief_after_approval` en T3) se reemplaza en T6 paso 3.

**Consistencia de nombres:** `store.set_patient(pid, **fields)` se usa igual en T3/T6; `trigger_client.complete(token_id, data)` igual en T3; `wa.send(to, body)` igual en T0/T3/T6; `checkin_agent.open_question/turn` igual en T3 rutas y módulo; `require_key` definido en T2 y usado en T3/T4/T6; `Header` importado en T0.
