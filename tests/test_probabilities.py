import pytest

from app.services.probabilities import (MIN_PREDICTIONS_FOR_TRENDS, Probabilities,
                                        match_probabilities, player_trends, round_to_100)


@pytest.mark.parametrize("values, expected", [
    ([1, 1, 1], [34, 33, 33]),
    ([45, 30, 25], [45, 30, 25]),
    ([2, 1, 0], [67, 33, 0]),
    ([0.455, 0.301, 0.244], [46, 30, 24]),
    ([1, 0, 0], [100, 0, 0]),
])
def test_round_to_100(values, expected):
    assert round_to_100(values) == expected
    assert sum(round_to_100(values)) == 100


def test_round_to_100_refuses_all_zero():
    with pytest.raises(ValueError):
        round_to_100([0, 0, 0])


def test_trends_count_home_draw_away():
    scores = [(2, 1), (1, 0), (3, 1), (1, 1), (0, 2), (2, 0)]  # 4 domicile, 1 nul, 1 extérieur
    assert player_trends(scores) == Probabilities(67, 17, 16, source="players", count=6)


def test_trends_hidden_below_threshold():
    scores = [(1, 0)] * (MIN_PREDICTIONS_FOR_TRENDS - 1)
    assert player_trends(scores) is None


def test_trends_shown_from_threshold():
    scores = [(0, 0)] * MIN_PREDICTIONS_FOR_TRENDS
    assert player_trends(scores) == Probabilities(0, 100, 0, source="players", count=5)


def test_provider_probabilities_come_first():
    result = match_probabilities(55, 26, 19, [(0, 1)] * 10)
    assert result == Probabilities(55, 26, 19, source="provider")


def test_trends_used_without_provider_probabilities():
    assert match_probabilities(None, None, None, [(0, 1)] * 5).source == "players"


def test_nothing_without_provider_or_enough_predictions():
    assert match_probabilities(None, None, None, [(0, 1)]) is None
