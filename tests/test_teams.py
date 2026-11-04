import pytest

from app.services.teams import team_initials


@pytest.mark.parametrize("name, expected", [
    ("Paris Saint-Germain", "PSG"),
    ("Paris Saint-Germain FC", "PSG"),
    ("Manchester United FC", "MU"),
    ("Real Madrid CF", "RM"),
    ("Marseille", "MAR"),
    ("AS Monaco", "MON"),
    ("Olympique de Marseille", "OM"),
    ("PSG", "PSG"),
    ("Coton Sport", "CS"),
    ("Atlético Madrid", "AM"),
    ("FC", "FC"),
    ("", "?"),
])
def test_team_initials(name, expected):
    assert team_initials(name) == expected
