import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import requests


class GuardError(Exception):
    pass


@dataclass
class GuardDecision:
    request_id: str
    decision: str
    reason: Optional[str] = None


class GuardClient:
    """
    Minimal Agent SDK to integrate with the Gateway API.
    - request_access() creates a request and returns decision
    - if NEEDS_APPROVAL, it polls until decision changes or timeout
    """

    def __init__(self, base_url: str, org_id: str, timeout_seconds: int = 20):
        self.base_url = base_url.rstrip("/")
        self.org_id = org_id
        self.timeout_seconds = timeout_seconds

    def request_access(
        self,
        purpose: str,
        requested_resource: str,
        data_types: str,
        scope: str,
        ttl_minutes: int = 10,
        wait_for_approval: bool = True,
        poll_interval: float = 2.0,
    ) -> GuardDecision:
        payload = {
            "org_id": self.org_id,
            "purpose": purpose,
            "requested_resource": requested_resource,
            "data_types": data_types,
            "scope": scope,
            "ttl_minutes": ttl_minutes,
        }

        r = requests.post(f"{self.base_url}/access/request", json=payload, timeout=15)
        if r.status_code >= 400:
            raise GuardError(f"Request failed: {r.status_code} {r.text}")

        data = r.json()
        request_id = data["id"]
        decision = data["decision"]
        reason = data.get("decision_reason")

        if decision in ("ALLOW", "DENY"):
            return GuardDecision(request_id=request_id, decision=decision, reason=reason)

        # NEEDS_APPROVAL
        if not wait_for_approval:
            return GuardDecision(request_id=request_id, decision=decision, reason=reason)

        return self._poll_decision(request_id, poll_interval=poll_interval)

    def get_request(self, request_id: str) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/access/request/{request_id}", timeout=15)
        if r.status_code >= 400:
            raise GuardError(f"Get failed: {r.status_code} {r.text}")
        return r.json()

    def _poll_decision(self, request_id: str, poll_interval: float = 2.0) -> GuardDecision:
        start = time.time()
        while True:
            data = self.get_request(request_id)
            decision = data["decision"]
            reason = data.get("decision_reason")

            if decision in ("ALLOW", "DENY"):
                return GuardDecision(request_id=request_id, decision=decision, reason=reason)

            if time.time() - start > self.timeout_seconds:
                # still pending
                return GuardDecision(request_id=request_id, decision="NEEDS_APPROVAL", reason="Timed out waiting for approval.")

            time.sleep(poll_interval)
