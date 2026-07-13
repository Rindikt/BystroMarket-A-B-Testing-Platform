import datetime

from sqlalchemy import String, Enum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from schemas import EventType
from database import Base


class Event(Base):
    __tablename__ = "events"
    __table_args__ = {'schema': 'raw'}

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[int] = mapped_column()
    type_event: Mapped[EventType] = mapped_column(Enum(EventType, native_enum=False))
    time_event: Mapped[datetime.datetime] = mapped_column(server_default=func.now(), nullable=False)
    metadata_: Mapped[dict] = mapped_column('metadata', JSONB)