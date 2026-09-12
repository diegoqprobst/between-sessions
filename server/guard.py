"""Guardrail de riesgo. Falla cerrado: sin veredicto, el mensaje no llega al modelo.
Backend: Llama Guard 4 vía OpenRouter (por defecto) o el endpoint de moderación de OpenAI."""
from server import config, llm

RISK_REPLY = (
    "Gracias por contarme esto. No soy un servicio de emergencia. "
    "Si estás en peligro ahora mismo, llama o escribe al 988 (EE. UU.) o al 911. "
    "Voy a avisar a tu terapeuta como acordamos al inicio. ¿Estás en un lugar seguro en este momento?"
)
UNAVAILABLE_REPLY = "Ahora mismo no puedo leer mensajes. Si es urgente, llama al 988 o al 911. Te escribo en cuanto vuelva."

LLAMA_GUARD_SELF_HARM = "S11"   # categoría "Suicide & Self-Harm" de Llama Guard
OPENAI_RISK_PREFIXES = ("self-harm",)

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
        return {"ok": True, "risk": LLAMA_GUARD_SELF_HARM in cats, "categories": cats}
    return {"ok": False, "risk": None, "categories": []}

def _assess_llama_guard(text: str) -> dict:
    res = llm.sync_client().chat.completions.create(
        model=config.GUARD_MODEL, messages=[{"role": "user", "content": text}], max_tokens=20, temperature=0,
        extra_body=llm.provider_policy())
    return parse_llama_guard(res.choices[0].message.content)

def _assess_openai_moderation(text: str) -> dict:
    res = llm.sync_client().moderations.create(model="omni-moderation-latest", input=text)
    r = res.results[0]
    cats = [k for k, v in r.categories.model_dump().items() if v]
    return {"ok": True, "risk": any(c.startswith(OPENAI_RISK_PREFIXES) for c in cats), "categories": cats}

def assess(text: str) -> dict:
    try:
        return _assess_llama_guard(text) if config.USE_OPENROUTER else _assess_openai_moderation(text)
    except Exception:
        return {"ok": False, "risk": None, "categories": []}
