from datetime import datetime, timezone
from fastapi import FastAPI, Request, Header, HTTPException, Response
from server import config, store, decide
from server.channels import twilio as wa
from server.signals import health as health_signals

app = FastAPI(title="Between Sessions")

@app.on_event("startup")
def _startup():
    store.init_db()

def require_key(key: str | None):
    if key != config.THERAPIST_KEY:
        raise HTTPException(401, "bad key")

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
