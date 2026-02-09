from datetime import datetime
from typing import Optional, Dict, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# -----------------------
# Shared types
# -----------------------

Decision = Literal["ALLOW", "DENY", "NEEDS_APPROVAL"]


def _clean_str(v: str) -> str:
    return (v or "").strip()


# -----------------------
# ORGS
# -----------------------

class OrgCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = _clean_str(v)
        if not v:
            raise ValueError("name cannot be empty")
        return v


class OrgOut(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -----------------------
# ACCESS REQUESTS
# -----------------------

class AccessRequestCreate(BaseModel):
    purpose: str = Field(..., min_length=3, max_length=500)
    requested_resource: str = Field(..., min_length=2, max_length=80)
    data_types: str = Field(..., min_length=2, max_length=120)
    scope: str = Field(..., min_length=2, max_length=200)
    ttl_minutes: int = Field(default=10, ge=1, le=1440)  # 1 min to 24h

    @field_validator("purpose", "requested_resource", "data_types", "scope")
    @classmethod
    def trim_and_validate(cls, v: str) -> str:
        v = _clean_str(v)
        if not v:
            raise ValueError("field cannot be empty")
        return v


class DecisionCreate(BaseModel):
    decision: Literal["ALLOW", "DENY"]
    reason: Optional[str] = None

    @field_validator("reason")
    @classmethod
    def trim_reason(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = _clean_str(v)
        return v or None


class AccessRequestOut(BaseModel):
    id: str
    org_id: str
    agent_id: Optional[str] = None

    purpose: str
    requested_resource: str
    data_types: str
    scope: str
    ttl_minutes: int

    decision: Decision
    decision_reason: Optional[str] = None
    risk_score: Optional[int] = None

    # JSONB -> dict
    policy_json: Optional[Dict[str, Any]] = None

    created_at: datetime
    decided_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
