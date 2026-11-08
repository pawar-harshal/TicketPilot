# TicketPilot

An agentic AI system that handles customer support tickets end-to-end — not just another FAQ chatbot.

**Live demo:** https://ticketpilot.duckdns.org

## What it does

Most "AI" customer support today just answers FAQs and hands off to a human the moment things get real. TicketPilot is built to actually act:

- Reads each incoming support request and checks the real order data behind it
- Decides the next action on its own, based on that data — not a canned response
- If the customer isn't satisfied, the same conversation continues as a RAG-backed chat until it's actually resolved
- Escalates to a human when it's unsure, and routes sensitive actions through manager approval before anything goes out
- Only has access to the specific tools and actions it's explicitly granted — no open-ended access to the system

## Architecture

```
TicketPilot/
├── backend/   FastAPI service — ticket/approval routes, agent orchestration, RAG pipeline
├── frontend/  React + Redux UI — customer ticket flow, manager approval queue
└── mysql/     Database schema and seed data
```

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, MySQL
- **AI / RAG:** LLM-based agent orchestration, Qdrant (vector search), prompt engineering
- **Frontend:** React, Redux
- **Auth:** JWT-based authentication, role-based access (customer / support manager)

## Running locally

Backend and frontend each have their own setup — see `backend/ticket_pilot_das/README.md` and `frontend/ticketpilot_ui/` for environment variables and run instructions.

## Demo data

The manager profile includes a "Reset Demo Data" action, and the backend also resets demo data automatically on a fixed interval, so the live demo stays usable for anyone trying it out.

---

Built as a personal project by [Harshal Pawar](https://github.com/pawar-harshal).
