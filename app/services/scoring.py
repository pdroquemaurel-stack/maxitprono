"""Calcul des points d'un pronostic.

Fonctions pures : aucune base de données.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoringRules:
    """Barème (modifiable plus tard par l'admin dans le back-office)."""

    winner_points: int = 3  # bon vainqueur ou bon match nul
    exact_bonus: int = 2  # en plus si le score est exact


@dataclass(frozen=True)
class PredictionResult:
    points: int
    is_exact: bool
    is_winner: bool  # bon vainqueur ou bon nul ; vrai aussi quand le score est exact


def _outcome(home: int, away: int) -> int:
    """1 si l'équipe à domicile gagne, 0 pour un nul, -1 si l'équipe à l'extérieur gagne."""
    return (home > away) - (home < away)


def score_prediction(pred_home: int, pred_away: int, real_home: int, real_away: int,
                     rules: ScoringRules) -> PredictionResult:
    is_exact = (pred_home, pred_away) == (real_home, real_away)
    is_winner = _outcome(pred_home, pred_away) == _outcome(real_home, real_away)
    points = 0
    if is_winner:
        points += rules.winner_points
    if is_exact:
        points += rules.exact_bonus
    return PredictionResult(points, is_exact, is_winner)
