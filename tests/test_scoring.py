import pytest

from app.services.scoring import PredictionResult, ScoringRules, score_prediction

RULES = ScoringRules()


@pytest.mark.parametrize("pred, real, expected", [
    ((2, 1), (2, 1), PredictionResult(5, True, True)),    # score exact
    ((1, 1), (1, 1), PredictionResult(5, True, True)),    # nul exact
    ((3, 0), (1, 0), PredictionResult(3, False, True)),   # bon vainqueur
    ((0, 2), (1, 4), PredictionResult(3, False, True)),   # bon vainqueur extérieur
    ((0, 0), (2, 2), PredictionResult(3, False, True)),   # bon nul
    ((2, 1), (1, 2), PredictionResult(0, False, False)),  # mauvais vainqueur
    ((1, 1), (1, 0), PredictionResult(0, False, False)),  # nul annoncé, victoire réelle
    ((2, 0), (1, 1), PredictionResult(0, False, False)),  # victoire annoncée, nul réel
    ((9, 7), (9, 7), PredictionResult(5, True, True)),    # gros score exact
])
def test_score_prediction_with_default_rules(pred, real, expected):
    assert score_prediction(*pred, *real, RULES) == expected


def test_score_prediction_uses_custom_rules():
    rules = ScoringRules(winner_points=1, exact_bonus=4)
    assert score_prediction(2, 1, 2, 1, rules).points == 5
    assert score_prediction(3, 1, 2, 1, rules).points == 1
