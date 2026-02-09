# app/policy_engine.py
import os
import re
import json
import uuid
from typing import TypedDict, Literal, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from google import genai
from .models import AccessRequest
from fastapi import HTTPException


Decision = Literal["ALLOW", "DENY", "NEEDS_APPROVAL"]
Engine = Literal["gemini", "hard_rules", "fallback"]


class PolicyResult(TypedDict, total=False):
    decision: Decision
    risk_score: int
    reason: str
    constraints: List[str]
    safe_alternative: str

    # Metadata
    engine: Engine                 # gemini | hard_rules | fallback
    model: str                     # model name used (if gemini)
    overridden: bool               # hard rules overrode AI?
    override_from: Decision
    override_to: Decision


# ----------------------------
# Helpers
# ----------------------------

def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _split_types(data_types: str) -> List[str]:
    txt = _norm(data_types)
    if not txt:
        return []
    parts = re.split(r"[,\|/;\s]+", txt)
    return [p for p in parts if p]


def _scope_is_bulk(scope: str) -> bool:
    s = _norm(scope)
    bulk_words = ["all", "everyone", "entire", "export", "dump", "bulk", "full"]
    if any(w in s for w in bulk_words):
        return True
    if re.search(r":\s*(all|\*|everything)\b", s):
        return True
    return False


def _scope_is_narrow(scope: str) -> bool:
    """
    Narrow means: scope contains something like customer:123, ticket:abc-1, user:9, etc.
    """
    s = _norm(scope)
    m = re.search(r":\s*([a-z0-9\-_]{2,})", s)
    if not m:
        return False
    val = m.group(1)
    if val in ("all", "*", "everything"):
        return False
    return True


def _clean_model_name(model: str) -> str:
    """
    Accept both 'models/xxx' and 'xxx' and normalize to 'xxx'
    """
    m = (model or "").strip()
    if m.startswith("models/"):
        m = m[len("models/"):]
    return m or "gemini-3-flash-preview"


# ----------------------------
# Hard-rule layer
# ----------------------------

def hard_policy_decision(
    purpose: str,
    requested_resource: str,
    data_types: str,
    scope: str,
) -> Optional[PolicyResult]:
    types = _split_types(data_types)
    scope_n = _norm(scope)

    sensitive_types = {
        "pii", "financial", "secret", "secrets",
        "credential", "credentials", "password", "token", "key"
    }
    is_sensitive = any(t in sensitive_types for t in types)

    # 1) Block bulk always
    if _scope_is_bulk(scope_n):
        if is_sensitive:
            return {
                "engine": "hard_rules",
                "model": "",
                "decision": "DENY",
                "risk_score": 95,
                "reason": "Hard rule: bulk access to sensitive data is prohibited.",
                "constraints": [
                    "Bulk export is not allowed",
                    "Narrow scope to one identifier (e.g., customer:123)"
                ],
                "safe_alternative": "Request one specific record (e.g., customer:123) or use aggregated/anonymized data.",
            }
        return {
            "engine": "hard_rules",
            "model": "",
            "decision": "DENY",
            "risk_score": 85,
            "reason": "Hard rule: bulk access is prohibited.",
            "constraints": [
                "Bulk export is not allowed",
                "Narrow scope to one identifier (e.g., ticket:123)"
            ],
            "safe_alternative": "Narrow the scope to a specific entity instead of all records.",
        }

    # 2) Sensitive but not narrow => approval needed
    if is_sensitive and not _scope_is_narrow(scope_n):
        return {
            "engine": "hard_rules",
            "model": "",
            "decision": "NEEDS_APPROVAL",
            "risk_score": 75,
            "reason": "Hard rule: sensitive data requires manager approval unless scope is clearly narrow.",
            "constraints": [
                "Scope must be narrowed to one identifier",
                "Sensitive access must be audited"
            ],
            "safe_alternative": "Use non-sensitive/aggregated data or narrow scope (e.g., customer:123).",
        }

    # 3) Public + narrow => allow
    if ("public" in types or not is_sensitive) and _scope_is_narrow(scope_n):
        if "public" in types:
            return {
                "engine": "hard_rules",
                "model": "",
                "decision": "ALLOW",
                "risk_score": 5,
                "reason": "Hard rule: public data with narrow scope is allowed.",
                "constraints": [f"Access limited to {scope.strip()}"],
                "safe_alternative": "",
            }

    return None


