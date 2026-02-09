import hashlib
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from .models import Organization, Agent, AccessRequest, AuditLog


DEFAULT_ORG_NAME = "Judge Demo Org"


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def seed_if_empty(db: Session) -> dict:
    """
    Idempotent seed:
    - If org exists, do nothing
    - If not, create org + demo agent + a few requests
    """
    org = db.query(Organization).filter(Organization.name == DEFAULT_ORG_NAME).first()
    if org:
        return {"seeded": False, "org_id": org.id}

    org = Organization(name=DEFAULT_ORG_NAME)
    db.add(org)
    db.flush()  # to get org.id

    demo_agent = Agent(
        org_id=org.id,
        name="demo_agent",
        api_key_hash=_hash_key("demo-key-123"),
    )
    db.add(demo_agent)

    # Requests for manager console
    db.add_all([
        AccessRequest(
            org_id=org.id,
            agent_id="demo_agent",
            purpose="Refund verification for ticket 123",
            requested_resource="orders_table",
            data_types="public",
            scope="ticket:123",
            ttl_minutes=30,
            decision="NEEDS_APPROVAL",
            decision_reason="",
            risk_score=15,
            policy_json={
                "engine": "hard_rules",
                "reason": "Public data + narrow scope → safe",
                "constraints": ["Only ticket:123", "No export", "Read-only"],
                "safe_alternative": "",
            }
        ),
        AccessRequest(
            org_id=org.id,
            agent_id="demo_agent",
            purpose="View customer 123 profile",
            requested_resource="customers_table",
            data_types="pii",
            scope="customer:123",
            ttl_minutes=30,
            decision="NEEDS_APPROVAL",
            decision_reason="PII access requires manager approval",
            risk_score=45,
            policy_json={
                "engine": "hard_rules",
                "reason": "PII access needs human approval",
                "constraints": ["Only customer:123", "No bulk export", "Mask sensitive fields"],
                "safe_alternative": "Ask for masked fields only",
            }
        ),
        AccessRequest(
            org_id=org.id,
            agent_id="demo_agent",
            purpose="Export all customers for marketing",
            requested_resource="customers_table",
            data_types="pii",
            scope="all",
            ttl_minutes=60,
            decision="DENY",
            decision_reason="Hard rule: bulk export of PII prohibited",
            risk_score=90,
            policy_json={
                "engine": "hard_rules",
                "reason": "Bulk export of PII is prohibited",
                "constraints": [],
                "safe_alternative": "Use aggregated metrics (no PII)",
            }
        ),
    ])

    db.add(AuditLog(
        org_id=org.id,
        event_type="SEED",
        message="Seeded judge demo org + agent + sample access requests",
    ))

    db.commit()
    return {"seeded": True, "org_id": org.id}


def force_reseed(db: Session) -> dict:
    """
    Always reset demo data (judge can test repeatedly).
    Only wipes the demo org data, not necessarily everything else.
    """
    org = db.query(Organization).filter(Organization.name == DEFAULT_ORG_NAME).first()
    if not org:
        return seed_if_empty(db)

    # Delete child tables first
    db.query(AccessRequest).filter(AccessRequest.org_id == org.id).delete()
    db.query(AuditLog).filter(AuditLog.org_id == org.id).delete()
    db.query(Agent).filter(Agent.org_id == org.id).delete()

    # Re-create demo agent + requests
    demo_agent = Agent(
        org_id=org.id,
        name="demo_agent",
        api_key_hash=_hash_key("demo-key-123"),
    )
    db.add(demo_agent)

    db.add_all([
        AccessRequest(
            org_id=org.id,
            agent_id="demo_agent",
            purpose="Refund verification for ticket 123",
            requested_resource="orders_table",
            data_types="public",
            scope="ticket:123",
            ttl_minutes=30,
            decision="NEEDS_APPROVAL",
            decision_reason="",
            risk_score=15,
            policy_json={"engine": "hard_rules", "reason": "Public + narrow scope", "constraints": ["Only ticket:123"]}
        ),
        AccessRequest(
            org_id=org.id,
            agent_id="demo_agent",
            purpose="View customer 123 profile",
            requested_resource="customers_table",
            data_types="pii",
            scope="customer:123",
            ttl_minutes=30,
            decision="NEEDS_APPROVAL",
            decision_reason="PII access requires manager approval",
            risk_score=45,
            policy_json={"engine": "hard_rules", "reason": "PII needs approval", "constraints": ["Only customer:123"]}
        ),
        AccessRequest(
            org_id=org.id,
            agent_id="demo_agent",
            purpose="Export all customers for marketing",
            requested_resource="customers_table",
            data_types="pii",
            scope="all",
            ttl_minutes=60,
            decision="DENY",
            decision_reason="Hard rule: bulk export of PII prohibited",
            risk_score=90,
            policy_json={"engine": "hard_rules", "reason": "Bulk PII export prohibited"}
        ),
    ])

    db.add(AuditLog(
        org_id=org.id,
        event_type="RESEED",
        message="Force re-seeded judge demo data",
    ))

    db.commit()
    return {"seeded": True, "org_id": org.id, "mode": "force_reseed"}
