from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CollectedResource:
    id: str
    resource_type: str
    name: str
    region: str | None = None
    tags: dict = field(default_factory=dict)
    configuration: dict = field(default_factory=dict)
    utilization: dict = field(default_factory=dict)


@dataclass
class CollectedCost:
    period_start: str
    period_end: str
    service_name: str
    billed_cost: float
    currency: str = "USD"
    resource_id: str | None = None
    region: str | None = None
    source: str = "provider_api"
    raw: dict = field(default_factory=dict)


@dataclass
class CollectionResult:
    resources: list[CollectedResource] = field(default_factory=list)
    costs: list[CollectedCost] = field(default_factory=list)
    native_recommendations: list[dict] = field(default_factory=list)


class CloudConnector(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def collect(self) -> CollectionResult: ...

