from datetime import datetime

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.types import UTCDateTime, utc_now


class GameSettings(Base):
    """Réglages du jeu modifiables dans le back-office : une seule ligne (id = 1)."""

    __tablename__ = "game_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    winner_points: Mapped[int] = mapped_column(Integer)  # bon vainqueur ou bon match nul
    exact_bonus: Mapped[int] = mapped_column(Integer)  # en plus si le score est exact
    league_max_members: Mapped[int] = mapped_column(Integer)
    prediction_days_ahead: Mapped[int] = mapped_column(Integer, default=14, server_default="14")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
