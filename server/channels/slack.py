"""Canal Slack: mensajes directos con el bot. Los ids de paciente son 'slack:<user_id>'."""
from slack_sdk import WebClient
from server import config

PREFIX = "slack:"
_client: WebClient | None = None

def client() -> WebClient:
    global _client
    if _client is None:
        _client = WebClient(token=config.SLACK_BOT_TOKEN)
    return _client

def send(to: str, body: str) -> str:
    """to: 'slack:U0123'. Sin token, imprime (modo local)."""
    user_id = to[len(PREFIX):] if to.startswith(PREFIX) else to
    if not config.SLACK_BOT_TOKEN:
        print(f"[slack] (sin token) → {user_id}: {body}")
        return "local"
    res = client().chat_postMessage(channel=user_id, text=body)
    return res.get("ts", "")
