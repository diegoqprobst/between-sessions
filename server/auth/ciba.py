"""Auth0 Asynchronous Authorization (CIBA): push de aprobación al celular del paciente."""
import json, time
import httpx
from server import config

def request(sub: str, message: str) -> dict:
    r = httpx.post(f"https://{config.AUTH0_DOMAIN}/bc-authorize", data={
        "client_id": config.AUTH0_CLIENT_ID, "client_secret": config.AUTH0_CLIENT_SECRET,
        "scope": "openid", "binding_message": message[:64],
        "login_hint": json.dumps({"format": "iss_sub", "iss": f"https://{config.AUTH0_DOMAIN}/", "sub": sub}),
    }, timeout=15)
    r.raise_for_status()
    return r.json()  # auth_req_id, expires_in, interval

def poll(auth_req_id: str, interval: int = 5, timeout_s: int = 120) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = httpx.post(f"https://{config.AUTH0_DOMAIN}/oauth/token", data={
            "grant_type": "urn:openid:params:grant-type:ciba", "auth_req_id": auth_req_id,
            "client_id": config.AUTH0_CLIENT_ID, "client_secret": config.AUTH0_CLIENT_SECRET}, timeout=15)
        if r.status_code == 200:
            return True
        err = r.json().get("error", "")
        if err in ("authorization_pending", "slow_down"):
            time.sleep(interval + (5 if err == "slow_down" else 0)); continue
        return False  # access_denied, expired_token, etc.
    return False

def enabled() -> bool:
    return bool(config.AUTH0_DOMAIN and config.AUTH0_CLIENT_ID and config.AUTH0_CLIENT_SECRET)
