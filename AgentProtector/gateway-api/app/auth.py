# app/auth.py
import hashlib
import hmac
import secrets
from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .models import Agent


# -------------------------
# Key issuing + hashing
# -------------------------

def issue_key(prefix: str = "sa_", nbytes: int = 32) -> str:
    """
    Create a new API key (shown ONCE to the user).
    Example: sa_xxxxx...
    """
    return prefix + secrets.token_urlsafe(nbytes)


def hash_key(raw_key: str) -> str:
    """
    Hash raw API key using SHA-256.
    Store ONLY this hash in DB.
    """
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# -------------------------
# Auth helpers
# -------------------------

def get_agent_from_key(db: Session, raw_key: str) -> Agent:
    """
    Fetch Agent row by raw API key using constant-time compare.
    Raises 401 if invalid.
    """
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    incoming_hash = hash_key(raw_key)

    agent = db.query(Agent).filter(Agent.api_key_hash == incoming_hash).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # extra safety: constant-time compare
    if not hmac.compare_digest(agent.api_key_hash, incoming_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return agent


# -------------------------
# FastAPI dependency
# -------------------------

def require_agent(
    x_api_key: str = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Agent:
    """
    Dependency that authenticates an agent via X-API-Key header.
    Returns Agent row if valid, otherwise 401.
    """
    return get_agent_from_key(db=db, raw_key=x_api_key)
