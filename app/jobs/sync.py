"""Synchronisation complète, partagée par la GitHub Action (/internal/sync),
les boutons du back-office et scripts/run_import.py.

  fixtures : matchs de J-3 à J+14 (ou plus, selon le réglage admin) + pourcentages 1 / N / 2
  scores   : mise à jour des matchs en cours, sans aucun appel API s'il n'y en a pas
Les points des matchs terminés sont calculés après chaque synchronisation, même en échec.
"""
import logging
from datetime import datetime
from typing import Callable, Literal

from sqlalchemy.orm import Session

from app.jobs.import_matches import import_upcoming_matches, update_live_scores
from app.jobs.import_probabilities import import_probabilities
from app.jobs.score_predictions import score_finished_matches
from app.providers.base import FootballProvider, ProviderError
from app.services.settings_store import current_rules, prediction_days_ahead

Task = Literal["fixtures", "scores"]
logger = logging.getLogger(__name__)


def run_sync(db: Session, provider_factory: Callable[[Session], FootballProvider],
             task: Task, now: datetime) -> dict:
    """Lance la tâche et renvoie le résumé ; la clé « error » n'existe qu'en cas d'échec."""
    result = {"matches": 0}
    try:
        provider = provider_factory(db)
        if task == "fixtures":
            result["matches"] = import_upcoming_matches(db, provider, now.date(),
                                                        prediction_days_ahead(db))
            result["probabilities"] = import_probabilities(db, provider, now)
        else:
            result["matches"] = update_live_scores(db, provider, now)
    except ProviderError as exc:
        db.rollback()
        result["error"] = str(exc)
        logger.warning("Synchronisation %s en échec : %s", task, exc)
    result["predictions_scored"] = score_finished_matches(db, current_rules(db), now)
    return result
