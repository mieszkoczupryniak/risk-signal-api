from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, validator

from typing import Literal
from pydantic import BaseModel


RiskLevel = Literal["low", "medium", "high"]
Sentiment = Literal["negative", "neutral", "positive"]


class NewsItemInput(BaseModel):
    headline: str = Field(..., description="Title or short description of the news item")
    body: Optional[str] = Field(
        None, description="Optional longer text of the article"
    )
    source: Optional[str] = Field(
        None, description="News source, e.g. Reuters, FT, Bloomberg"
    )
    published_at: Optional[str] = Field(
        None,
        description="ISO 8601 datetime string, e.g. 2026-03-22T10:00:00Z",
    )
    region: Optional[str] = Field(
        None, description="Region code, e.g. EU, US, MENA"
    )
    topic_hint: Optional[str] = Field(
        None, description="Optional topic hint: energy, banking, defense, macro"
    )

    @validator("headline")
    def headline_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("headline must not be empty")
        return v


class RiskSignalRequest(BaseModel):
    items: List[NewsItemInput]
    focus: Optional[str] = Field(
        None, description="Optional focus: energy, banking, geopolitics"
    )
    horizon_days: int = Field(
        7, description="Risk horizon in days, default 7", ge=1, le=365
    )

    @validator("items")
    def items_not_empty(cls, v: List[NewsItemInput]) -> List[NewsItemInput]:
        if not v:
            raise ValueError("items list must contain at least one news item")
        return v


class NewsItemOutput(BaseModel):
    headline: str
    sentiment: Sentiment
    categories: List[str]
    affects_score: bool
    risk_contribution: int


class RiskSignalResponse(BaseModel):
    overall_risk_score: int
    risk_level: RiskLevel
    top_risk_tags: List[str]
    summary: str
    methodology_note: str
    items: List[NewsItemOutput]

# === Trend API models (NEW) ===

class RiskSignalTrendPeriod(BaseModel):
    period_label: str
    items: list[NewsItemInput]


class TrendDelta(BaseModel):
    score_change: int
    direction: Literal["up", "down", "flat"]
    comment: str


class TrendPeriodSummary(BaseModel):
    period_label: str
    overall_risk_score: int
    risk_level: str


class RiskSignalTrendResponse(BaseModel):
    baseline: TrendPeriodSummary
    current: TrendPeriodSummary
    delta: TrendDelta
    driver_tags: list[str]
    methodology_note: str = (
        "Trend is computed by running the existing heuristic on both periods "
        "and comparing scores."
    )


class RiskSignalTrendRequest(BaseModel):
    baseline: RiskSignalTrendPeriod
    current: RiskSignalTrendPeriod
    focus: str | None = None
    horizon_days: int = 7
