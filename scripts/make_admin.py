"""Donne (ou retire) l'accès au back-office /admin à un joueur.

Usage : python -m scripts.make_admin Paul
        python -m scripts.make_admin Paul --off
En production : depuis le Shell de Render.
"""
import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.services.accounts import nickname_key


def set_admin(db, nickname: str, is_admin: bool) -> User | None:
    user = db.scalar(select(User).where(User.nickname_key == nickname_key(nickname)))
    if user is not None:
        user.is_admin = is_admin
        db.commit()
    return user


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("nickname", help="pseudo du joueur")
    parser.add_argument("--off", action="store_true", help="retirer l'accès")
    args = parser.parse_args()
    with SessionLocal() as db:
        user = set_admin(db, args.nickname, not args.off)
    if user is None:
        print(f"Joueur inconnu : {args.nickname}")
    else:
        print(f"{user.nickname} : {'admin' if user.is_admin else 'plus admin'}")


if __name__ == "__main__":
    main()
