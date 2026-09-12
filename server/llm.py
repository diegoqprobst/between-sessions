"""Cliente de modelos: OpenRouter (por defecto, con política de privacidad por solicitud) u OpenAI directo."""
from openai import AsyncOpenAI, OpenAI
from agents import set_default_openai_client, set_default_openai_api, ModelSettings
from server import config

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

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
