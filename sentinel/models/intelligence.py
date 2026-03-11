from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SituationBrief(BaseModel):
    region: str | None = None
    country: str | None = None
    generated_at: datetime
    brief: str
    key_developments: list[str] = Field(default_factory=list)
    risk_level: str = "unknown"
    watch_items: list[str] = Field(default_factory=list)
    sources_used: int = 0
    model: str = ""


class DeltaBrief(BaseModel):
    generated_at: datetime
    comparing_to: datetime
    new_developments: list[str] = Field(default_factory=list)
    escalations: list[str] = Field(default_factory=list)
    de_escalations: list[str] = Field(default_factory=list)
    emerging_patterns: list[str] = Field(default_factory=list)
    brief: str
    model: str = ""


class CountryRiskScore(BaseModel):
    country_code: str
    country_name: str
    score: float
    components: dict = Field(default_factory=dict)
    trend: Literal["rising", "stable", "falling"] = "stable"
    updated_at: datetime