def enforce_hard_rules(
    purpose: str,
    requested_resource: str,
    data_types: str,
    scope: str,
    policy: PolicyResult,
) -> PolicyResult:
    """
    Hard rules ALWAYS win if they are stricter than Gemini.
    """
    hard = hard_policy_decision(purpose, requested_resource, data_types, scope)
    if hard is None:
        return policy

    hard_decision = hard.get("decision")
    gem_decision = policy.get("decision")

    # If hard is stricter, override (and annotate)
    if hard_decision in ("DENY", "NEEDS_APPROVAL") and gem_decision == "ALLOW":
        hard["overridden"] = True
        hard["override_from"] = "ALLOW"
        hard["override_to"] = hard_decision  # type: ignore[assignment]
        hard["reason"] = f"{hard.get('reason')} (Overrode AI: ALLOW → {hard_decision})"
        return hard

    if hard_decision == "DENY" and gem_decision == "NEEDS_APPROVAL":
        hard["overridden"] = True
        hard["override_from"] = "NEEDS_APPROVAL"
        hard["override_to"] = "DENY"
        hard["reason"] = f"{hard.get('reason')} (Overrode AI: NEEDS_APPROVAL → DENY)"
        return hard

    return policy


# ----------------------------
# Deterministic fallback policy
# ----------------------------

def _fallback_policy(
    purpose: str,
    requested_resource: str,
    data_types: str,
    scope: str,
    reason: str,
    risk_score: int = 60,
) -> PolicyResult:
    base: PolicyResult = {
        "engine": "fallback",
        "model": "",
        "decision": "NEEDS_APPROVAL",
        "risk_score": risk_score,
        "reason": reason,
        "constraints": ["Manager approval required"],
        "safe_alternative": "Narrow the scope (e.g., customer:123) or use aggregated data.",
    }
    return enforce_hard_rules(purpose, requested_resource, data_types, scope, base)


# ----------------------------
# Gemini policy decision
# ----------------------------

def gemini_policy_decision(
    purpose: str,
    requested_resource: str,
    data_types: str,
    scope: str,
) -> PolicyResult:
    # 1) Hard rules first
    hard = hard_policy_decision(purpose, requested_resource, data_types, scope)
    if hard is not None:
        return hard

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_policy(
            purpose, requested_resource, data_types, scope,
            reason="GEMINI_API_KEY missing; routed to manager approval.",
            risk_score=60,
        )

    model = _clean_model_name(os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))
    client = genai.Client(api_key=api_key)

    system = (
        "You are a security policy engine for AI agents. "
        "Return ONLY valid JSON. "
        "Rules: deny bulk exports, require approval for PII/secrets/credentials/financial unless scope is one ID, "
        "allow public data with narrow scope."
    )

    user = (
        "Evaluate this access request and return JSON.\n\n"
        f"purpose: {purpose}\n"
        f"requested_resource: {requested_resource}\n"
        f"data_types: {data_types}\n"
        f"scope: {scope}\n\n"
        "Output JSON fields: decision, risk_score, reason, constraints (array), safe_alternative (string)."
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=[{"role": "user", "parts": [{"text": system + "\n\n" + user}]}],
            config={
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "decision": {"type": "string", "enum": ["ALLOW", "DENY", "NEEDS_APPROVAL"]},
                        "risk_score": {"type": "integer", "minimum": 0, "maximum": 100},
                        "reason": {"type": "string"},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                        "safe_alternative": {"type": "string"},
                    },
                    "required": ["decision", "risk_score", "reason", "constraints"],
                },
            },
        )

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, dict):
            policy: PolicyResult = {
                "engine": "gemini",
                "model": model,
                "decision": parsed.get("decision", "NEEDS_APPROVAL"),
                "risk_score": int(parsed.get("risk_score", 70) or 70),
                "reason": str(parsed.get("reason", "No reason provided")),
                "constraints": parsed.get("constraints") if isinstance(parsed.get("constraints"), list) else ["Manager approval required"],
                "safe_alternative": str(parsed.get("safe_alternative", "")),
                "overridden": False,
            }
            return enforce_hard_rules(purpose, requested_resource, data_types, scope, policy)

        txt = getattr(response, "text", "") or ""
        return _fallback_policy(
            purpose, requested_resource, data_types, scope,
            reason=f"Model output not parsed; routed to manager approval. Raw: {txt[:120]}",
            risk_score=70,
        )

    except Exception as e:
        return _fallback_policy(
            purpose, requested_resource, data_types, scope,
            reason=f"Policy model unavailable; routed to manager approval. ({type(e).__name__})",
            risk_score=65,
        )


