# app/routes_access.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from .db import get_db
from .models import AccessRequest, AuditLog, Organization
from .schemas import AccessRequestCreate, AccessRequestOut, DecisionCreate
from .policy_engine import gemini_policy_decision
from .auth import require_agent

router = APIRouter(prefix="/access", tags=["Access Gateway"])


def audit(db: Session, org_id: str, event_type: str, message: str) -> None:
    db.add(AuditLog(org_id=org_id, event_type=event_type, message=message))


def _validate_org(db: Session, org_id: str) -> None:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="org not found")


@router.post("/request", response_model=AccessRequestOut, status_code=status.HTTP_201_CREATED)
def create_access_request(
    payload: AccessRequestCreate,
    db: Session = Depends(get_db),
    agent=Depends(require_agent),
):
    agent_org_id = str(agent.org_id)

    # backward compatibility check
    if getattr(payload, "org_id", None):
        if str(payload.org_id) != agent_org_id:
            raise HTTPException(status_code=403, detail="org_id does not match the agent's organization")

    org_id = agent_org_id
    _validate_org(db, org_id)

    policy = gemini_policy_decision(
        purpose=payload.purpose,
        requested_resource=payload.requested_resource,
        data_types=payload.data_types,
        scope=payload.scope,
    )

    decision = policy.get("decision", "NEEDS_APPROVAL")
    reason = policy.get("reason", "No reason")
    risk_score = policy.get("risk_score", 0)

    try:
        risk_score = int(risk_score or 0)
    except Exception:
        risk_score = 0

    ar = AccessRequest(
        org_id=org_id,
        agent_id=str(agent.id),
        purpose=(payload.purpose or "").strip(),
        requested_resource=(payload.requested_resource or "").strip(),
        data_types=(payload.data_types or "").strip(),
        scope=(payload.scope or "").strip(),
        ttl_minutes=payload.ttl_minutes,
        decision=decision,
        decision_reason=reason,
        risk_score=risk_score,
        policy_json=policy,
        decided_at=func.now() if decision in ("ALLOW", "DENY") else None,
    )

    db.add(ar)
    audit(
        db,
        org_id,
        "ACCESS_REQUESTED",
        f"agent={agent.id} decision={decision} risk={risk_score} engine={policy.get('engine')} model={policy.get('model')} reason={reason}",
    )

    db.commit()
    db.refresh(ar)
    return ar


@router.get("/request/{request_id}", response_model=AccessRequestOut)
def get_access_request(request_id: str, db: Session = Depends(get_db)):
    ar = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not ar:
        raise HTTPException(status_code=404, detail="request not found")
    return ar


@router.post("/decision/{request_id}", response_model=AccessRequestOut)
def decide_access_request(request_id: str, payload: DecisionCreate, db: Session = Depends(get_db)):
    ar = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not ar:
        raise HTTPException(status_code=404, detail="request not found")

    if ar.decision != "NEEDS_APPROVAL":
        raise HTTPException(status_code=409, detail=f"Request already decided as {ar.decision}")

    decision = (payload.decision or "").strip().upper()
    if decision not in ("ALLOW", "DENY"):
        raise HTTPException(status_code=400, detail="decision must be ALLOW or DENY")

    reason = (payload.reason or "").strip() or ("Approved" if decision == "ALLOW" else "Denied")

    ar.decision = decision
    ar.decision_reason = reason
    ar.decided_at = func.now()

    audit(db, ar.org_id, "DECISION_MADE", f"Manager decision={decision} request={request_id} reason={reason}")

    db.commit()
    db.refresh(ar)
    return ar


@router.get("/pending/{org_id}", response_model=List[AccessRequestOut])
def list_pending_by_org(org_id: str, db: Session = Depends(get_db)):
    _validate_org(db, org_id)
    return (
        db.query(AccessRequest)
        .filter(AccessRequest.org_id == org_id, AccessRequest.decision == "NEEDS_APPROVAL")
        .order_by(AccessRequest.created_at.desc())
        .all()
    )


@router.get("/audit")
def list_audit(org_id: str, limit: int = 50, db: Session = Depends(get_db)):
    _validate_org(db, org_id)
    limit = min(max(limit, 1), 200)

    return (
        db.query(AuditLog)
        .filter(AuditLog.org_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
