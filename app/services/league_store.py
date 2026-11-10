"""Lectures et écritures des ligues en base ; les règles sont dans leagues.py."""
from dataclasses import dataclass
from datetime import UTC, datetime, time

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (Competition, League, LeagueCompetition, LeagueMember, Match, MatchStatus,
                        Prediction, User)
from app.services.activity import ACTIVITY_WINDOW, Event, exact_event, join_event, latest_events
from app.services.deadlines import CLOSING_DELAY, OPEN_STATUSES
from app.services.leaderboards import league_competition_filter, leaderboard
from app.services.leagues import (clean_color, clean_name, create_error, generate_code,
                                  invite_from_next, join_error, leave_error, normalize_code,
                                  rank_moves,
                                  remove_error, valid_inviter, validate_league_name)
from app.services.ranking import PlayerScore, week_bounds, week_start
from app.services.settings_store import league_max_members

EPOCH = datetime(2000, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Result:
    league: League | None = None
    error: str | None = None


@dataclass(frozen=True)
class Member:
    """Ce qu'il faut pour afficher un membre (sans charger sa photo)."""
    user_id: int
    nickname: str
    has_photo: bool


# --- Lectures ---

def find_by_code(db: Session, code: str) -> League | None:
    return db.scalar(select(League).where(League.code == normalize_code(code)))


def membership(db: Session, league_id: int, user_id: int) -> LeagueMember | None:
    return db.scalar(select(LeagueMember).where(LeagueMember.league_id == league_id,
                                                LeagueMember.user_id == user_id))


def member_count(db: Session, league_id: int) -> int:
    return db.scalar(select(func.count()).select_from(LeagueMember)
                     .where(LeagueMember.league_id == league_id))


def player_league_count(db: Session, user_id: int) -> int:
    return db.scalar(select(func.count()).select_from(LeagueMember)
                     .where(LeagueMember.user_id == user_id))


def my_leagues(db: Session, user_id: int) -> list[tuple[League, int]]:
    """Ligues du joueur avec leur nombre de membres, la plus récemment rejointe d'abord."""
    counts = (select(LeagueMember.league_id, func.count().label("members"))
              .group_by(LeagueMember.league_id).subquery())
    query = (select(League, counts.c.members)
             .join(LeagueMember, LeagueMember.league_id == League.id)
             .join(counts, counts.c.league_id == League.id)
             .where(LeagueMember.user_id == user_id)
             .order_by(LeagueMember.joined_at.desc(), League.id.desc()))
    return [(league, members) for league, members in db.execute(query)]


def members(db: Session, league_id: int) -> list[LeagueMember]:
    """Membres par date d'arrivée (l'admin en premier)."""
    query = (select(LeagueMember).join(LeagueMember.user)
             .where(LeagueMember.league_id == league_id)
             .order_by(LeagueMember.joined_at, LeagueMember.id))
    return list(db.scalars(query))


def member_cards(db: Session, league_id: int) -> list[Member]:
    """Membres par date d'arrivée, avec seulement pseudo et présence d'une photo."""
    query = (select(User.id, User.nickname, User.avatar_mime)
             .join(LeagueMember, LeagueMember.user_id == User.id)
             .where(LeagueMember.league_id == league_id)
             .order_by(LeagueMember.joined_at, LeagueMember.id))
    return [Member(user_id, nickname, bool(mime)) for user_id, nickname, mime in db.execute(query)]


def competitions_of(db: Session, league_id: int) -> list[Competition]:
    """Compétitions choisies par la ligue ; liste vide = toutes."""
    query = (select(Competition).join(LeagueCompetition,
                                      LeagueCompetition.competition_id == Competition.id)
             .where(LeagueCompetition.league_id == league_id).order_by(Competition.name))
    return list(db.scalars(query))


def active_competitions(db: Session) -> list[Competition]:
    """Compétitions proposées à la création d'une ligue."""
    return list(db.scalars(select(Competition).where(Competition.is_active.is_(True))
                           .order_by(Competition.name)))


def last_scored_kickoff(db: Session, league_id: int) -> datetime | None:
    """Coup d'envoi du dernier match compté pour la ligue (sa « dernière journée »)."""
    return db.scalar(select(func.max(Match.kickoff_at))
                     .join(Prediction, Prediction.match_id == Match.id)
                     .join(LeagueMember, LeagueMember.user_id == Prediction.user_id)
                     .where(LeagueMember.league_id == league_id,
                            Prediction.points.is_not(None),
                            Match.kickoff_at >= LeagueMember.joined_at,
                            league_competition_filter(league_id)))


def standing_with_moves(db: Session, league_id: int) -> tuple[list[PlayerScore], dict]:
    """Classement de la ligue et places gagnées depuis la veille de la dernière journée."""
    ranking = leaderboard(db, league_id=league_id)
    last = last_scored_kickoff(db, league_id)
    if last is None:
        return ranking, {}
    day_start = datetime.combine(last.date(), time.min, tzinfo=UTC)
    before = leaderboard(db, league_id=league_id, period=(EPOCH, day_start))
    return ranking, rank_moves(before, ranking)


def last_week_ranking(db: Session, league_id: int) -> list[PlayerScore]:
    """Classement de la ligue sur la semaine (lundi-dimanche) de la dernière journée."""
    last = last_scored_kickoff(db, league_id)
    if last is None:
        return []
    return leaderboard(db, league_id=league_id, period=week_bounds(week_start(last.date())))


def next_open_match(db: Session, league_id: int, now: datetime) -> Match | None:
    """Prochain match encore ouvert aux pronos dans les compétitions de la ligue."""
    query = (select(Match).join(Match.competition).options(joinedload(Match.competition))
             .where(Competition.is_active.is_(True), Match.status.in_(OPEN_STATUSES),
                    Match.kickoff_at > now + CLOSING_DELAY, league_competition_filter(league_id))
             .order_by(Match.kickoff_at).limit(1))
    return db.scalar(query)


def match_players(db: Session, league_id: int, match_id: int) -> list[tuple[int, int, int]]:
    """(user_id, buts domicile, buts extérieur) des membres qui ont pronostiqué ce match.

    Sert à la tendance V/N/D et à « qui a joué » : les scores ne sortent pas du serveur
    avant le coup d'envoi.
    """
    query = (select(Prediction.user_id, Prediction.home_score, Prediction.away_score)
             .join(LeagueMember, LeagueMember.user_id == Prediction.user_id)
             .where(LeagueMember.league_id == league_id, Prediction.match_id == match_id))
    return [tuple(row) for row in db.execute(query)]


def finished_matches(db: Session, league_id: int, limit: int = 10) -> list[Match]:
    """Derniers matchs terminés (avec score) des compétitions de la ligue, du plus récent."""
    query = (select(Match).options(joinedload(Match.competition))
             .where(Match.status == MatchStatus.FINISHED, Match.home_score.is_not(None),
                    league_competition_filter(league_id))
             .order_by(Match.kickoff_at.desc()).limit(limit))
    return list(db.scalars(query))


def match_predictions(db: Session, league_id: int, match_id: int) -> list[tuple]:
    """(user_id, pseudo, pronostic ou None) de chaque membre de la ligue sur ce match."""
    query = (select(User.id, User.nickname, Prediction)
             .join(LeagueMember, LeagueMember.user_id == User.id)
             .outerjoin(Prediction, (Prediction.user_id == User.id)
                        & (Prediction.match_id == match_id))
             .where(LeagueMember.league_id == league_id))
    return [tuple(row) for row in db.execute(query)]


def recent_activity(db: Session, league: League, now: datetime) -> list[Event]:
    """Arrivées et scores exacts des membres sur les 7 derniers jours.

    Comme pour le classement de la ligue, seuls comptent les matchs commencés
    après l'arrivée du joueur.
    """
    since = now - ACTIVITY_WINDOW
    joins = db.execute(select(User.id, User.nickname, LeagueMember.joined_at)
                       .join(LeagueMember, LeagueMember.user_id == User.id)
                       .where(LeagueMember.league_id == league.id,
                              LeagueMember.joined_at >= since))
    exacts = db.execute(select(User.nickname, Match.home_team, Match.away_team, Match.kickoff_at)
                        .join(Prediction, Prediction.user_id == User.id)
                        .join(Match, Prediction.match_id == Match.id)
                        .join(LeagueMember, LeagueMember.user_id == User.id)
                        .where(LeagueMember.league_id == league.id,
                               Prediction.is_exact, Prediction.points.is_not(None),
                               Match.kickoff_at >= LeagueMember.joined_at,
                               Match.kickoff_at >= since,
                               league_competition_filter(league.id)))
    events = [join_event(nickname, at, user_id == league.owner_id) for user_id, nickname, at in joins]
    events += [exact_event(*row) for row in exacts]
    return latest_events(events, now)


# --- Écritures ---

def create_league(db: Session, owner: User, name: str, now: datetime, color: str = "",
                  competition_ids: list[int] = ()) -> Result:
    """`competition_ids` vide : la ligue compte toutes les compétitions."""
    error = validate_league_name(name) or create_error(player_league_count(db, owner.id))
    if error:
        return Result(error=error)
    league = League(name=clean_name(name), code=_unused_code(db), owner_id=owner.id,
                    created_at=now, color=clean_color(color))
    db.add(league)
    db.flush()
    db.add(LeagueMember(league_id=league.id, user_id=owner.id, joined_at=now))
    _set_competitions(db, league.id, competition_ids)
    db.commit()
    return Result(league=league)


def update_league(db: Session, league: League, user: User, name: str, color: str,
                  competition_ids: list[int]) -> str | None:
    """Réglages modifiables par l'admin de la ligue : nom, couleur, compétitions."""
    if league.owner_id != user.id:
        return "error_not_league_owner"
    error = validate_league_name(name, current_name=league.name)
    if error:
        return error
    league.name, league.color = clean_name(name), clean_color(color)
    _set_competitions(db, league.id, competition_ids)
    db.commit()
    return None


def join_league(db: Session, league: League, user: User, now: datetime,
                ref: str | None = None) -> Result:
    """`ref` : identifiant du membre qui a partagé le lien d'invitation, s'il y en a un."""
    error = join_error(membership(db, league.id, user.id) is not None,
                       member_count(db, league.id), player_league_count(db, user.id),
                       league_max_members(db))
    if error:
        return Result(league=league, error=error)
    member_ids = list(db.scalars(select(LeagueMember.user_id)
                                 .where(LeagueMember.league_id == league.id)))
    db.add(LeagueMember(league_id=league.id, user_id=user.id, joined_at=now,
                        invited_by_id=valid_inviter(ref, member_ids, user.id)))
    db.commit()
    return Result(league=league)


def join_from_invite(db: Session, user: User, next_url: str, now: datetime) -> str | None:
    """Après connexion ou inscription depuis un lien d'invitation : rejoint la ligue et
    renvoie l'adresse de la ligue. None si `next_url` n'est pas une invitation valable ou
    si le joueur ne peut pas entrer (ligue pleine…) : la page d'invitation expliquera."""
    invite = invite_from_next(next_url)
    league = find_by_code(db, invite[0]) if invite else None
    if league is None:
        return None
    result = join_league(db, league, user, now, invite[1])
    if result.error == "error_already_member":
        return f"/leagues/{league.id}"
    return None if result.error else f"/leagues/{league.id}?joined=1"


def leave_league(db: Session, league: League, user: User) -> str | None:
    error = leave_error(league.owner_id == user.id)
    if error is None:
        _delete_membership(db, league.id, user.id)
    return error


def remove_member(db: Session, league: League, owner: User, user_id: int) -> str | None:
    error = remove_error(league.owner_id == owner.id, league.owner_id == user_id)
    if error is None:
        _delete_membership(db, league.id, user_id)
    return error


def delete_league(db: Session, league: League, user: User) -> str | None:
    if league.owner_id != user.id:
        return "error_not_league_owner"
    db.execute(delete(LeagueMember).where(LeagueMember.league_id == league.id))
    db.execute(delete(LeagueCompetition).where(LeagueCompetition.league_id == league.id))
    db.delete(league)
    db.commit()
    return None


def _delete_membership(db: Session, league_id: int, user_id: int) -> None:
    db.execute(delete(LeagueMember).where(LeagueMember.league_id == league_id,
                                          LeagueMember.user_id == user_id))
    db.commit()


def _set_competitions(db: Session, league_id: int, competition_ids: list[int]) -> None:
    db.execute(delete(LeagueCompetition).where(LeagueCompetition.league_id == league_id))
    db.add_all(LeagueCompetition(league_id=league_id, competition_id=competition_id)
               for competition_id in competition_ids)


def _unused_code(db: Session) -> str:
    """Code pas encore pris (31^6 ≈ 900 millions de codes : les collisions sont rares)."""
    while True:
        code = generate_code()
        if find_by_code(db, code) is None:
            return code
