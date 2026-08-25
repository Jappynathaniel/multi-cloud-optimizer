from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents import explain_recommendation
from app.config import get_settings
from app.db import CloudConnection, CollectionRun, CostRecord, Recommendation, RecommendationEvent, get_session, init_db
from app.scenarios import ScenarioRequest, analyze_scenario
from app.schemas import AgentQuestion, ConnectionCreate, RecommendationDecision
from app.security import encrypt_config
from app.services import build_recommendations, collect_connection


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="RedBridge FinOps", version="3.0.0", lifespan=lifespan,
    description="Read-only multi-cloud FinOps discovery, recommendation, and approval workflows.")


@app.get("/")
def dashboard():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():
    settings = get_settings()
    return {"status": "healthy", "version": app.version, "mode": "read_only",
            "agent_enabled": bool(settings.openai_api_key), "encryption_configured": bool(settings.encryption_key)}


@app.get("/v1/capabilities")
def capabilities():
    return {"aws": {"cost": "Cost Explorer", "inventory": "EC2", "native_recommendations": "Compute Optimizer"},
            "azure": {"cost": "Cost Management query", "inventory": "planned", "native_recommendations": "planned"},
            "gcp": {"cost": "BigQuery Billing export", "inventory": "planned", "native_recommendations": "planned"},
            "execution": "not implemented by design"}


@app.post("/v1/connections", status_code=201)
def create_connection(payload: ConnectionCreate, session: Session = Depends(get_session)):
    if session.scalar(select(CloudConnection).where(CloudConnection.name == payload.name)):
        raise HTTPException(409, "A connection with this name already exists")
    connection = CloudConnection(name=payload.name, provider=payload.provider, encrypted_config=encrypt_config(payload.config))
    session.add(connection); session.commit(); session.refresh(connection)
    return {"id": connection.id, "name": connection.name, "provider": connection.provider, "status": connection.status}


@app.get("/v1/connections")
def list_connections(session: Session = Depends(get_session)):
    rows = session.scalars(select(CloudConnection).order_by(CloudConnection.id.desc())).all()
    return [{"id": row.id, "name": row.name, "provider": row.provider, "status": row.status, "created_at": row.created_at} for row in rows]


@app.post("/v1/connections/{connection_id}/collect")
def collect(connection_id: int, session: Session = Depends(get_session)):
    connection = session.get(CloudConnection, connection_id)
    if not connection: raise HTTPException(404, "Connection not found")
    run = collect_connection(session, connection)
    if run.state == "failed": raise HTTPException(502, {"run_id": run.id, "error": run.error})
    return {"run_id": run.id, "state": run.state, "summary": run.summary}


@app.get("/v1/collection-runs")
def collection_runs(session: Session = Depends(get_session)):
    rows = session.scalars(select(CollectionRun).order_by(CollectionRun.id.desc()).limit(50)).all()
    return [{"id": row.id, "connection_id": row.connection_id, "state": row.state, "summary": row.summary,
             "error": row.error, "started_at": row.started_at, "finished_at": row.finished_at} for row in rows]


@app.post("/v1/connections/{connection_id}/recommendations")
def generate_recommendations(connection_id: int, session: Session = Depends(get_session)):
    if not session.get(CloudConnection, connection_id): raise HTTPException(404, "Connection not found")
    return {"created": build_recommendations(session, connection_id), "execution_mode": "read_only"}


@app.get("/v1/recommendations")
def recommendations(connection_id: int | None = None, session: Session = Depends(get_session)):
    query = select(Recommendation).order_by(Recommendation.created_at.desc())
    if connection_id: query = query.where(Recommendation.connection_id == connection_id)
    rows = session.scalars(query.limit(500)).all()
    return [{"id": row.id, "connection_id": row.connection_id, "resource_id": row.resource_id, "kind": row.kind,
             "title": row.title, "state": row.state, "risk": row.risk, "confidence": row.confidence,
             "estimated_monthly_savings": row.estimated_monthly_savings, "evidence": row.evidence} for row in rows]


@app.post("/v1/recommendations/{recommendation_id}/decision/{decision}")
def decide_recommendation(recommendation_id: int, decision: str, payload: RecommendationDecision,
                          session: Session = Depends(get_session)):
    if decision not in {"approve", "reject"}: raise HTTPException(422, "decision must be approve or reject")
    row = session.get(Recommendation, recommendation_id)
    if not row: raise HTTPException(404, "Recommendation not found")
    if row.state != "proposed": raise HTTPException(409, f"Recommendation is already {row.state}")
    row.state = "approved" if decision == "approve" else "rejected"
    session.add(RecommendationEvent(recommendation_id=row.id, action=decision, actor=payload.actor, note=payload.note))
    session.commit()
    return {"id": row.id, "state": row.state, "execution_mode": "No cloud changes are performed by RedBridge."}


@app.post("/v1/scenarios/capacity")
def capacity_scenario(payload: ScenarioRequest):
    return analyze_scenario(payload)


@app.post("/v1/recommendations/{recommendation_id}/agent-explanation")
def agent_explanation(recommendation_id: int, payload: AgentQuestion, session: Session = Depends(get_session)):
    row = session.get(Recommendation, recommendation_id)
    if not row: raise HTTPException(404, "Recommendation not found")
    return explain_recommendation({"title": row.title, "kind": row.kind, "risk": row.risk,
        "confidence": row.confidence, "savings": row.estimated_monthly_savings, "evidence": row.evidence}, payload.question)


@app.get("/v1/portfolio")
def portfolio(session: Session = Depends(get_session)):
    cost = session.scalar(select(func.coalesce(func.sum(CostRecord.billed_cost), 0.0)))
    savings = session.scalar(select(func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0.0)))
    return {"recorded_cost": round(float(cost), 2), "proposed_monthly_savings": round(float(savings), 2),
            "note": "Savings with different strategies may be alternatives and must not be summed for execution planning."}

