from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class WatchlistItem(BaseModel):
    type: Literal["region", "country", "topic", "entity"]
    value: str
    notify_severity: Literal["critical", "high", "medium", "low"] = "medium"


class WatchlistAlert(BaseModel):
    item: WatchlistItem
    severity: Literal["critical", "high", "medium", "low", "info"]
    reason: str
    created_at: datetime
