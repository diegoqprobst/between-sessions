"""Guardrail de riesgo. Falla cerrado: sin veredicto, el mensaje no llega al modelo.

Tres backends, según el proveedor activo:
  openrouter → Llama Guard 4 (clasificador dedicado)
  gemini / openai → el mismo modelo de chat, con el formato de salida de Llama Guard
Todos devuelven 'safe' o 'unsafe\\nS11', y los parsea la misma función probada.
"""
from server import config, llm

RISK_REPLY = (
    "Gracias por contarme esto. No soy un servicio de emergencia. "
    "Si estás en peligro ahora mismo, llama o escribe al 988 (EE. UU.) o al 911. "
    "Voy a avisar a tu terapeuta como acordamos al inicio. ¿Estás en un lugar seguro en este momento?"
)
UNAVAILABLE_REPLY = "Ahora mismo no puedo leer mensajes. Si es urgente, llama al 988 o al 911. Te escribo en cuanto vuelva."

SELF_HARM = "S11"

CLASSIFIER_PROMPT = """You are a safety classifier. Read the user message and classify it.

Categories:
S1: Violent crimes
S6: Specialized advice (medical, legal, financial)
S10: Hate
S11: Suicide & self-harm (including passive ideation, hopelessness about living, self-injury)

Answer with EXACTLY this format and nothing else:
safe
or
unsafe
S11

Use only the category codes above, comma-separated on the second line. No explanation, no punctuation, no preamble."""

def parse_llama_guard(text: str) -> dict:
    """'safe' → sin riesgo; 'unsafe\\nS11,S6' → categorías. Cualquier otra cosa: sin veredicto."""
    lines = [l.strip() for l in (text or "").strip().splitlines() if l.strip()]
    if not lines:
        return {"ok": False, "risk": None, "categories": []}
    head = lines[0].lower()
    if head == "safe":
        return {"ok": True, "risk": False, "categories": []}
    if head.startswith("unsafe"):
        cats = [c.strip().upper() for l in lines[1:] for c in l.split(",") if c.strip()]
        return {"ok": True, "risk": SELF_HARM in cats, "categories": cats}
    return {"ok": False, "risk": None, "categories": []}

def _classify(text: str) -> dict:
    """Un clasificador dedicado si lo hay; si no, el modelo de chat con el mismo formato."""
    dedicated = llm.provider() == "openrouter"
    model = config.GUARD_MODEL if dedicated else llm.model_id()
    messages = ([{"role": "user", "content": text}] if dedicated
                else [{"role": "system", "content": CLASSIFIER_PROMPT}, {"role": "user", "content": text}])
    res = llm.sync_client().chat.completions.create(
        model=llm.model_id(model) if dedicated else model,
        messages=messages, max_tokens=20, temperature=0, extra_body=llm.provider_policy())
    return parse_llama_guard(res.choices[0].message.content)

def assess(text: str) -> dict:
    if not llm.configured():
        return {"ok": False, "risk": None, "categories": []}
    try:
        return _classify(text)
    except Exception:
        return {"ok": False, "risk": None, "categories": []}
