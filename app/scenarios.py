from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    current_monthly_cost: float = Field(gt=0)
    traffic_change_percent: float = Field(ge=-100, le=1000)
    utilization_target_percent: float = Field(default=65, gt=0, le=100)
    current_utilization_percent: float = Field(gt=0, le=100)
    min_monthly_cost: float = Field(default=0, ge=0)


def analyze_scenario(input: ScenarioRequest) -> dict:
    """Transparent capacity cost projection; not a provider price quotation."""
    demand_factor = 1 + input.traffic_change_percent / 100
    required_capacity_factor = demand_factor * input.current_utilization_percent / input.utilization_target_percent
    projected_cost = max(input.min_monthly_cost, input.current_monthly_cost * required_capacity_factor)
    return {
        "assumptions": ["Cost changes linearly with required capacity.", "Unit pricing, discounts, and architecture remain unchanged.",
                        "Validate against provider pricing and real peak metrics before approval."],
        "demand_factor": round(demand_factor, 3),
        "required_capacity_factor": round(required_capacity_factor, 3),
        "projected_monthly_cost": round(projected_cost, 2),
        "change_from_current": round(projected_cost - input.current_monthly_cost, 2),
        "mode": "deterministic_scenario",
    }

