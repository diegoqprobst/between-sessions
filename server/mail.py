import smtplib
from email.message import EmailMessage
from server import config

def send(to: str, subject: str, body: str) -> bool:
    if not (config.SMTP_USER and config.SMTP_PASS and to):
        print(f"[mail] (sin SMTP) → {to}: {subject}\n{body}")
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_USER, to, subject
    msg.set_content(body)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.starttls(); s.login(config.SMTP_USER, config.SMTP_PASS); s.send_message(msg)
    return True
