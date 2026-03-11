from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from sentinel.models.geo import GeoPoint


class Classification(BaseModel):
    severity: Literal["critical", "high", "medium", "low", "info"]
    category: str
    confidence: float
    source: Literal["keyword", "llm"] = "keyword"


class NewsArticle(BaseModel):
    id: str
    title: str
    url: str
    source: str
    source_tier: int = Field(default=3, ge=1, le=4)
    published_at: datetime
    classification: Classification | None = None
    location: GeoPoint | None = None
    entities: list[str] = Field(default_factory=list)
    summary: str | None = None
