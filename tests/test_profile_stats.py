"""Calculs de la page Profil (fonctions pures)."""
from datetime import UTC, date, datetime, timedelta

from app.services import profile_stats as stats
from app.services.profile_stats import PlayedPick
from app.services.ranking import PlayerScore

START = datetime(2026, 11, 1, 20, 0, tzinfo=UTC)


def pick(pred, real, day=0, competition="Ligue 1", points=0):
    return PlayedPick(pred[0], pred[1], real[0], real[1], START + timedelta(days=day),
                      competition, points=points)


EXACT, GOOD, MISS = pick((2, 1), (2, 1)), pick((1, 0), (3, 1)), pick((0, 0), (1, 0))


def test_outcomes():
    assert stats.pick_outcome(EXACT) == "exact"
    assert stats.pick_outcome(GOOD) == "good"
    assert stats.pick_outcome(pick((1, 1), (2, 2))) == "good"  # bon match nul
    assert stats.pick_outcome(MISS) == "miss"


def test_summary_without_predictions():
    summary = stats.summarize([])
    assert (summary.played, summary.success_rate, summary.points) == (0, 0, 0)
    assert (summary.exact_pct, summary.good_pct, summary.miss_pct) == (0, 0, 0)
    assert summary.average_points == 0


def test_summary_counts_and_rounded_rate():
    summary = stats.summarize([EXACT, GOOD, MISS])
    assert (summary.played, summary.exacts, summary.goods, summary.misses) == (3, 1, 1, 1)
    assert summary.success_rate == 67  # 2 / 3 arrondi
    # La répartition fait 100 et colle au taux de réussite
    assert summary.exact_pct + summary.good_pct == 67 and summary.miss_pct == 33


def test_percent_rounds_half_up():
    assert stats.percent(1, 8) == 13  # 12,5 -> 13
    assert stats.percent(0, 0) == 0


def test_points_and_average():
    summary = stats.summarize([pick((2, 1), (2, 1), points=5), pick((1, 0), (2, 0), points=3)])
    assert summary.points == 8 and summary.average_points == 4.0


def test_form_and_streaks_in_kickoff_order():
    picks = [pick((0, 0), (1, 0), day=0), pick((1, 0), (1, 0), day=1), pick((2, 0), (1, 0), day=2),
             pick((0, 3), (0, 1), day=3), pick((0, 0), (2, 0), day=4), pick((1, 1), (0, 0), day=5)]
    outcomes = stats.chronological_outcomes(list(reversed(picks)))
    assert outcomes == ["miss", "exact", "good", "good", "miss", "good"]
    assert stats.current_streak(outcomes) == 1
    assert stats.best_streak(outcomes) == 3
    assert stats.recent_form(outcomes, size=4) == ["good", "good", "miss", "good"]


def test_by_competition_and_strongest():
    picks = ([pick((1, 0), (1, 0), competition="Ligue des champions")] * 5
             + [pick((1, 0), (0, 1), competition="Ligue 1")] * 6
             + [pick((1, 0), (1, 0), competition="Liga")])
    competition_stats = stats.by_competition(picks)
    assert [(s.name, s.played, s.success_rate) for s in competition_stats] == [
        ("Ligue 1", 6, 0), ("Ligue des champions", 5, 100), ("Liga", 1, 100)]
    # Liga a 100 % mais moins de 5 pronos
    assert stats.strongest_competition(competition_stats).name == "Ligue des champions"
    assert stats.strongest_competition([]) is None


def test_best_climb():
    d1, d2, d3, d4 = (date(2026, 11, day) for day in (1, 2, 3, 4))
    ranks = [(d1, 9), (d2, 3), (d3, 4), (d4, 1)]
    assert stats.best_climb(ranks, {d1, d2, d3, d4}) == 6  # 9e -> 3e
    assert stats.best_climb(ranks, {d4}) == 3  # seules comptent les journées jouées
    assert stats.best_climb([(d1, 5)], {d1}) == 0  # pas classé avant
    assert stats.best_climb([], set()) == 0


def test_badges_and_next_badge():
    badges = stats.compute_badges(exacts=3, best_climb=2, invited_friends=0, best_success_streak=4)
    assert {b.key: b.unlocked for b in badges} == {
        "prophet": True, "remontada": False, "gatherer": False, "flawless": False}
    upcoming = stats.next_badge(badges)
    assert (upcoming.key, upcoming.remaining) == ("gatherer", 1)
    all_done = stats.compute_badges(exacts=9, best_climb=9, invited_friends=3, best_success_streak=9)
    assert stats.next_badge(all_done) is None


def test_choose_competition():
    competitions = [(1, "Ligue 1"), (2, "UEFA Champions League")]
    assert stats.choose_competition(competitions, "1") == 1
    assert stats.choose_competition(competitions, "99") == 2  # Ligue des champions par défaut
    assert stats.choose_competition([(1, "Ligue 1")], None) == 1
    assert stats.choose_competition([], None) is None


def test_rank_change():
    fifth, third = (PlayerScore(1, "a", "CM", START, 0, 0, 0, rank=rank) for rank in (5, 3))
    assert stats.rank_change(fifth, third) == 2  # 2 places gagnées
    assert stats.rank_change(third, fifth) == -2
    assert stats.rank_change(None, third) is None


def test_single_matchday():
    def on(matchday, competition="Ligue 1"):
        return PlayedPick(1, 0, 1, 0, START, competition, matchday=matchday)
    assert stats.single_matchday([on(12), on(12)]) == 12
    assert stats.single_matchday([on(12), on(4, "Ligue des champions")]) is None
    assert stats.single_matchday([on(12), on(None)]) is None
    assert stats.single_matchday([]) is None


def test_stable_competition_rows_keep_career_order_with_period_values():
    from app.services.profile_stats import CompetitionStat, stable_competition_rows
    career = [CompetitionStat("Ligue 1", 9, 50), CompetitionStat("CAN", 4, 75)]
    period = [CompetitionStat("CAN", 2, 100)]
    assert stable_competition_rows(period, career) == [CompetitionStat("Ligue 1", 0, 0),
                                                       CompetitionStat("CAN", 2, 100)]
    assert stable_competition_rows([], []) == []
