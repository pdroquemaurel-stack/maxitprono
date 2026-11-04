from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.types import UTCDateTime, utc_now
from app.models.user import User


class League(Base):
    """Ligue privée entre amis ; son créateur en est l'admin (et un membre)."""

    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    code: Mapped[str] = mapped_column(String(6), unique=True)  # code d'invitation, ex. K7PM4X
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    owner: Mapped[User] = relationship()


class LeagueMember(Base):
    __tablename__ = "league_members"
    __table_args__ = (UniqueConstraint("league_id", "user_id",
                                       name="uq_league_members_league_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Le classement de la ligue ne compte que les matchs commencés après cette date
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    league: Mapped[League] = relationship()
    user: Mapped[User] = relationship()
