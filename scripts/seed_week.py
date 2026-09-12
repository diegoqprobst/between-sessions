"""Siembra la semana del demo: señales sintéticas + plan fijo. Requiere que el paciente ya escribió 'hola' y su nombre."""
import json, os, sys, sqlite3, re
from datetime import date, timedelta
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
def shifted(path: str, last_day_in_fixture: str) -> dict:
    """Desplaza todas las fechas del fixture para que su último día sea hoy (la noche corta cae hoy)."""
    offset = (date.today() - date.fromisoformat(last_day_in_fixture)).days
    raw = open(path).read()
    def bump(m):
        return (date.fromisoformat(m.group(0)) + timedelta(days=offset)).isoformat()
    return json.loads(re.sub(r"\d{4}-\d{2}-\d{2}", bump, raw))

h = httpx.post(f"{SERVER}/health/{token}", json=shifted("fixtures/health_sample.json", "2026-09-12"), timeout=30)
print("health:", h.status_code, h.text)
plan = json.load(open("fixtures/plan_ejemplo.json")); plan["patient_ref"] = ref
plan["session_date"] = (date.today() - timedelta(days=6)).isoformat()      # sesión hace 6 días → hoy también es día de tarea
plan["next_session_date"] = (date.today() + timedelta(days=1)).isoformat()  # sesión mañana → el brief nocturno aplica
p = httpx.post(f"{SERVER}/plans", json=plan, headers={"x-therapist-key": KEY}, timeout=30)
print("plan:", p.status_code, p.text)
d = httpx.post(f"{SERVER}/decide", headers={"x-therapist-key": KEY}, timeout=30)
print("decide:", d.status_code, d.text)
