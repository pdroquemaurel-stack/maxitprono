"""Code couleur des chiffres d'un score (charte : gagnant vert, perdant rouge, nul bleu).

Fonction pure. Le même calcul existe en JavaScript (static/js/score-colors.js)
pour recolorer les cases pendant la saisie.
"""


def score_classes(home: int | None, away: int | None) -> tuple[str, str]:
    """Classes CSS des deux chiffres : ("win", "lose"), ("draw", "draw")... ou ("", "") si incomplet."""
    if home is None or away is None:
        return "", ""
    if home > away:
        return "win", "lose"
    if home < away:
        return "lose", "win"
    return "draw", "draw"
