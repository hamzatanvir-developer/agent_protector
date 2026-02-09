# app/models.py
import uuid
from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.sql import func
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import JSONB

from .db import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AccessRequest(Base):
    """
    Decision can be: ALLOW / DENY / NEEDS_APPROVAL
    """
    __tablename__ = "access_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)

    agent_id = Column(String, nullable=True, index=True)

    purpose = Column(String, nullable=False)
    requested_resource = Column(String, nullable=False)
    data_types = Column(String, nullable=False)
    scope = Column(String, nullable=False)
    ttl_minutes = Column(Integer, nullable=False, default=10)

    decision = Column(String, nullable=False, default="NEEDS_APPROVAL")
    decision_reason = Column(Text, nullable=True)

    risk_score = Column(Integer, nullable=True)

    # Portable JSON (SQLite = JSON(TEXT), Postgres = JSONB)
    policy_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)

    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)

    api_key_hash = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
