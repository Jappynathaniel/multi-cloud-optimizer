from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class CloudConnection(Base):
    __tablename__ = "cloud_connections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(16), index=True)
    encrypted_config: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    runs: Mapped[list["CollectionRun"]] = relationship(back_populates="connection", cascade="all, delete-orphan")


class AgentConnection(Base):
    __tablename__ = "agent_connections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(24), index=True)
    encrypted_config: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CollectionRun(Base):
    __tablename__ = "collection_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("cloud_connections.id"), index=True)
    state: Mapped[str] = mapped_column(String(20), default="queued")
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connection: Mapped[CloudConnection] = relationship(back_populates="runs")


class ResourceSnapshot(Base):
    __tablename__ = "resource_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("cloud_connections.id"), index=True)
    provider_resource_id: Mapped[str] = mapped_column(String(512), index=True)
    resource_type: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(256))
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    utilization: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class CostRecord(Base):
    __tablename__ = "cost_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("cloud_connections.id"), index=True)
    period_start: Mapped[str] = mapped_column(String(32), index=True)
    period_end: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    service_name: Mapped[str] = mapped_column(String(256), index=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    billed_cost: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    source: Mapped[str] = mapped_column(String(64))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("cloud_connections.id"), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(256))
    state: Mapped[str] = mapped_column(String(24), default="proposed")
    risk: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    estimated_monthly_savings: Mapped[float] = mapped_column(Float)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), index=True)
    action: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(128))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session():
    with SessionLocal() as session:
        yield session

