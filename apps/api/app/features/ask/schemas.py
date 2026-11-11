from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AskIn(BaseModel):
    farm_id: int
    question: str = Field(..., min_length=3, max_length=500)


class Recommendation(BaseModel):
    """One card under the answer. Validates the JSON block the model writes."""

    what: str = Field(min_length=3)
    why: str = Field(min_length=3)
    when_urgency: Literal["immediate", "this_week", "monitor"]
    risk_if_ignored: str
    priority: Literal["high", "medium", "low"]


class RecommendationBlock(BaseModel):
    recommendations: list[Recommendation] = Field(min_length=1, max_length=3)


class AskOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    narrative: str
    recommendations: list[dict]
    cited_chunks: list[dict]
    model_name: str
    timing_ms: dict
    saved_recommendation_ids: list[int]
