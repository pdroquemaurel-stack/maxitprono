"""Règles des comptes joueurs : validation, hash du PIN, blocage après erreurs.

Fonctions pures : aucune base de données, la date courante est passée en paramètre.
"""
import base64
import binascii
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta

NICKNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,20}$")
PIN_PATTERN = re.compile(r"^[0-9]{4}$")

MAX_PIN_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=15)

PBKDF2_ITERATIONS = 200_000

# Le navigateur réduit la photo à ~20 Ko ; on accepte plus large pour l'envoi sans JavaScript
MAX_AVATAR_BYTES = 300_000
AVATAR_SIGNATURES = {b"\xff\xd8\xff": "image/jpeg", b"\x89PNG\r\n\x1a\n": "image/png"}


# --- Validation (renvoie une clé de traduction d'erreur, ou None si valide) ---

def validate_nickname(nickname: str) -> str | None:
    if not NICKNAME_PATTERN.match(nickname):
        return "error_nickname_format"
    return None


def validate_pin(pin: str) -> str | None:
    if not PIN_PATTERN.match(pin):
        return "error_pin_format"
    return None


def validate_country(country_code: str, known_codes: set[str]) -> str | None:
    if country_code not in known_codes:
        return "error_country"
    return None


def nickname_key(nickname: str) -> str:
    """Forme utilisée pour l'unicité : « Paul » et « paul » sont le même pseudo."""
    return nickname.strip().lower()


# --- Hash du PIN (stockage : "pbkdf2$<itérations>$<sel>$<hash>") ---

def hash_pin(pin: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = _pbkdf2(pin, salt, PBKDF2_ITERATIONS)
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    return hmac.compare_digest(_pbkdf2(pin, salt, int(iterations)), digest)


def _pbkdf2(pin: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), iterations).hex()


# --- Blocage après trop de PIN faux ---

def is_locked(locked_until: datetime | None, now: datetime) -> bool:
    return locked_until is not None and now < locked_until


def after_failed_attempt(failed_attempts: int, now: datetime) -> tuple[int, datetime | None]:
    """Renvoie (nouveau compteur, date de fin de blocage ou None).

    Au 5e échec, le compte est bloqué 15 minutes et le compteur repart à zéro.
    """
    failed_attempts += 1
    if failed_attempts >= MAX_PIN_ATTEMPTS:
        return 0, now + LOCK_DURATION
    return failed_attempts, None


# --- Avatar ---

def decode_data_url(value: str) -> bytes | None:
    """Décode "data:image/jpeg;base64,..." envoyé par le navigateur ; None si illisible."""
    _, _, encoded = value.partition(";base64,")
    try:
        return base64.b64decode(encoded, validate=True) or None
    except binascii.Error:
        return None


def avatar_mime(data: bytes) -> tuple[str | None, str | None]:
    """Renvoie (type MIME, erreur) : seules les images JPEG et PNG de taille raisonnable passent."""
    if len(data) > MAX_AVATAR_BYTES:
        return None, "error_avatar_too_big"
    for signature, mime in AVATAR_SIGNATURES.items():
        if data.startswith(signature):
            return mime, None
    return None, "error_avatar_format"
