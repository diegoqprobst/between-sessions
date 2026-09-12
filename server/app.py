from fastapi import FastAPI, Request, Header, HTTPException, Response
from server import config
from server.channels import twilio as wa

app = FastAPI(title="Between Sessions")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/twilio/webhook")
async def twilio_webhook(request: Request, x_twilio_signature: str | None = Header(default=None)):
    form = dict(await request.form())
    url = f"{config.PUBLIC_URL}/twilio/webhook"
    if not wa.valid_signature(url, form, x_twilio_signature):
        raise HTTPException(403, "bad signature")
    sender, body = form.get("From", ""), form.get("Body", "")
    reply = await handle_inbound(sender, body)
    if reply:
        wa.send(sender, reply)
    return Response(content="<Response/>", media_type="application/xml")

async def handle_inbound(sender: str, body: str) -> str | None:
    return f"Recibido: {body}"