# ----------------------------
# Gemini "Manager Assist"
# ----------------------------

def gemini_manager_recommendation(
    purpose: str,
    requested_resource: str,
    data_types: str,
    scope: str,
    current_policy: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Returns a manager-facing recommendation for pending items.
    NEVER auto-applies. Just suggests ALLOW or DENY + a professional reason.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    model = _clean_model_name(os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))

    if not api_key:
        return {
            "enabled": False,
            "error": "GEMINI_API_KEY missing",
            "recommendation": "DENY",
            "confidence": 0,
            "manager_reason": "",
            "key_points": ["Gemini not configured."],
            "model": model,
        }

    client = genai.Client(api_key=api_key)

    policy_text = ""
    if isinstance(current_policy, dict) and current_policy:
        policy_text = f"\n\nCurrent policy output:\n{json.dumps(current_policy, ensure_ascii=False)[:1500]}"

    system = (
        "You are a security manager assistant for access approvals. "
        "You must recommend either ALLOW or DENY for a SINGLE request. "
        "Write a short professional manager_reason suitable for audit logs. "
        "If uncertain, choose DENY (security-first). "
        "Return ONLY valid JSON."
    )

    user = (
        "Given the access request below, recommend a manager decision.\n"
        f"purpose: {purpose}\n"
        f"requested_resource: {requested_resource}\n"
        f"data_types: {data_types}\n"
        f"scope: {scope}"
        f"{policy_text}\n\n"
        "Output JSON fields:\n"
        "- recommendation: 'ALLOW' or 'DENY'\n"
        "- confidence: integer 0..100\n"
        "- manager_reason: short audit-ready sentence\n"
        "- key_points: array of 2-5 short bullets\n"
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=[{"role": "user", "parts": [{"text": system + "\n\n" + user}]}],
            config={
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "recommendation": {"type": "string", "enum": ["ALLOW", "DENY"]},
                        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                        "manager_reason": {"type": "string"},
                        "key_points": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["recommendation", "confidence", "manager_reason", "key_points"],
                },
            },
        )

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, dict):
            manager_reason = str(parsed.get("manager_reason", "") or "").strip()
            return {
                "enabled": True,
                "recommendation": parsed.get("recommendation", "DENY"),
                "confidence": int(parsed.get("confidence", 60) or 60),
                "manager_reason": manager_reason,
                "key_points": parsed.get("key_points") if isinstance(parsed.get("key_points"), list) else [],
                "model": model,
            }

        txt = getattr(response, "text", "") or ""
        return {
            "enabled": False,
            "error": "Unparsed Gemini response",
            "recommendation": "DENY",
            "confidence": 0,
            "manager_reason": "",
            "key_points": [f"Raw: {txt[:120]}"],
            "model": model,
        }

    except Exception as e:
        return {
            "enabled": False,
            "error": f"Gemini error: {type(e).__name__}",
            "recommendation": "DENY",
            "confidence": 0,
            "manager_reason": "",
            "key_points": [f"{type(e).__name__}: Gemini call failed"],
            "model": model,
        }


