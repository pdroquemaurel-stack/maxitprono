"""Réglages du jeu (barème, taille des ligues) : valeurs par défaut et contrôle de saisie.

Fonctions pures : aucune base. La lecture en base est dans settings_store.py.
"""
from dataclasses import dataclass

from app.services.scoring import ScoringRules

POINTS_RANGE = (0, 20)
LEAGUE_SIZE_RANGE = (2, 1000)


@dataclass(frozen=True)
class Settings:
    winner_points: int = ScoringRules.winner_points
    exact_bonus: int = ScoringRules.exact_bonus
    league_max_members: int = 100

    @property
    def rules(self) -> ScoringRules:
        return ScoringRules(self.winner_points, self.exact_bonus)


def parse_settings(winner_points: str, exact_bonus: str,
                   league_max_members: str) -> tuple[Settings | None, str | None]:
    """Réglages saisis dans le formulaire, ou (None, clé d'erreur)."""
    values = []
    for text, (low, high), error in (
        (winner_points, POINTS_RANGE, "error_points"),
        (exact_bonus, POINTS_RANGE, "error_points"),
        (league_max_members, LEAGUE_SIZE_RANGE, "error_league_size"),
    ):
        text = text.strip()
        if not text.isdigit() or not low <= int(text) <= high:
            return None, error
        values.append(int(text))
    return Settings(*values), None
