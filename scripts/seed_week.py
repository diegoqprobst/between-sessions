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
