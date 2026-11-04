"""Classement des joueurs et départage.

Fonctions pures : aucune base de données.
"""
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta


@dataclass(frozen=True)
class PlayerScore:
    user_id: int
    nickname: str
    country_code: str
    created_at: datetime  # date d'inscription
    points: int
    exacts: int  # nombre de scores exacts
    winners: int  # nombre de bons vainqueurs (scores exacts compris)
    rank: int = 0


def _ranking_key(player: PlayerScore) -> tuple:
    """Départage : 1) points, 2) scores exacts, 3) bons vainqueurs, 4) inscription la plus ancienne."""
    return (-player.points, -player.exacts, -player.winners, player.created_at, player.user_id)


def rank_players(players: list[PlayerScore]) -> list[PlayerScore]:
    """Trie les joueurs et leur donne un rang (1, 2, 3...).

    La date d'inscription départage toujours : deux joueurs n'ont jamais le même rang.
    """
    ordered = sorted(players, key=_ranking_key)
    return [replace(player, rank=position) for position, player in enumerate(ordered, start=1)]


def find_player(ranking: list[PlayerScore], user_id: int) -> PlayerScore | None:
    return next((player for player in ranking if player.user_id == user_id), None)


# --- Semaines (du lundi au dimanche, selon l'heure UTC du coup d'envoi) ---

def week_start(day: date) -> date:
    """Lundi de la semaine qui contient ce jour."""
    return day - timedelta(days=day.weekday())


def week_bounds(monday: date) -> tuple[datetime, datetime]:
    """Début (inclus) et fin (exclue) de la semaine, en UTC."""
    start = datetime.combine(monday, time.min, tzinfo=UTC)
    return start, start + timedelta(days=7)
