"""Proceso del bot de Slack (Socket Mode): recibe DMs y los pasa al mismo flujo que WhatsApp.
Uso: uv run python -m server.slack_app"""
import asyncio
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from server import config, store
from server.app import handle_inbound
from server.channels import slack as slack_channel

app = App(token=config.SLACK_BOT_TOKEN)

@app.event("message")
def on_message(event, say, logger):
    if event.get("channel_type") != "im" or event.get("bot_id") or event.get("subtype"):
        return
    sender = f"{slack_channel.PREFIX}{event['user']}"
    reply = asyncio.run(handle_inbound(sender, event.get("text", "")))
    if reply:
        store.add_message(store.get_or_create_patient(sender)["id"], "out", reply)
        say(reply)

def main() -> None:
    if not (config.SLACK_BOT_TOKEN and config.SLACK_APP_TOKEN):
        raise SystemExit("faltan SLACK_BOT_TOKEN (xoxb-) y SLACK_APP_TOKEN (xapp-) en .env")
    store.init_db()
    print("[slack] conectado en Socket Mode; escribe un DM al bot")
    SocketModeHandler(app, config.SLACK_APP_TOKEN).start()

if __name__ == "__main__":
    main()
