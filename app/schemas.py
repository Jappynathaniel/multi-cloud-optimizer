from typing import Literal
from pydantic import BaseModel, Field


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    provider: Literal["aws", "azure", "gcp"]
    config: dict


class AgentConnectionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    provider: Literal["openai", "anthropic"]
    api_key: str = Field(min_length=10)
    model: str = Field(min_length=2, max_length=128)


class AgentQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    agent_connection_id: int | None = None


class RecommendationDecision(BaseModel):
    actor: str = Field(min_length=2, max_length=128)
    note: str | None = Field(default=None, max_length=2000)

