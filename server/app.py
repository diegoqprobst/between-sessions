from datetime import datetime, timezone
from fastapi import FastAPI, Request, Header, HTTPException, Response
from pydantic import BaseModel
from server import config, store, decide, guard, trigger_client
from server.channels import twilio as wa
from server.signals import health as health_signals
from server.agent import checkin as checkin_agent

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
        store.add_checkin(pid, {"trigger": p["pending_trigger"] or "spontaneous", "risk_flag": True,
                                "note": "riesgo detectado por guardrail", "status": "risk"})
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

async def _send_brief_after_approval(p: dict) -> str:
    return "Gracias, lo envío."  # se reemplaza en la Tarea 6

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
