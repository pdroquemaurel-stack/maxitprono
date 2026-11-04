from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.types import UTCDateTime, utc_now


class ApiCallLog(Base):
    """Un appel à un fournisseur de données foot, pour suivre la consommation du quota."""

    __tablename__ = "api_call_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(20), default="")
    endpoint: Mapped[str] = mapped_column(String(60))
    params: Mapped[str] = mapped_column(Text, default="")  # JSON
    status_code: Mapped[int | None] = mapped_column(Integer)
    requests_remaining: Mapped[int | None] = mapped_column(Integer)  # quota restant du jour
    error: Mapped[str] = mapped_column(Text, default="")
    called_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, index=True)
