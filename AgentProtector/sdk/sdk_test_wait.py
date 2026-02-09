import os
from dotenv import load_dotenv

from agent_guard import AgentGuardClient, AccessBlocked, enforce

load_dotenv()

BASE_URL = os.getenv("GATEWAY_BASE_URL", "http://127.0.0.1:8000")
AGENT_API_KEY = os.getenv("AGENT_API_KEY")


def read_customer_data():
    print("📦 Reading customer data... (dummy function)")
    print("✅ DONE: simulated CRM read")


def header(title: str):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def show_env():
    print("BASE_URL:", BASE_URL)
    print("AGENT_API_KEY starts:", (AGENT_API_KEY or "")[:6])
    print("Tip: If AGENT_API_KEY is None → fix sdk/.env\n")


if not AGENT_API_KEY:
    header("❌ Missing SDK env")
    show_env()
    raise SystemExit("Please set AGENT_API_KEY in sdk/.env")


client = AgentGuardClient(base_url=BASE_URL, api_key=AGENT_API_KEY, timeout_sec=60)

header("✅ AgentProtector SDK Demo Started")
show_env()


# -------------------------------------------------------------------
# Test A: ALLOW
# -------------------------------------------------------------------
header("TEST A — ALLOW (low risk) → agent should continue")

try:
    decision = client.request_access(
        purpose="Read public status for ticket 123",
        requested_resource="helpdesk",
        data_types="PUBLIC",
        scope="ticket:123",
        wait_for_approval=False,
    )

    print(f"Gateway decision: {decision.decision} | request_id={decision.request_id}")

    enforce(decision)
    print("✅ Access granted. Doing work...")
    read_customer_data()

except AccessBlocked as e:
    print("🛑 TASK STOPPED (unexpected for ALLOW)")
    print(str(e))


# -------------------------------------------------------------------
# Test B: DENY
# -------------------------------------------------------------------
header("TEST B — DENY (high risk bulk PII) → agent should stop immediately")

try:
    decision = client.request_access(
        purpose="Customer support follow-up",
        requested_resource="crm",
        data_types="PII",
        scope="customer:all",  # bulk → should DENY
        wait_for_approval=False,
    )

    print(f"Gateway decision: {decision.decision} | request_id={decision.request_id}")

    enforce(decision)
    print("✅ Access granted. Doing work... (should NOT happen)")
    read_customer_data()

except AccessBlocked as e:
    print("🛑 TASK STOPPED (expected)")
    print(str(e))


# -------------------------------------------------------------------
# Test C: NEEDS_APPROVAL (NO DUPLICATE REQUESTS)
# -------------------------------------------------------------------
header("TEST C — NEEDS_APPROVAL (medium risk)")

print("Step 1) Create ONE request (non-blocking)...")
decision = client.request_access(
    purpose="Support follow-up for customer 123",
    requested_resource="crm",
    data_types="PII",
    scope="customer:123",
    wait_for_approval=False,  # create only
)

print(f"Gateway decision: {decision.decision} | request_id={decision.request_id}")

try:
    enforce(decision)
    print("✅ Access granted. Doing work...")
    read_customer_data()

except AccessBlocked as e:
    print("🛑 TASK PAUSED (expected if NEEDS_APPROVAL)")
    print(str(e))

    if decision.manager_console_url:
        print("\n➡️ Approve/Deny it in Manager Console:")
        print("   " + decision.manager_console_url)
    else:
        print("\n➡️ Open Manager Console (org_id required):")
        print("   " + f"{BASE_URL}/manager/console?org_id=<YOUR_ORG_ID>")

    print("\nStep 2) DEMO WAIT: Now wait on the SAME request_id (no new request)...")

    final_decision = client.wait_for_decision(
        request_id=decision.request_id,
        poll_every_sec=2,
        max_wait_sec=180,
    )

    print(f"Final decision: {final_decision.decision} | request_id={final_decision.request_id}")

    try:
        enforce(final_decision)
        print("✅ Approved! Doing work...")
        read_customer_data()
    except AccessBlocked as e2:
        print("🛑 TASK STOPPED (denied or timed out)")
        print(str(e2))


header("✅ Demo Finished")
print("Tip: For your video, show Test B (DENY) + Test C (approve in UI + continue).")
