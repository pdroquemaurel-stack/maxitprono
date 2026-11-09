from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RankSnapshot(Base):
    """Rang d'un joueur au classement général à la fin d'une journée de matchs (jour UTC).

    Recalculé par app/services/rank_history.py à chaque calcul des points.
    """

    __tablename__ = "rank_snapshots"
    __table_args__ = (UniqueConstraint("day", "user_id", name="uq_rank_snapshots_day_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)
