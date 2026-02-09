from cybo_guard import GuardClient

ORG_ID = "d9408f3b-0ea8-410c-8330-1286b93732d1"
BASE_URL = "http://127.0.0.1:8000"

guard = GuardClient(BASE_URL, org_id=ORG_ID, timeout_seconds=15)

print("1) Low-risk request:")
d1 = guard.request_access(
    purpose="Reply to support ticket 123",
    requested_resource="db",
    data_types="public",
    scope="ticket:123",
    ttl_minutes=10,
    wait_for_approval=True,
)
print(d1)

print("\n2) Sensitive request (will likely NEEDS_APPROVAL; will poll):")
d2 = guard.request_access(
    purpose="Verify customer identity",
    requested_resource="db",
    data_types="PII",
    scope="customer:email_for_ticket_123",
    ttl_minutes=10,
    wait_for_approval=False,  # set True if you want it to wait
)
print(d2)
