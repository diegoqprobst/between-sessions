import httpx
from server import config

def complete(token_id: str | None, data: dict) -> bool:
    """Completa un waitpoint token de Trigger.dev. Devuelve False si no hay token o falla."""
    if not token_id or not config.TRIGGER_SECRET_KEY:
        return False
    try:
        r = httpx.post(f"{config.TRIGGER_API_URL}/api/v1/waitpoints/tokens/{token_id}/complete",
                       headers={"Authorization": f"Bearer {config.TRIGGER_SECRET_KEY}"},
                       json={"data": data}, timeout=10)
        return r.status_code < 300
    except httpx.HTTPError:
        return False
