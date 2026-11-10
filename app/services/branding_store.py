"""Lecture et écriture de la personnalisation (table branding, une seule ligne), avec un petit cache.

Le nom et les couleurs servent sur toutes les pages : on ne relit la base qu'au plus une fois
par minute (CACHE_SECONDS). L'enregistrement met le cache à jour tout de suite ; s'il y a
plusieurs processus serveur, les autres suivent au plus tard une minute après.
"""
import time
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BrandingChange, BrandingRow, User
from app.services.branding import FIELDS, Branding, changed_fields

BRANDING_ID = 1
CACHE_SECONDS = 60
HISTORY_SIZE = 20

_cache: dict = {"branding": None, "loaded_at": 0.0}


def current_branding() -> Branding:
    """Réglages du cache (sans base) : utilisé par les templates et les traductions."""
    return _cache["branding"] or Branding()


def refresh_branding(db: Session) -> Branding:
    """Relit la base si le cache est vide ou trop vieux (appelé au début de chaque requête)."""
    if _cache["branding"] is None or time.monotonic() - _cache["loaded_at"] > CACHE_SECONDS:
        _remember(load_branding(db))
    return _cache["branding"]


def clear_cache() -> None:
    _cache.update(branding=None, loaded_at=0.0)


def _remember(branding: Branding) -> None:
    _cache.update(branding=branding, loaded_at=time.monotonic())


def load_branding(db: Session) -> Branding:
    """Réglages en base, ou valeurs par défaut tant que l'admin n'a rien enregistré."""
    row = db.get(BrandingRow, BRANDING_ID)
    if row is None:
        return Branding()
    return Branding(**{name: getattr(row, name) for name in FIELDS})


def save_branding(db: Session, branding: Branding, user_id: int, now: datetime) -> int:
    """Enregistre les réglages et une ligne d'historique par champ modifié.

    Renvoie le nombre de champs modifiés.
    """
    changes = changed_fields(load_branding(db), branding)
    row = db.get(BrandingRow, BRANDING_ID) or BrandingRow(id=BRANDING_ID)
    for name in FIELDS:
        setattr(row, name, getattr(branding, name))
    row.updated_at = now
    db.add(row)
    db.add_all(BrandingChange(user_id=user_id, field=field, old_value=old, new_value=new,
                              changed_at=now) for field, old, new in changes)
    db.commit()
    _remember(branding)
    return len(changes)


def recent_changes(db: Session) -> list[tuple[BrandingChange, str]]:
    """Dernières modifications, les plus récentes d'abord, avec le pseudo de l'admin."""
    query = (select(BrandingChange, User.nickname)
             .outerjoin(User, User.id == BrandingChange.user_id)
             .order_by(BrandingChange.changed_at.desc(), BrandingChange.id.desc())
             .limit(HISTORY_SIZE))
    return [(change, nickname or "?") for change, nickname in db.execute(query)]
