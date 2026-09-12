"""API de solo lectura para el panel. No expone texto crudo del paciente:
el panel del clínico ve señales, check-ins estructurados y el brief aprobado."""
from fastapi import APIRouter, HTTPException
from server import store

router = APIRouter(prefix="/api", tags=["panel"])

CONSENT_FIELDS = ("paused", "excluded_signals", "awaiting_brief")

def _patient_public(p: dict) -> dict:
    """Perfil sin datos de contacto: el panel no necesita el teléfono ni el id de Slack."""
    return {"id": p["id"], "name": p.get("name"), "ref": p.get("ref"),
            "channel": "slack" if (p.get("phone") or "").startswith("slack:") else "whatsapp",
            "consent": {k: p.get(k) for k in CONSENT_FIELDS}}

@router.get("/patients")
def list_patients():
    return {"patients": [_patient_public(p) for p in store.list_patients() if p.get("ref")]}

def _require(pid: int) -> dict:
    p = store.get_patient(pid)
    if not p:
        raise HTTPException(404, "unknown patient")
    return p

@router.get("/patients/{pid}")
def get_patient(pid: int):
    p = _require(pid)
    return {**_patient_public(p), "plan": store.latest_plan(pid)}

@router.get("/patients/{pid}/signals")
def get_signals(pid: int, days: int = 14):
    _require(pid)
    rows = store.signals_since(pid, days)
    return {"days": days, "signals": [{k: v for k, v in r.items() if k != "patient_id"} for r in rows]}

@router.get("/patients/{pid}/checkins")
def get_checkins(pid: int, days: int = 7):
    _require(pid)
    return {"days": days, "checkins": [{k: v for k, v in c.items() if k != "patient_id"}
                                       for c in store.checkins_since(pid, days)]}

@router.get("/patients/{pid}/brief")
def get_brief(pid: int):
    _require(pid)
    b = store.latest_brief(pid)
    if not b:
        raise HTTPException(404, "no brief yet")
    return {"at": b["at"], "content": b["content"],
            "approved": bool(b["approved"]), "sent": bool(b["sent"])}
