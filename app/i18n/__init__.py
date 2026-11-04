"""Traductions simples : un fichier JSON par langue, français par défaut."""
import json
from datetime import date, datetime, tzinfo
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


def format_day(day: date, today: date, lang: str = settings.default_language) -> str:
    """« Aujourd'hui », « Demain », sinon « mardi 10 novembre »."""
    if day == today:
        return translate("today", lang)
    if (day - today).days == 1:
        return translate("tomorrow", lang)
    weekday = translate(f"weekday_{day.weekday()}", lang)
    month = translate(f"month_{day.month}", lang)
    return translate("day_format", lang).format(weekday=weekday, day=day.day, month=month)


def format_time(moment: datetime, tz: tzinfo) -> str:
    """Heure locale du joueur, ex. « 21:00 »."""
    return moment.astimezone(tz).strftime("%H:%M")


def format_date_time(moment: datetime, tz: tzinfo) -> str:
    """Date et heure courtes, ex. « 10/11 21:00 »."""
    return moment.astimezone(tz).strftime("%d/%m %H:%M")
