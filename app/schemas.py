from typing import Literal
from pydantic import BaseModel, Field


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    provider: Literal["aws", "azure", "gcp"]
    config: dict


class AgentQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class RecommendationDecision(BaseModel):
    actor: str = Field(min_length=2, max_length=128)
    note: str | None = Field(default=None, max_length=2000)

