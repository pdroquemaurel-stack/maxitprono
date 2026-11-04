"""Lecture de la configuration depuis les variables d'environnement (.env en local)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE_URL = "sqlite:///./maxitprono.db"


def normalize_database_url(url: str) -> str:
    """Force le pilote psycopg (v3) pour Postgres.

    Render fournit des URL en postgres:// ou postgresql://, que SQLAlchemy
    associerait à l'ancien pilote psycopg2, non installé.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_football_key: str
    secret_key: str
    default_language: str
    secure_cookies: bool  # cookie envoyé seulement en HTTPS (vrai sur Render)


def load_settings() -> Settings:
    return Settings(
        database_url=normalize_database_url(os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL),
        api_football_key=os.getenv("API_FOOTBALL_KEY", ""),
        secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
        default_language=os.getenv("DEFAULT_LANGUAGE", "fr"),
        secure_cookies=os.getenv("SECURE_COOKIES", "false").lower() == "true",
    )


settings = load_settings()
