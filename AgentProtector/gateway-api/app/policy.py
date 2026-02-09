def evaluate_policy(requested_resource: str, data_types: str, scope: str, ttl_minutes: int) -> tuple[str, str]:
    """
    Returns: (decision, reason)
    decision: ALLOW / DENY / NEEDS_APPROVAL
    """

    dt = data_types.lower()
    sc = scope.lower()
    rr = requested_resource.lower()

    # Hard DENY rules (clear danger)
    if "all" in sc or "bulk" in sc or "export" in sc:
        return ("DENY", "Bulk/Export scope is blocked by default policy.")

    if "external" in sc or "http" in sc or "https" in sc:
        return ("DENY", "External destinations are blocked by default policy.")

    # Needs approval rules (sensitive data)
    if "pii" in dt or "financial" in dt or "medical" in dt:
        return ("NEEDS_APPROVAL", "Sensitive data type requires manager approval.")

    # TTL too long → approval
    if ttl_minutes > 15:
        return ("NEEDS_APPROVAL", "TTL above 15 minutes requires approval.")

    # Default allow (low risk)
    return ("ALLOW", "Low-risk request allowed by default policy.")
