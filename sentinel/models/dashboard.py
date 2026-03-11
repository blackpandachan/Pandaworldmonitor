from datetime import datetime

from pydantic import BaseModel, Field


class DashboardState(BaseModel):
    articles: list[dict] = Field(default_factory=list)
    risk_scores: list[dict] = Field(default_factory=list)
    convergence_alerts: list[dict] = Field(default_factory=list)
    watchlist_alerts: list[dict] = Field(default_factory=list)
    data_freshness: dict[str, datetime] = Field(default_factory=dict)
    last_brief: dict | None = None
