"""Initiales affichées à la place de l'écusson quand l'équipe n'a pas de logo."""
import re

# Mots ignorés : formes juridiques et sigles de clubs, articles
_IGNORED_WORDS = {
    "fc", "cf", "ac", "as", "sc", "afc", "ssc", "rc", "sco", "us", "sv", "fk", "cd", "ud",
    "sd", "rcd", "ca", "club", "de", "du", "des", "la", "le", "les", "of", "the",
}


def team_initials(name: str) -> str:
    """« Paris Saint-Germain » -> « PSG », « Manchester United FC » -> « MU »,
    « Marseille » -> « MAR ». Au plus 3 lettres."""
    words = [w for w in re.split(r"[\s\-.'’]+", name) if w]
    kept = [w for w in words if w.lower() not in _IGNORED_WORDS] or words
    if len(kept) >= 2:
        return "".join(w[0] for w in kept[:3]).upper()
    return kept[0][:3].upper() if kept else "?"
