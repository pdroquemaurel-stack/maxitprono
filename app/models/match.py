from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.competition import Competition
from app.models.types import UTCDateTime


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"  # le pronostic reste valable
    CANCELLED = "cancelled"  # le pronostic est annulé


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_id: Mapped[int | None] = mapped_column(Integer, unique=True)  # vide si ajouté à la main
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), index=True)
    season: Mapped[int | None] = mapped_column(Integer)  # saison API, vide si ajouté à la main
    home_team: Mapped[str] = mapped_column(String(120))
    away_team: Mapped[str] = mapped_column(String(120))
    home_logo_url: Mapped[str] = mapped_column(String(255), default="")
    away_logo_url: Mapped[str] = mapped_column(String(255), default="")
    kickoff_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)  # en UTC
    status: Mapped[str] = mapped_column(String(20), default=MatchStatus.SCHEDULED)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    synced_at: Mapped[datetime | None] = mapped_column(UTCDateTime)  # dernière mise à jour API

    competition: Mapped[Competition] = relationship()
