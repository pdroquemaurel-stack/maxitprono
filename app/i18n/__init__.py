"""Traductions simples : un fichier JSON par langue, français par défaut."""
import json
from pathlib import Path

from app.config import settings

I18N_DIR = Path(__file__).parent
SUPPORTED_LANGUAGES = ("fr", "en")


def _load(lang: str) -> dict:
    return json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))


TRANSLATIONS = {lang: _load(lang) for lang in SUPPORTED_LANGUAGES}


def translate(key: str, lang: str = settings.default_language) -> str:
    """Renvoie le texte traduit ; retombe sur le français, puis sur la clé elle-même."""
    return TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["fr"].get(key) or key