# ==========================================================
# Demo-agent helpers (MUST be at top-level, not nested)
# ==========================================================

def _simple_intent_parse(prompt: str) -> dict:
    """
    VERY IMPORTANT: prompt is untrusted.
    Parse into strict schema (demo). Do not allow prompt to choose arbitrary tools.
    """
    p = (prompt or "").lower()

    # Default safe-ish task
    tool = "orders_table"
    data_types = "public"
    scope = "ticket:123"
    purpose = (prompt or "")[:120]

    if "customer" in p:
        tool = "customers_table"
        data_types = "pii"
        scope = "customer:123"

    if ("export" in p) or ("all customers" in p) or ("dump" in p):
        tool = "customers_table"
        data_types = "pii"
        scope = "all"

    suspicious = any(x in p for x in [
        "ignore policy", "bypass", "override", "system prompt",
        "admin", "sudo", "dump", "exfiltrate"
    ])

    return {
        "purpose": purpose,
        "requested_resource": tool,
        "data_types": data_types,
        "scope": scope,
        "suspicious": suspicious
    }


def gateway_decide_from_prompt(db: Session, org_id: str, prompt: str) -> AccessRequest:
    intent = _simple_intent_parse(prompt)

    # Default
    risk = 10
    decision: Decision = "ALLOW"
    decision_reason = "Auto-approved: low risk"
    policy_json: Dict[str, Any] = {"engine": "hard_rules", "reason": "low risk", "constraints": []}

    # Hard rule: any PII => needs approval (no auto allow)
    if intent["data_types"] == "pii":
        decision = "NEEDS_APPROVAL"
        decision_reason = "PII access requires manager approval"
        risk = 60
        policy_json["reason"] = "PII requires approval"
        policy_json["constraints"] = ["Limit scope to customer:ID", "No bulk export"]

    # Suspicious prompt => force approval
    if intent["suspicious"]:
        decision = "NEEDS_APPROVAL"
        decision_reason = "Suspicious / prompt-injection patterns detected"
        risk = max(risk, 85)
        policy_json["reason"] = "Possible prompt injection / policy bypass attempt"
        policy_json["constraints"] = ["Deny bulk access", "Require explicit scope", "Log and review"]

    # Optional: attach Gemini manager-assist notes for transparency
    if os.getenv("GEMINI_API_KEY"):
        try:
            rec = gemini_manager_recommendation(
                purpose=intent["purpose"],
                requested_resource=intent["requested_resource"],
                data_types=intent["data_types"],
                scope=intent["scope"],
                current_policy=policy_json,
            )
            policy_json["gemini"] = {
                "enabled": rec.get("enabled", False),
                "recommendation": rec.get("recommendation"),
                "confidence": rec.get("confidence"),
                "key_points": rec.get("key_points", []),
                "model": rec.get("model", ""),
                "error": rec.get("error", ""),
            }
            policy_json["engine"] = "hard_rules+gemini"
            policy_json["model"] = rec.get("model", "")
        except Exception as e:
            policy_json["gemini_error"] = str(e)

    ar = AccessRequest(
        id=str(uuid.uuid4()),
        org_id=org_id,
        agent_id="demo_agent",
        purpose=intent["purpose"],
        requested_resource=intent["requested_resource"],
        data_types=intent["data_types"],
        scope=intent["scope"],
        ttl_minutes=30,
        decision=decision,
        decision_reason=decision_reason,
        risk_score=risk,
        policy_json=policy_json,
        created_at=func.now(),
    )
    db.add(ar)
    db.commit()
    db.refresh(ar)
    return ar


def issue_grant_if_approved(db: Session, ar: AccessRequest) -> dict:
    """
    Simulated tool gate: if manager approved, return tool output. If not, block.
    """
    if ar.decision != "ALLOW":
        raise HTTPException(status_code=403, detail="Not approved yet. Approve in Manager Console first.")

    return {
        "tool": ar.requested_resource,
        "scope": ar.scope,
        "result_preview": f"✅ Tool executed successfully for scope={ar.scope}. (demo output)",
    }
