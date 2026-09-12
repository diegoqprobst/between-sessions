"""Entrega del brief en el espacio de trabajo del clínico (Ambiguous AI).

El correo funciona siempre; esto añade lo que el correo no puede: el agente existe
como compañero con identidad propia, el brief queda como documento que el clínico
puede comentar, y una tarea recuerda revisarlo antes de la sesión.
"""
import httpx
from server import config

BASE = "https://app.ambiguous.ai/api"
AGENT_USERNAME = "between"

def enabled() -> bool:
    return bool(config.AMBIGUOUS_API_KEY)

def _client(as_agent: bool = False) -> httpx.Client:
    """as_agent=True firma con la identidad del agente, para que el documento
    aparezca escrito por 'Between Sessions' y no por la persona."""
    key = (config.AMBIGUOUS_AGENT_KEY if as_agent and config.AMBIGUOUS_AGENT_KEY
           else config.AMBIGUOUS_API_KEY)
    return httpx.Client(base_url=BASE, timeout=25,
                        headers={"Authorization": f"Bearer {key}",
                                 "content-type": "application/json"})

def call(method: str, path: str, payload: dict | None = None, as_agent: bool = False) -> tuple[int, dict]:
    """Devuelve (código, cuerpo). Nunca lanza: la entrega por correo no debe caerse por esto."""
    try:
        with _client(as_agent) as c:
            r = c.request(method, path, json=payload)
            try:
                return r.status_code, r.json()
            except ValueError:
                return r.status_code, {"raw": r.text[:300]}
    except httpx.HTTPError as e:
        return 0, {"error": str(e)[:200]}

def find_agent() -> dict | None:
    code, body = call("GET", "/admin/users")
    if code != 200:
        return None
    for u in body.get("data", []):
        if u.get("username") == AGENT_USERNAME or u.get("type") == "agent":
            return u
    return None

def provision_agent(display_name: str = "Between Sessions") -> tuple[int, dict]:
    return call("POST", "/admin/users/provision-agent",
                {"display_name": display_name, "username": AGENT_USERNAME, "role": "member"})

def deliver_brief(patient_name: str, content: str, session_date: str | None) -> dict:
    """Publica el brief en el espacio del clínico, firmado por el agente.

    Es un extra sobre el correo, nunca un sustituto: si algo falla, se informa
    y el correo ya salió. Devuelve qué se creó, para poder decirlo en el log.
    """
    if not enabled():
        return {"enabled": False}
    out: dict = {"enabled": True}
    title = f"Brief previo a sesión — {patient_name}"
    code, body = call("POST", "/documents",
                      {"title": title, "type": "doc", "content": content}, as_agent=True)
    out["document"] = {"ok": code < 300, "id": body.get("id"), "owner": body.get("owner_username")}
    if code >= 300:
        out["document"]["error"] = str(body)[:200]
        return out
    due = f" (sesión {session_date})" if session_date else ""
    tcode, tbody = call("POST", "/tasks",
                        {"title": f"Revisar el brief de {patient_name} antes de la sesión{due}",
                         "description": f"Documento: {title}. Lo aprobó {patient_name} desde su chat."},
                        as_agent=True)
    task = (tbody or {}).get("task", {})
    out["task"] = {"ok": tcode < 300, "key": task.get("task_key")}
    return out
