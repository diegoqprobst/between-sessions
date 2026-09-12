"""Capa de modelo. Un solo sitio decide a qué proveedor se habla.

Precedencia por clave presente: OpenRouter → Gemini → OpenAI. Todos exponen
API compatible con OpenAI, así que el Agents SDK funciona igual en los tres.
"""
from openai import AsyncOpenAI, OpenAI
from agents import set_default_openai_client, set_default_openai_api, set_tracing_disabled, ModelSettings
from server import config

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
OLLAMA_BASE = "http://localhost:11434/v1"

DEFAULT_MODEL = {"ollama": "qwen3:14b", "openrouter": "openai/gpt-5.4-mini",
                 "gemini": "gemini-3.8-flash", "openai": "gpt-5-mini"}

def provider() -> str:
    """Local primero: el demo corre entero en la máquina del terapeuta, que es la tesis.
    Una clave de nube solo toma el mando si LOCAL_FIRST está apagado."""
    if config.FORCE_PROVIDER:
        return config.FORCE_PROVIDER
    if config.LOCAL_FIRST:
        return "ollama"
    if config.OPENROUTER_API_KEY:
        return "openrouter"
    if config.GEMINI_API_KEY:
        return "gemini"
    return "openai"

def api_key() -> str:
    if provider() == "ollama":
        return "ollama"  # Ollama ignora la clave, pero el SDK exige uno no vacío
    return {"openrouter": config.OPENROUTER_API_KEY, "gemini": config.GEMINI_API_KEY,
            "openai": config.OPENAI_API_KEY}.get(provider()) or ""

def base_url() -> str | None:
    return {"openrouter": OPENROUTER_BASE, "gemini": GEMINI_BASE, "ollama": OLLAMA_BASE}.get(provider())

def is_local() -> bool:
    return provider() == "ollama"

def configured() -> bool:
    """Hay con qué hablar. Si es False, el flujo debe degradar, nunca inventar."""
    return bool(api_key())

def model_id(name: str | None = None) -> str:
    """Normaliza el id del modelo al proveedor activo.

    OpenRouter exige prefijo ('openai/gpt-5-mini'); OpenAI y Gemini lo rechazan.
    Así el mismo .env sirve para los tres caminos.
    """
    p = provider()
    if p == "ollama":
        return name or config.LOCAL_MODEL or DEFAULT_MODEL["ollama"]
    name = name or config.OPENAI_MODEL or DEFAULT_MODEL[p]
    if p == "ollama":
        return name  # los ids de Ollama ya llevan su propia forma (qwen3:14b, llama-guard3:1b)
    if p == "openrouter":
        return name if "/" in name else f"openai/{name}"
    if name.startswith(("openai/", "google/", "meta-llama/")):
        name = name.split("/", 1)[1]
    # Un id de otro proveedor no sirve aquí: cae al modelo por defecto del activo.
    if p == "gemini" and not name.startswith("gemini"):
        return DEFAULT_MODEL["gemini"]
    if p == "openai" and not name.startswith("gpt"):
        return DEFAULT_MODEL["openai"]
    return name

THINK_OPEN, THINK_CLOSE = "<think>", "</think>"

def strip_thinking(text: str) -> str:
    """Los modelos locales de razonamiento (qwen3) emiten <think>…</think> en el contenido.
    El Agents SDK lo maneja con salida estructurada; las llamadas crudas no, así que se limpia aquí."""
    out = text or ""
    while THINK_OPEN in out and THINK_CLOSE in out:
        start, end = out.index(THINK_OPEN), out.index(THINK_CLOSE) + len(THINK_CLOSE)
        if end <= start:
            break
        out = out[:start] + out[end:]
    # Un bloque de razonamiento sin cerrar (respuesta truncada) no deja nada aprovechable.
    if THINK_OPEN in out:
        out = out.split(THINK_OPEN)[0]
    return out.strip()

def guard_model() -> str:
    """Clasificador de seguridad dedicado por proveedor; cadena vacía = no hay uno."""
    p = provider()
    if p == "ollama":
        return config.LOCAL_GUARD_MODEL
    if p == "openrouter":
        return config.GUARD_MODEL
    return ""

def provider_policy() -> dict:
    """Política de privacidad por solicitud. Solo OpenRouter la entiende."""
    if provider() != "openrouter":
        return {}
    policy = {"data_collection": config.OPENROUTER_DATA_COLLECTION}
    if config.OPENROUTER_ZDR:
        policy["zdr"] = True
    return {"provider": policy}

def model_settings() -> ModelSettings:
    extra = provider_policy()
    return ModelSettings(extra_body=extra) if extra else ModelSettings()

def sync_client() -> OpenAI:
    return OpenAI(api_key=api_key() or "missing", base_url=base_url())

def configure_agents() -> None:
    """Apunta el Agents SDK al proveedor activo. Idempotente."""
    set_tracing_disabled(True)
    if base_url():
        set_default_openai_client(AsyncOpenAI(api_key=api_key() or "missing", base_url=base_url()),
                                  use_for_tracing=False)
        set_default_openai_api("chat_completions")

configure_agents()
