"""Enrutador de canales: el id del paciente dice por dónde responder."""
from server.channels import slack, twilio

def send(to: str, body: str) -> str:
    if to.startswith(slack.PREFIX):
        return slack.send(to, body)
    return twilio.send(to, body)
