import time
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

import requests


@dataclass
class GuardDecision:
    request_id: str
    decision: str  # ALLOW / DENY / NEEDS_APPROVAL
    reason: str
    constraints: Optional[List[str]] = None
    safe_alternative: str = ""
    request_url: str = ""
    manager_console_url: str = ""


class AccessBlocked(Exception):
    pass


def enforce(decision: GuardDecision) -> None:
    if decision.decision == "ALLOW":
        return

    if decision.decision == "NEEDS_APPROVAL":
        msg = (
            "Task paused: needs approval.\n"
            f"Reason: {decision.reason}\n"
            f"Request: {decision.request_id}\n"
        )
        if decision.manager_console_url:
            msg += f"Manager Console: {decision.manager_console_url}\n"
        if decision.request_url:
            msg += f"Request Details: {decision.request_url}\n"
        raise AccessBlocked(msg.strip())

    if decision.decision == "DENY":
        msg = (
            "Task blocked permanently.\n"
            f"Reason: {decision.reason}\n"
            f"Request: {decision.request_id}\n"
        )
        if decision.request_url:
            msg += f"Request Details: {decision.request_url}\n"
        raise AccessBlocked(msg.strip())

    raise AccessBlocked(f"Task blocked: unknown decision '{decision.decision}'")


class AgentGuardClient:
    def __init__(self, base_url: str, api_key: str, timeout_sec: int = 15):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.timeout_sec = int(timeout_sec)

        if not self.base_url:
            raise ValueError("base_url is required")
        if not self.api_key:
            raise ValueError("api_key is required (X-API-Key)")
        if self.timeout_sec <= 0:
            raise ValueError("timeout_sec must be > 0")

        self._cached_org_id: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def get_org_id(self, force_refresh: bool = False) -> Optional[str]:
        """
        Requires backend endpoint: GET /agents/me
        If you don't have it, this just returns None.
        """
        if self._cached_org_id and not force_refresh:
            return self._cached_org_id

        try:
            r = requests.get(
                f"{self.base_url}/agents/me",
                headers=self._headers(),
                timeout=self.timeout_sec,
            )
            if not r.ok:
                return None

            data = r.json()
            org_id = data.get("org_id")
            if isinstance(org_id, str) and org_id:
                self._cached_org_id = org_id
                return org_id

        except Exception:
            return None

        return None

    def manager_console_url(self) -> str:
        org_id = self.get_org_id()
        if not org_id:
            return ""
        return f"{self.base_url}/manager/console?org_id={org_id}"

    # ------------------------------------------------------------------
    # ✅ request_access supports BOTH styles:
    # 1) New style: create request once and return immediately
    # 2) Old style: wait_for_approval=True -> polls SAME request_id (no duplicates)
    # ------------------------------------------------------------------
    def request_access(
        self,
        purpose: str,
        requested_resource: str,
        data_types: str,
        scope: str,
        ttl_minutes: int = 10,
        wait_for_approval: bool = False,     # backward compatible
        poll_every_sec: int = 2,             # backward compatible
        max_wait_sec: int = 120,             # backward compatible
    ) -> GuardDecision:
        """
        Creates ONE access request and returns a GuardDecision.

        If wait_for_approval=True AND decision is NEEDS_APPROVAL:
        ✅ it will POLL the SAME request_id (no new request created)
        """

        payload = {
            "purpose": purpose,
            "requested_resource": requested_resource,
            "data_types": data_types,
            "scope": scope,
            "ttl_minutes": ttl_minutes,
        }

        r = requests.post(
            f"{self.base_url}/access/request",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_sec,
        )

        if not r.ok:
            raise requests.HTTPError(
                f"{r.status_code} {r.reason} calling POST /access/request\nBody: {r.text}",
                response=r,
            )

        data = r.json()
        request_id = data["id"]
        decision = data["decision"]
        reason = data.get("decision_reason") or ""

        constraints, safe_alt = self._extract_policy_bits(data.get("policy_json"))
        req_url = f"{self.base_url}/access/request/{request_id}"

        result = GuardDecision(
            request_id=request_id,
            decision=decision,
            reason=reason,
            constraints=constraints,
            safe_alternative=safe_alt,
            request_url=req_url,
            manager_console_url=self.manager_console_url(),
        )

        # ✅ if caller wants wait-mode, poll the SAME request
        if wait_for_approval and result.decision == "NEEDS_APPROVAL":
            return self.wait_for_decision(
                request_id=result.request_id,
                poll_every_sec=poll_every_sec,
                max_wait_sec=max_wait_sec,
            )

        return result

    def wait_for_decision(
        self,
        request_id: str,
        poll_every_sec: int = 2,
        max_wait_sec: int = 120,
    ) -> GuardDecision:
        """
        Polls an EXISTING request_id until it becomes ALLOW or DENY (or times out).
        ✅ This prevents duplicate requests.
        """
        req_url = f"{self.base_url}/access/request/{request_id}"
        deadline = time.time() + int(max_wait_sec)
        poll_every_sec = max(1, int(poll_every_sec))

        constraints: Optional[List[str]] = None
        safe_alt: str = ""
        last_reason: str = ""

        while time.time() < deadline:
            g = requests.get(
                req_url,
                headers=self._headers(),
                timeout=self.timeout_sec,
            )

            if not g.ok:
                raise requests.HTTPError(
                    f"{g.status_code} {g.reason} calling GET /access/request/{request_id}\nBody: {g.text}",
                    response=g,
                )

            cur = g.json()
            cur_decision = cur["decision"]
            last_reason = cur.get("decision_reason") or ""

            c2, s2 = self._extract_policy_bits(cur.get("policy_json"))
            constraints = c2 or constraints
            safe_alt = s2 or safe_alt

            if cur_decision in ("ALLOW", "DENY"):
                return GuardDecision(
                    request_id=request_id,
                    decision=cur_decision,
                    reason=last_reason,
                    constraints=constraints,
                    safe_alternative=safe_alt,
                    request_url=req_url,
                    manager_console_url=self.manager_console_url(),
                )

            time.sleep(poll_every_sec)

        return GuardDecision(
            request_id=request_id,
            decision="NEEDS_APPROVAL",
            reason="Timed out waiting for manager approval.",
            constraints=constraints,
            safe_alternative=safe_alt,
            request_url=req_url,
            manager_console_url=self.manager_console_url(),
        )

    def _extract_policy_bits(self, policy_json: Any) -> Tuple[Optional[List[str]], str]:
        if not policy_json:
            return None, ""

        if isinstance(policy_json, str):
            try:
                policy_json = json.loads(policy_json)
            except Exception:
                return None, ""

        if not isinstance(policy_json, dict):
            return None, ""

        constraints = policy_json.get("constraints")
        if constraints is not None and not isinstance(constraints, list):
            constraints = None

        safe_alt = policy_json.get("safe_alternative") or ""
        if not isinstance(safe_alt, str):
            safe_alt = ""

        return constraints, safe_alt
