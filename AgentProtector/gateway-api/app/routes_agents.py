# app/routes_agents.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .models import Agent, Organization
from .auth import issue_key, hash_key, require_agent

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_agent(org_id: str, name: str, db: Session = Depends(get_db)):
    # 1) Validate org exists
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="org_id not found")

    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="name is required")

    # 2) Create key + store hash
    raw_key = issue_key()
    agent = Agent(org_id=org_id, name=name.strip(), api_key_hash=hash_key(raw_key))

    db.add(agent)
    db.commit()
    db.refresh(agent)

    # IMPORTANT: show key once only
    return {"agent_id": str(agent.id), "name": agent.name, "api_key": raw_key}


@router.get("/me")
def me(agent: Agent = Depends(require_agent)):
    """
    Used by SDK to auto-discover org_id and agent_id from X-API-Key.
    """
    return {
        "agent_id": str(agent.id),
        "org_id": str(agent.org_id),
        "name": getattr(agent, "name", None),
    }
