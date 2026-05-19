## Live Demo

| Endpoint | Description |
|---|---|
| [/health](https://web-production-1f27a.up.railway.app/health) | System status |
| [/demo](https://web-production-1f27a.up.railway.app/demo) | Full agent showcase |
| [/docs](https://web-production-1f27a.up.railway.app/docs) | Interactive API explorer |

# PharmAgent AI

**Intelligent Agent System for Pharmacy Management**
Target Infrastructure: DataVita Scottish Data Centre

---

## Overview

PharmAgent AI is a multi-agent system that augments independent pharmacy operations using Claude AI. Three specialist agents handle drug interaction safety, stock intelligence, and patient engagement — coordinated by a central Orchestrator Agent.

## Project Structure

pharmagent/
├── agents/
│   ├── interaction_safety_agent.py
│   ├── stock_intelligence_agent.py
│   ├── patient_engagement_agent.py
│   └── orchestrator_agent.py
├── tools/
│   └── pharmacy_tools.py
├── db/
│   ├── models.py
│   └── database.py
├── api/
│   └── main.py
├── tests/
│   └── test_agents.py
├── scripts/
│   └── seed.py
├── run_demo.py
└── requirements.txt

## Setup


1. Clone and enter the project
git clone https://github.com/Maricikam/pharmagent
cd pharmagent

2. Create a virtual environment
python -m venv venv
venv\Scripts\activate

3. Install dependencies
pip install -r requirements.txt

4. Add your Anthropic API key
Create a .env file and add:
ANTHROPIC_API_KEY=sk-ant-your-key-here

5. Seed the database
python scripts/seed.py

6. Run the demo
python run_demo.py

## Running Tests

pytest tests/ -v

## Running the API

uvicorn api.main:app --reload
API docs available at http://localhost:8000/docs

## Architecture

Tool Layer (deterministic): DB queries, stock checks, message sending, audit logging
Agent Layer (AI reasoning): Interaction Safety, Stock Intelligence, Patient Engagement
Orchestration Layer: OrchestratorAgent routes intent and synthesises results

## Agents

InteractionSafetyAgent — checks active prescriptions for drug interaction risks
StockIntelligenceAgent — reviews inventory, flags low/expiring stock, triggers reorders
PatientEngagementAgent — sends personalised SMS/email refill reminders
OrchestratorAgent — accepts plain English requests, coordinates sub-agents

## Data Privacy

All patient data remains within the configured database. In production deployment
at DataVita, data stays within Scottish data centres, satisfying NHS Scotland
GDPR requirements (NFR-01).
