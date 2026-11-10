"""Règles pures de la page d'accueil : compétition du moment, résumé de la veille."""
from datetime import datetime, timedelta

FEATURED_WINDOW = timedelta(days=7)


def featured_competition(matches: list, now: datetime):
    """Compétition « du moment » : celle qui a le plus de matchs dans les 7 prochains jours.

    `matches` : objets avec `.competition` et `.kickoff_at`, triés par coup d'envoi.
    À égalité, celle dont le prochain match arrive en premier. None s'il n'y a aucun match.
    """
    counts: dict[int, int] = {}
    first_seen: dict[int, object] = {}
    for match in matches:
        if now <= match.kickoff_at <= now + FEATURED_WINDOW:
            counts[match.competition.id] = counts.get(match.competition.id, 0) + 1
            first_seen.setdefault(match.competition.id, match.competition)
    if not counts:
        return None
    order = list(first_seen)  # ordre d'apparition = ordre des coups d'envoi
    best = max(order, key=lambda cid: (counts[cid], -order.index(cid)))
    return first_seen[best]
