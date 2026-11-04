"""Lecture de la configuration depuis les variables d'environnement (.env en local)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE_URL = "sqlite:///./maxitprono.db"


@dataclass(frozen=True)
class Settings:
    database_url: str
    api_football_key: str
    secret_key: str
    default_language: str


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL,
        api_football_key=os.getenv("API_FOOTBALL_KEY", ""),
        secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
        default_language=os.getenv("DEFAULT_LANGUAGE", "fr"),
    )


settings = load_settings()
