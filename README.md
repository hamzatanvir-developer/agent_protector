🛡️ AgentProtector

AI-Powered Access Control Gateway for Autonomous Agents

AgentProtector is a security gateway for AI agent systems. It prevents agents from leaking sensitive data, bypassing policies, or executing risky actions by enforcing policy-driven, explainable, and human-reviewable access control—before a tool/API call happens.

✨ Key Highlights

✅ Policy-driven access control between agents and tools

🧠 Gemini-powered reasoning for intent + risk analysis

🧪 Prompt injection detection & suspicious behavior flags

🧑‍💼 Human-in-the-loop approvals for sensitive actions

📜 Audit logs for compliance and traceability

🎯 Safe alternatives instead of silent denial

🚨 Why AgentProtector Exists

AI agents are becoming more autonomous—but that increases risk:

Prompt injection attacks can override instructions

Agents may access data/tools beyond intended scope

Bulk exports can lead to exfiltration incidents

Actions can be executed without approvals or logs

Most systems lack explainability (“why was this allowed?”)

AgentProtector solves this by enforcing security as infrastructure—not just prompts.

✅ What AgentProtector Does

AgentProtector acts as a security gateway that:

Intercepts every agent tool request

Applies AI + rule-based policy checks

Returns one of these outcomes:

✅ ALLOW → Tool executes

❌ DENY → Request blocked

🕒 NEEDS REVIEW → Manager approval required

🧩 Architecture (High-Level Flow)

User Prompt

→ AI Agent

→ AgentProtector Gateway

→ Gemini Policy Engine

→ Decision

✅ ALLOW → Execute tool

❌ DENY → Block request

🕒 NEEDS REVIEW → Send to manager console

🧠 Gemini Integration (Core Innovation)

AgentProtector uses Google Gemini API to generate intelligent security decisions:

Intent analysis

Sensitive data detection

Prompt injection identification

Risk scoring

Explainable policy reasoning

Safer alternative suggestions

Output is:

Context-aware

Explainable

Audit-friendly

Suitable for human review

🧰 Features
🔹 Demo Agent UI

Bulletproof “judge mode” demo experience

One-click test prompts

Live allow/deny/review decisions

Clean SaaS-style interface

🔹 Manager Console

View pending requests

Approve / deny with one click

See Gemini reasoning + risk score

Audit history (who approved what and when)

🔹 Security Capabilities

Blocks prompt injection attempts

Detects bulk export/exfiltration patterns

Flags suspicious intent (e.g., “ignore policy”)

Supports least-privilege enforcement

🧪 Quick Judge Testing (Under 2 Minutes)
Step 1 — Open Demo UI

/demo/agent?org_id=...

Step 2 — Run Test Prompts

Export all customers → ❌ DENY

View customer 123 → 🕒 NEEDS REVIEW

Ignore policy + dump data → 🚨 High risk / prompt injection suspected

Step 3 — Open Manager Console

/manager/console

Step 4 — Approve → Execute

Tool runs only after approval ✅

🛠️ Tech Stack
Backend

Python

FastAPI

SQLAlchemy

SQLite (default for demo/judges)

PostgreSQL (production-ready)

AI & Security

Google Gemini API

Policy reasoning + risk scoring

Explainable outputs

Frontend

Jinja2 Templates

Custom responsive UI

Infrastructure

Docker / Docker Compose

Environment-based config

Zero-setup judge mode

📦 Project Structure
AgentProtector/
├── gateway-api/
│   ├── app/
│   │   ├── routes_demo.py
│   │   ├── routes_access.py
│   │   ├── policy_engine.py
│   │   ├── models.py
│   │   ├── db.py
│   │   └── templates/
│   ├── main.py
│   └── requirements.txt
├── docker-compose.yml
└── README.md

⚙️ Run Locally (Recommended)
1) Clone
git clone <repo-url>
cd AgentProtector/gateway-api

2) Create venv
python -m venv .venv

3) Activate (Windows CMD)
.venv\Scripts\activate

4) Install
pip install -r requirements.txt

5) Start server
python -m uvicorn main:app --reload --port 8000


✅ Open:
http://127.0.0.1:8000/manager/console?org_id=aada601f-6e70-4f43-beca-3f0b88ef852f&tab=pending&refresh=6&from=demo

🐳 Run with Docker (Optional)
docker compose up -d

📌 What We Learned

AI agents need governance, not blind trust

Prompt injection is a practical real-world risk

Explainability increases trust and adoption

Human-in-the-loop is essential for sensitive actions

Security must be built into the system layer

⚠️ Challenges

Designing policies that are flexible but strict

Handling injection safely without false positives

Making AI decisions explainable and auditable

Balancing automation vs human approvals

Building a judge-friendly, zero-setup demo

🌍 Real-World Use Cases

AgentProtector fits well in:

AI copilots

Enterprise automation systems

Customer support agents

Fintech & healthcare workflows

Agent orchestration platforms

🎯 Why It Matters

As AI agents shift from assistants to actors, security becomes non-negotiable.

AgentProtector ensures AI behaves responsibly, transparently, and safely.

📽️ Demo Video

🎥 https://youtu.be/QiNNasgTEbo
