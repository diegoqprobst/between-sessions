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
