"""Authentification du POC : pseudo + code PIN à 4 chiffres.

Plus tard, un module `maxit_auth` (wx.login) offrira le même résultat :
un user_id interne. Le reste de l'app ne dépend que de ce user_id.
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.i18n.countries import COUNTRY_CODES
from app.models import User
from app.services.accounts import (
    after_failed_attempt,
    hash_pin,
    is_locked,
    nickname_key,
    validate_country,
    validate_nickname,
    validate_pin,
    verify_pin,
)


@dataclass
class AuthResult:
    user_id: int | None = None
    error: str | None = None  # clé de traduction du message d'erreur


def register(db: Session, nickname: str, pin: str, country_code: str,
             rules_accepted: bool, now: datetime) -> AuthResult:
    nickname = nickname.strip()
    error = (validate_nickname(nickname) or validate_pin(pin)
             or validate_country(country_code, COUNTRY_CODES))
    if error is None and not rules_accepted:
        error = "error_rules_not_accepted"
    if error is None and _find_user(db, nickname) is not None:
        error = "error_nickname_taken"
    if error:
        return AuthResult(error=error)

    user = User(nickname=nickname, nickname_key=nickname_key(nickname), pin_hash=hash_pin(pin),
                country_code=country_code, rules_accepted_at=now, created_at=now)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # même pseudo créé au même instant par un autre joueur
        db.rollback()
        return AuthResult(error="error_nickname_taken")
    return AuthResult(user_id=user.id)


def login(db: Session, nickname: str, pin: str, now: datetime) -> AuthResult:
    user = _find_user(db, nickname)
    if user is None:
        return AuthResult(error="error_login")  # même message que PIN faux
    if is_locked(user.locked_until, now):
        return AuthResult(error="error_locked")

    if not verify_pin(pin, user.pin_hash):
        user.failed_pin_attempts, user.locked_until = after_failed_attempt(
            user.failed_pin_attempts, now)
        db.commit()
        return AuthResult(error="error_locked" if user.locked_until else "error_login")

    user.failed_pin_attempts, user.locked_until = 0, None
    db.commit()
    return AuthResult(user_id=user.id)


def _find_user(db: Session, nickname: str) -> User | None:
    return db.scalar(select(User).where(User.nickname_key == nickname_key(nickname)))
