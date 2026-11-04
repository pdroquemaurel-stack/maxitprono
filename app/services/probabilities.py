"""Pourcentages 1 / N / 2 affichés sur les cartes de match (SPEC §4).

Source : prédictions du fournisseur si disponibles, sinon tendance des pronostics
des joueurs. Fonctions pures : aucune base, aucun réseau.
"""
from dataclasses import dataclass

MIN_PREDICTIONS_FOR_TRENDS = 5  # en dessous, la tendance n'a pas de sens : rien n'est affiché


@dataclass(frozen=True)
class Probabilities:
    home: int
    draw: int
    away: int
    source: str  # "provider" ou "players"
    count: int = 0  # nombre de pronostics, pour la tendance des joueurs


def round_to_100(values: list[float]) -> list[int]:
    """Entiers proportionnels à `values` dont la somme fait exactement 100.

    Méthode du plus fort reste : on arrondit à l'entier inférieur, puis on
    distribue les points manquants aux plus grandes parties décimales.
    """
    total = sum(values)
    if total <= 0:
        raise ValueError("au moins une valeur positive est nécessaire")
    exact = [100 * v / total for v in values]
    result = [int(x) for x in exact]
    by_remainder = sorted(range(len(values)), key=lambda i: exact[i] - result[i], reverse=True)
    for i in by_remainder[:100 - sum(result)]:
        result[i] += 1
    return result


def player_trends(scores: list[tuple[int, int]]) -> Probabilities | None:
    """Part des pronostics victoire domicile / nul / victoire extérieur."""
    if len(scores) < MIN_PREDICTIONS_FOR_TRENDS:
        return None
    home = sum(1 for h, a in scores if h > a)
    draw = sum(1 for h, a in scores if h == a)
    away = len(scores) - home - draw
    values = round_to_100([home, draw, away])
    return Probabilities(*values, source="players", count=len(scores))


def match_probabilities(prob_home: int | None, prob_draw: int | None, prob_away: int | None,
                        scores: list[tuple[int, int]]) -> Probabilities | None:
    """Pourcentages du fournisseur s'ils sont en base, sinon tendance des joueurs."""
    if None not in (prob_home, prob_draw, prob_away):
        return Probabilities(prob_home, prob_draw, prob_away, source="provider")
    return player_trends(scores)
