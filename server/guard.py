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

# Red determinista de ideación explícita. Existe porque los clasificadores probabilísticos
# fallan en español: llama-guard3:1b marcó "ya no quiero seguir viviendo" como segura.
# Esto no sustituye al modelo, va ANTES: lo que cae aquí es riesgo, sin discusión.
IDEATION = [
    r"no quiero (seguir )?(vivir|viviendo)",
    r"no quiero (seguir )?(estando |estar )?(aqu[ií]|ac[aá])",
    r"(me )?quiero (matar(me)?|morir(me)?|desaparecer)",
    r"me (quiero|voy a) morir(me)?",
    r"quitarme la vida",
    r"acabar con (todo|mi vida)",
    r"hacerme da[ñn]o",
    r"(lastimarme|cortarme|autolesion)",
    r"suicid(arme|io|a)",
    r"no vale la pena vivir",
    r"(estar[ií]an|estar[ií]a) mejor sin m[ií]",
    r"kill myself",
    r"end (my life|it all)",
    r"(don'?t|do not) want to (live|be here)",
    r"want to die",
    r"(hurt|harm)(ing)? myself",
    r"better off dead",
    r"no reason to live",
    r"self.?harm",
]
# Frases hechas que contienen las palabras pero no son ideación.
IDIOMS = [
    r"me muero de (sue[ñn]o|hambre|sed|risa|ganas|fr[ií]o|calor|verg[üu]enza)",
    r"matarme a (trabajar|estudiar)",
    r"me mata(n)? (el|la|los|las) ",
]

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

def _normalize(text: str) -> str:
    import unicodedata
    lowered = (text or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", lowered) if unicodedata.category(c) != "Mn")

def matches_ideation(text: str) -> bool:
    """True si el texto contiene ideación explícita. Determinista, sin red, sin modelo."""
    import re
    norm = _normalize(text)
    for idiom in IDIOMS:
        norm = re.sub(idiom, " ", norm)
    return any(re.search(_normalize(p), norm) for p in IDEATION)

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
    """Un clasificador dedicado si lo hay (Llama Guard, local o en OpenRouter);
    si no, el modelo de chat activo con el mismo formato de salida."""
    dedicated = llm.guard_model()
    model = dedicated or llm.model_id()
    messages = ([{"role": "user", "content": text}] if dedicated
                else [{"role": "system", "content": CLASSIFIER_PROMPT}, {"role": "user", "content": text}])
    res = llm.sync_client().chat.completions.create(
        model=model, messages=messages, max_tokens=64, temperature=0,
        extra_body=llm.provider_policy())
    return parse_llama_guard(llm.strip_thinking(res.choices[0].message.content))

def assess(text: str) -> dict:
    """Dos capas. La red determinista decide primero y no se puede desdecir;
    el clasificador solo puede AÑADIR riesgo, nunca quitarlo."""
    if matches_ideation(text):
        return {"ok": True, "risk": True, "categories": [SELF_HARM], "source": "phrase"}
    if not llm.configured():
        return {"ok": False, "risk": None, "categories": []}
    try:
        verdict = _classify(text)
        verdict["source"] = "model"
        return verdict
    except Exception:
        return {"ok": False, "risk": None, "categories": []}
