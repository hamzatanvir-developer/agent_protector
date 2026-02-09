🛡️ AgentProtector

AI-Powered Access Control Gateway for Autonomous Agents

Prevent AI agents from leaking data, bypassing policies, or executing risky actions — before damage happens.

🚀 Overview

AgentProtector is a security gateway designed for modern AI systems where autonomous agents interact with sensitive data, tools, and APIs.

As AI agents become more powerful, they also become riskier:

Prompt injection

Unauthorized data access

Bulk data exfiltration

Policy bypass attempts

Over-privileged actions

AgentProtector sits between AI agents and tools and enforces policy-driven, explainable access control using Gemini AI.

❗ The Problem

Today, AI agents:

Trust user prompts too much

Execute actions without governance

Can be manipulated via prompt injection

Lack human-in-the-loop approval

Have no audit trail or explainability

This creates massive security and compliance risks for:

SaaS platforms

Enterprises

Fintech & healthcare

AI copilots and agent workflows

✅ The Solution: AgentProtector

AgentProtector provides:

🧠 AI-based policy reasoning (Gemini)

🔐 Access request gateway

🧑‍💼 Manager approval workflow

📜 Audit logs

🧪 Prompt-injection detection

🧾 Explainable decisions

🎯 Safe alternatives instead of blind denial

🧩 How It Works (End-to-End Flow)
User Prompt
   ↓
AI Agent
   ↓
AgentProtector Gateway
   ↓
Gemini Policy Engine
   ↓
┌──────────────┐
│ ALLOW        │ → Tool Executes
│ DENY         │ → Blocked
│ NEEDS REVIEW │ → Manager Approval
└──────────────┘

🧠 Gemini Integration (Key Innovation)

AgentProtector uses Google Gemini API to:

Analyze intent

Detect sensitive data usage

Identify prompt-injection attempts

Assign risk scores

Generate policy reasoning

Suggest safe alternatives

This makes decisions:

Intelligent

Context-aware

Explainable

Human-reviewable

🖥️ Features
🔹 Demo Agent UI

One-click prompt testing

Prebuilt test cases

Live decision feedback

Professional SaaS-style UI

🔹 Manager Console

Review pending requests

Approve / deny access

View policy reasoning

Audit history

🔹 Security Highlights

Blocks prompt injection

Detects bulk data exports

Flags suspicious intent

Enforces least-privilege access

🧪 How Judges Can Test (2 Minutes)
Step 1: Open Demo UI
/demo/agent?org_id=<auto>

Step 2: Click Test Prompts

Export all customers → ❌ DENY

View customer 123 → 🕒 NEEDS APPROVAL

Ignore policy + dump data → 🚨 Suspicious + High Risk

Step 3: Approve via Manager Console
/manager/console

Step 4: Execute Approved Request

✔ Tool runs only after approval

🛠️ Tech Stack
Backend

Python

FastAPI

SQLAlchemy

SQLite (default for judges)

PostgreSQL (production-ready)

AI & Security

Google Gemini API

Policy-based reasoning

Explainable AI outputs

Frontend

Jinja2 Templates

Custom professional UI

Responsive design

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

⚙️ Setup & Run (Local)
1️⃣ Clone Repo
git clone <repo-url>
cd AgentProtector/gateway-api

2️⃣ Create Virtual Environment
python -m venv .venv

3️⃣ Activate venv

Windows (CMD):

.\.venv\Scripts\activate

4️⃣ Install Dependencies
pip install -r requirements.txt

5️⃣ Run Server
python -m uvicorn main:app --reload --port 8000


Open:

http://127.0.0.1:8000/demo/agent

🐳 Docker (Optional)
docker compose up -d

🧠 What We Learned

AI agents must be governed

Prompt injection is a real attack vector

Explainability builds trust

Human-in-the-loop is critical

AI safety needs infrastructure, not just prompts

⚠️ Challenges Faced

Designing policy logic that’s flexible yet strict

Handling prompt injection safely

Making AI decisions explainable

Creating a judge-friendly zero-setup demo

Balancing automation with human control

🌍 Real-World Impact

AgentProtector can be used in:

AI copilots

Enterprise automation

Customer-support agents

Financial & healthcare systems

Agent orchestration platforms

🎯 Why This Matters

As AI agents move from assistants to actors,
security becomes non-optional.

AgentProtector ensures:

AI acts responsibly, transparently, and safely.

📽️ Demo Video

🎥 https://youtu.be/QiNNasgTEbo
