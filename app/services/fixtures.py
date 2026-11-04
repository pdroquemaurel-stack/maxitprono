"""Choix des matchs dont il faut mettre à jour le score.

Fonctions pures : aucune base, aucun réseau. La conversion des réponses des
fournisseurs est dans app/providers/.
"""
from datetime import datetime, timedelta

from app.models.match import MatchStatus

# Au-delà, un match commencé est considéré comme terminé côté mise à jour
LIVE_WINDOW = timedelta(hours=3)


def needs_score_update(status: str, kickoff_at: datetime, now: datetime) -> bool:
    """Vrai si le match est en cours ou vient de commencer sans être terminé."""
    if status == MatchStatus.LIVE:
        return True
    return status == MatchStatus.SCHEDULED and kickoff_at <= now <= kickoff_at + LIVE_WINDOW
