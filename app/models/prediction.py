from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.match import Match
from app.models.types import UTCDateTime, utc_now


class Prediction(Base):
    """Pronostic de score exact d'un joueur sur un match (un seul par match)."""

    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("user_id", "match_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)
    home_score: Mapped[int] = mapped_column(Integer)
    away_score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    # Résultat, rempli quand le match est terminé. points vide = non compté (match annulé)
    points: Mapped[int | None] = mapped_column(Integer)
    is_exact: Mapped[bool] = mapped_column(Boolean, default=False)  # départage n°2
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)  # départage n°3
    scored_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    match: Mapped[Match] = relationship()
