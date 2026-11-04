"""Lectures et écritures des ligues en base ; les règles sont dans leagues.py."""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import League, LeagueMember, User
from app.services.leagues import (clean_name, create_error, generate_code, join_error,
                                  leave_error, normalize_code, remove_error, validate_league_name)


@dataclass(frozen=True)
class Result:
    league: League | None = None
    error: str | None = None


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


# --- Écritures ---

def create_league(db: Session, owner: User, name: str, now: datetime) -> Result:
    error = validate_league_name(name) or create_error(player_league_count(db, owner.id))
    if error:
        return Result(error=error)
    league = League(name=clean_name(name), code=_unused_code(db), owner_id=owner.id,
                    created_at=now)
    db.add(league)
    db.flush()
    db.add(LeagueMember(league_id=league.id, user_id=owner.id, joined_at=now))
    db.commit()
    return Result(league=league)


def join_league(db: Session, league: League, user: User, now: datetime) -> Result:
    error = join_error(membership(db, league.id, user.id) is not None,
                       member_count(db, league.id), player_league_count(db, user.id))
    if error:
        return Result(league=league, error=error)
    db.add(LeagueMember(league_id=league.id, user_id=user.id, joined_at=now))
    db.commit()
    return Result(league=league)


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
    db.delete(league)
    db.commit()
    return None


def _delete_membership(db: Session, league_id: int, user_id: int) -> None:
    db.execute(delete(LeagueMember).where(LeagueMember.league_id == league_id,
                                          LeagueMember.user_id == user_id))
    db.commit()


def _unused_code(db: Session) -> str:
    """Code pas encore pris (31^6 ≈ 900 millions de codes : les collisions sont rares)."""
    while True:
        code = generate_code()
        if find_by_code(db, code) is None:
            return code
