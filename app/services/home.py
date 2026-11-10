"""Règles pures de la page d'accueil : compétition du moment, résumé de la veille."""
from datetime import UTC, date, datetime, time, timedelta, tzinfo

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


def places_gained(ranks: list[tuple[date, int]], day: date) -> int:
    """Places gagnées (positif) ou perdues (négatif) au classement général le jour `day`.

    `ranks` : (jour, rang) du plus ancien au plus récent (rank_snapshots). 0 si le joueur
    n'a pas de rang ce jour-là ou pas de rang avant.
    """
    rank_that_day = dict(ranks).get(day)
    before = [rank for snapshot_day, rank in ranks if snapshot_day < day]
    if rank_that_day is None or not before:
        return 0
    return before[-1] - rank_that_day


def local_day_bounds(day: date, tz: tzinfo) -> tuple[datetime, datetime]:
    """Début et fin (exclue) d'un jour du fuseau du joueur, en UTC."""
    start = datetime.combine(day, time.min, tzinfo=tz)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def badge_progress(badge, goals: dict[str, int]) -> tuple[int, int]:
    """(fait, objectif) pour la barre de progression du prochain badge : « 2 sur 3 »."""
    goal = goals[badge.key]
    return goal - badge.remaining, goal
