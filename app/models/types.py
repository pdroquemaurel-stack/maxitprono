"""Types de colonnes partagés."""
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Date stockée en UTC et toujours relue avec son fuseau.

    SQLite ne garde pas le fuseau horaire : sans ce type, on relirait
    des dates « naïves », source d'erreurs sur l'heure de clôture.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Date sans fuseau horaire refusée : utiliser une date UTC")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)
