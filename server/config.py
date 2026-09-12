import os
from dotenv import load_dotenv

load_dotenv()

def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)

OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-5-mini")
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_FROM = env("TWILIO_FROM", "whatsapp:+14155238886")
TWILIO_VALIDATE = env("TWILIO_VALIDATE", "1") == "1"
PUBLIC_URL = env("PUBLIC_URL", "http://localhost:8000").rstrip("/")
THERAPIST_KEY = env("THERAPIST_KEY", "dev-therapist-key")
THERAPIST_EMAIL = env("THERAPIST_EMAIL", "")
DB_PATH = env("DB_PATH", "between.sqlite")
PATIENT_TZ = env("PATIENT_TZ", "America/New_York")
AUTH0_DOMAIN = env("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID = env("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET = env("AUTH0_CLIENT_SECRET", "")
TRIGGER_SECRET_KEY = env("TRIGGER_SECRET_KEY", "")
TRIGGER_API_URL = env("TRIGGER_API_URL", "https://api.trigger.dev").rstrip("/")
SMTP_HOST = env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER", "")
SMTP_PASS = env("SMTP_PASS", "")
OLLAMA_MODEL = env("OLLAMA_MODEL", "qwen3:14b")
