from datetime import datetime

from pydantic import BaseModel, Field

from sentinel.models.geo import GeoPoint


class ConflictEvent(BaseModel):
    id: str
    event_type: str
    country: str
    location: GeoPoint
    occurred_at: datetime
    fatalities: int = 0
    actors: list[str] = Field(default_factory=list)
    source: str
    admin1: str = ""


class NaturalEvent(BaseModel):
    id: str
    event_type: str
    title: str
    location: GeoPoint
    occurred_at: datetime
    magnitude: float | None = None
    source: str
    details: dict = Field(default_factory=dict)
