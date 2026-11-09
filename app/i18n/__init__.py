"""Traductions simples : un fichier JSON par langue, français par défaut.

La langue de la requête en cours (choisie par le joueur, sinon celle du téléphone)
est posée par un middleware (app/main.py) : toutes les fonctions ci-dessous
l'utilisent quand on ne leur en donne pas.
"""
import json
from contextvars import ContextVar
from datetime import date, datetime, tzinfo
from pathlib import Path

from app.config import settings
from app.services.deadlines import closing_info

I18N_DIR = Path(__file__).parent
SUPPORTED_LANGUAGES = ("fr", "en")


def _load(lang: str) -> dict:
    return json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))


TRANSLATIONS = {lang: _load(lang) for lang in SUPPORTED_LANGUAGES}

_current_language: ContextVar[str] = ContextVar("language", default=settings.default_language)


def pick_language(cookie: str | None, accept_language: str | None,
                  default: str = settings.default_language) -> str:
    """Choix du joueur (cookie), sinon langue du téléphone (en-tête Accept-Language), sinon défaut.

    Les navigateurs listent les langues par ordre de préférence : la première connue l'emporte.
    """
    if cookie in SUPPORTED_LANGUAGES:
        return cookie
    for part in (accept_language or "").split(","):
        primary = part.split(";")[0].strip().split("-")[0].lower()
        if primary in SUPPORTED_LANGUAGES:
            return primary
    return default


def set_language(lang: str) -> None:
    _current_language.set(lang if lang in SUPPORTED_LANGUAGES else settings.default_language)


def current_language() -> str:
    return _current_language.get()


def translate(key: str, lang: str | None = None) -> str:
    """Renvoie le texte traduit ; retombe sur le français, puis sur la clé elle-même."""
    lang = lang or current_language()
    return TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS["fr"].get(key) or key


def format_day(day: date, today: date, lang: str | None = None) -> str:
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


def closing_when(kickoff_at: datetime, now: datetime, tz: tzinfo,
                 lang: str | None = None) -> str:
    """Partie « quand » de la clôture : « dans 1 h 42 », « dans 8 min », « demain », « samedi »."""
    info = closing_info(kickoff_at, now, tz)
    if info.kind == "soon" and info.hours:
        return translate("closes_in_hours", lang).format(hours=info.hours, minutes=f"{info.minutes:02d}")
    if info.kind == "soon":
        return translate("closes_in_minutes", lang).format(minutes=info.minutes)
    if info.kind == "tomorrow":
        return translate("tomorrow", lang).lower()
    return translate(f"weekday_{info.day.weekday()}", lang)


def time_ago(moment: datetime, now: datetime, lang: str | None = None) -> str:
    """Il y a combien de temps : « à l'instant », « 12 min », « 2 h », « hier », « 3 j »."""
    minutes = int((now - moment).total_seconds() // 60)
    if minutes < 1:
        return translate("ago_now", lang)
    if minutes < 60:
        return translate("ago_minutes", lang).format(count=minutes)
    if minutes < 24 * 60:
        return translate("ago_hours", lang).format(count=minutes // 60)
    if minutes < 48 * 60:
        return translate("ago_yesterday", lang)
    return translate("ago_days", lang).format(count=minutes // (24 * 60))


def format_rank(rank: int, lang: str | None = None) -> str:
    """Place au classement : « 1er », « 3e » en français ; « 1st », « 3rd » en anglais."""
    if (lang or current_language()) == "en":
        suffix = "th" if 10 <= rank % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
        return f"{rank}{suffix}"
    return "1er" if rank == 1 else f"{rank}e"
