from app.services.score_colors import score_classes


def test_home_win_is_green_and_red():
    assert score_classes(2, 1) == ("win", "lose")


def test_away_win_is_red_and_green():
    assert score_classes(0, 3) == ("lose", "win")


def test_draw_is_blue_on_both_digits():
    assert score_classes(1, 1) == ("draw", "draw")


def test_incomplete_score_has_no_color():
    assert score_classes(None, 2) == ("", "")
    assert score_classes(None, None) == ("", "")
