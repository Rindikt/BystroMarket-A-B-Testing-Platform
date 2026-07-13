import datetime
import enum

from pydantic import BaseModel


class EventType(enum.Enum):
    VIEW = "view"
    CLICK = "click"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"


class UserEvent(BaseModel):
    event_id: str
    user_id: int
    type_event: EventType
    metadata: dict
    time_event: datetime.datetime|None = None


class UserBulkCreate(BaseModel):
    user_id: int
    group_test: str
    date_registration: datetime.datetime
