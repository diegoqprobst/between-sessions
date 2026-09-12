"""Cliente de modelos: OpenRouter (por defecto, con política de privacidad por solicitud) u OpenAI directo."""
from openai import AsyncOpenAI, OpenAI
from agents import set_default_openai_client, set_default_openai_api, ModelSettings
from server import config

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

def model_id(name: str | None = None) -> str:
    """Normaliza el id del modelo al destino activo.
    OpenRouter exige prefijo de proveedor ('openai/gpt-5-mini'); OpenAI directo lo rechaza.
    Así el mismo .env funciona en los dos caminos."""
    name = name or config.OPENAI_MODEL
    if config.USE_OPENROUTER:
        return name if "/" in name else f"openai/{name}"
    return name.split("/", 1)[1] if name.startswith("openai/") else name

def provider_policy() -> dict:
    policy = {"data_collection": config.OPENROUTER_DATA_COLLECTION}
    if config.OPENROUTER_ZDR:
        policy["zdr"] = True
    return {"provider": policy}

def model_settings() -> ModelSettings:
    if config.USE_OPENROUTER:
        return ModelSettings(extra_body=provider_policy())
    return ModelSettings()

def sync_client() -> OpenAI:
    if config.USE_OPENROUTER:
        return OpenAI(base_url=OPENROUTER_BASE, api_key=config.OPENROUTER_API_KEY)
    return OpenAI(api_key=config.OPENAI_API_KEY)

def configure_agents() -> None:
    """Debe llamarse antes de crear agentes. Idempotente."""
    if config.USE_OPENROUTER:
        set_default_openai_client(AsyncOpenAI(base_url=OPENROUTER_BASE, api_key=config.OPENROUTER_API_KEY), use_for_tracing=False)
        set_default_openai_api("chat_completions")

configure_agents()
