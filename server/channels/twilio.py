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
    """to: 'whatsapp:+1305...' . Devuelve el SID del mensaje. Sin credenciales, imprime (modo local)."""
    if not (config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN):
        print(f"[whatsapp] (sin Twilio) → {to}: {body}")
        return "local"
    msg = client().messages.create(from_=config.TWILIO_FROM, to=to, body=body)
    return msg.sid

def valid_signature(url: str, params: dict, signature: str | None) -> bool:
    if not config.TWILIO_VALIDATE:
        return True
    return RequestValidator(config.TWILIO_AUTH_TOKEN).validate(url, params, signature or "")

_CMD = re.compile(r"^\s*(pausa|pause|reanudar|resume|borrar|delete|no compartas|don't share|plan:|plan|sugerir|suggest)\s*(.*)$", re.I)

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
    if word in ("sugerir", "suggest"):
        return ("suggest", "")
    if word.startswith("plan"):
        return ("plan", arg.lstrip(":").strip()) if arg.strip(":").strip() else None
    return ("exclude", arg)

def parse_self_plan(text: str) -> dict:
    """'dormir 7h; cortar a las 6 | tarea: caminar 20 min' → watch + homework."""
    watch_part, _, homework = text.partition("|")
    homework = homework.split(":", 1)[-1].strip() if homework else ""
    watch = [w.strip() for w in watch_part.split(";") if w.strip()]
    return {"watch": watch, "homework": homework}
