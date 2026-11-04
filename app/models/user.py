from datetime import datetime

from sqlalchemy import Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.types import UTCDateTime, utc_now


class User(Base):
    """Un joueur. Le reste de l'app ne dépend que de son `id`."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str] = mapped_column(String(20))  # tel que saisi, pour l'affichage
    nickname_key: Mapped[str] = mapped_column(String(20), unique=True)  # en minuscules, unicité
    pin_hash: Mapped[str] = mapped_column(String(200))
    country_code: Mapped[str] = mapped_column(String(2))  # code ISO, ex. "CM"
    avatar: Mapped[bytes | None] = mapped_column(LargeBinary)
    avatar_mime: Mapped[str] = mapped_column(String(30), default="")
    rules_accepted_at: Mapped[datetime] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)  # départage n°4
    # Protection contre les essais de PIN en série
    failed_pin_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
