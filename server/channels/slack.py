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
    """Send a DM to a Slack user. Without a token, print for the local demo."""
    user_id = to[len(PREFIX):] if to.startswith(PREFIX) else to
    if not config.SLACK_BOT_TOKEN:
        print(f"[slack] (sin token) → {user_id}: {body}")
        return "local"
    # Scheduled check-ins happen outside an inbound event, so we cannot rely on
    # Bolt's `say()` callback. Open (or retrieve) the one-to-one DM first.
    dm = client().conversations_open(users=user_id)
    channel_id = dm["channel"]["id"]
    res = client().chat_postMessage(channel=channel_id, text=body)
    return res.get("ts", "")
