"""Déclenchement des synchronisations par la GitHub Action (.github/workflows/sync.yml).

POST /internal/sync?task=fixtures : import des matchs de J-3 à J+14 et des pourcentages
                                    1 / N / 2 du fournisseur (1 fois par jour)
POST /internal/sync?task=scores   : mise à jour des matchs en cours (toutes les 10 min),
                                    sans aucun appel API s'il n'y en a pas
Les points des matchs terminés sont calculés après chaque synchronisation.
Protégée par l'en-tête « Authorization: Bearer <SYNC_TOKEN> ».
"""
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.jobs.sync import run_sync
from app.models.types import utc_now
from app.providers import make_provider

router = APIRouter()


def get_provider_factory():
    """Dépendance remplaçable dans les tests : fabrique du fournisseur."""
    return make_provider


def check_token(authorization: str) -> None:
    expected = config.settings.sync_token
    if not expected:
        raise HTTPException(503, "Synchronisation désactivée : SYNC_TOKEN non défini")
    if not secrets.compare_digest(authorization.encode(), f"Bearer {expected}".encode()):
        raise HTTPException(401, "Jeton invalide")


@router.post("/internal/sync")
def sync(task: Literal["fixtures", "scores"], authorization: str = Header(""),
         db: Session = Depends(get_db), provider_factory=Depends(get_provider_factory)):
    check_token(authorization)
    result = {"task": task, "provider": config.settings.data_provider,
              **run_sync(db, provider_factory, task, utc_now())}
    if "error" in result:
        return JSONResponse(result, status_code=502)
    return result
