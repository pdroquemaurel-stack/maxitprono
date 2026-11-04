"""Cookie de session signé (HMAC) contenant uniquement le user_id interne.

Format du cookie : "<user_id>.<horodatage>.<signature>".
Le cookie ne peut pas être modifié par le joueur sans connaître SECRET_KEY.
"""
import hashlib
import hmac
from datetime import datetime, timedelta

from app.config import settings

COOKIE_NAME = "session"
SESSION_DURATION = timedelta(days=30)


def sign_session(user_id: int, now: datetime, secret: str = settings.secret_key) -> str:
    payload = f"{user_id}.{int(now.timestamp())}"
    return f"{payload}.{_signature(payload, secret)}"


def read_session(cookie: str | None, now: datetime, secret: str = settings.secret_key) -> int | None:
    """Renvoie le user_id si le cookie est authentique et pas expiré, sinon None."""
    if not cookie:
        return None
    try:
        user_id, issued_at, signature = cookie.split(".")
        payload = f"{user_id}.{issued_at}"
        if not hmac.compare_digest(signature, _signature(payload, secret)):
            return None
        if now.timestamp() - int(issued_at) > SESSION_DURATION.total_seconds():
            return None
        return int(user_id)
    except ValueError:
        return None


def _signature(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
