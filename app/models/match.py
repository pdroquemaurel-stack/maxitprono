from datetime import datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
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
    __table_args__ = (UniqueConstraint("provider", "external_id",
                                       name="uq_matches_provider_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Fournisseur et identifiant chez lui : vides si le match est ajouté à la main ou de démo
    provider: Mapped[str | None] = mapped_column(String(20))
    external_id: Mapped[str | None] = mapped_column(String(40))
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
