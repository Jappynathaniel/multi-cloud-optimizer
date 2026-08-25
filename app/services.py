from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors import CONNECTORS
from app.connectors.base import CollectionResult
from app.db import CloudConnection, CollectionRun, CostRecord, Recommendation, ResourceSnapshot
from app.security import decrypt_config


def collect_connection(session: Session, connection: CloudConnection) -> CollectionRun:
    run = CollectionRun(connection_id=connection.id, state="running")
    session.add(run); session.commit(); session.refresh(run)
    try:
        result: CollectionResult = CONNECTORS[connection.provider](decrypt_config(connection.encrypted_config)).collect()
        for resource in result.resources:
            session.add(ResourceSnapshot(connection_id=connection.id, provider_resource_id=resource.id,
                resource_type=resource.resource_type, name=resource.name, region=resource.region, tags=resource.tags,
                configuration=resource.configuration, utilization=resource.utilization))
        for cost in result.costs:
            session.add(CostRecord(connection_id=connection.id, period_start=cost.period_start, period_end=cost.period_end,
                resource_id=cost.resource_id, service_name=cost.service_name, region=cost.region, billed_cost=cost.billed_cost,
                currency=cost.currency, source=cost.source, raw=cost.raw))
        run.state = "completed"; connection.status = "connected"
        run.summary = {"resources": len(result.resources), "cost_records": len(result.costs),
                       "native_recommendations": len(result.native_recommendations)}
        for native in result.native_recommendations:
            _store_native_recommendation(session, connection.id, native)
    except Exception as exc:
        run.state = "failed"; connection.status = "error"; run.error = str(exc)
    run.finished_at = datetime.now(timezone.utc)
    session.commit(); session.refresh(run)
    return run


def _store_native_recommendation(session: Session, connection_id: int, native: dict) -> None:
    if "notice" in native:
        return
    savings = float(native.get("estimatedMonthlySavings", 0) or 0)
    session.add(Recommendation(connection_id=connection_id, resource_id=native.get("instanceArn"), kind="native_rightsize",
        title="Review provider rightsizing recommendation", state="proposed", risk="medium", confidence=0.75,
        estimated_monthly_savings=savings, evidence={"provider_finding": native, "source": "provider_native"}))


def build_recommendations(session: Session, connection_id: int) -> int:
    """Rules use stored evidence only. They never execute cloud mutations."""
    snapshots = session.scalars(select(ResourceSnapshot).where(ResourceSnapshot.connection_id == connection_id)
        .order_by(ResourceSnapshot.observed_at.desc())).all()
    created = 0
    for resource in snapshots:
        state = resource.configuration.get("state")
        tags = resource.tags or {}
        environment = tags.get("environment", tags.get("Environment", "unknown")).lower()
        if state == "stopped":
            session.add(Recommendation(connection_id=connection_id, resource_id=resource.provider_resource_id,
                kind="stopped_resource_review", title="Review stopped resource and attached storage", state="proposed",
                risk="low", confidence=0.7, estimated_monthly_savings=0,
                evidence={"resource_type": resource.resource_type, "state": state,
                          "reason": "Stopped compute can still retain chargeable attached resources."}))
            created += 1
        if environment in {"development", "test", "staging"} and state == "running":
            session.add(Recommendation(connection_id=connection_id, resource_id=resource.provider_resource_id,
                kind="nonproduction_schedule", title="Assess an off-hours schedule", state="proposed", risk="low",
                confidence=0.6, estimated_monthly_savings=0,
                evidence={"environment": environment, "reason": "No cost is claimed until pricing and required uptime are verified."}))
            created += 1
    session.commit()
    return created

