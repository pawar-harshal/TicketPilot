# ticketpilot_das

## Setup

```bash
# edit ticketpilot_das/data/config.ini directly with your own values
# (database credentials, jwt_secret, OpenRouter key) -- it's already
# there, there is no separate .example file to copy.

python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Config is organized like the reference auth-server's `configuration.py`:
`utils/Configuration.py` reads `data/config.ini` once, converts every
value to its proper type once, and exposes plain constants
(`Configuration.DATABASE_HOST`, `Configuration.MAX_TOOL_CALLS`, etc.) --
nothing else in the codebase re-reads the file or re-converts a value.

## Database

Either let the app create tables itself on startup (`auto_create_tables = true`
in config.ini, local dev only), or run the real SQL scripts by hand:

```bash
mysql -u root -p -e "CREATE DATABASE TicketPilot"
mysql -u root -p TicketPilot < ../sql/TicketPilot_structure.sql
mysql -u root -p TicketPilot < ../sql/TicketPilot_data.sql   # optional seed data
```

Seed data includes one support-manager login
(`harshal.pawar@quickcrave.com`) with a placeholder password hash --
generate a real one before using it:

```python
from ticketpilot_das.auth.db_operations.Auth import hash_password
print(hash_password("your-real-password"))
```
...then update that row's `U_PasswordHash` in MySQL.

## Qdrant

Runs in LOCAL/EMBEDDED mode by default -- no server, no Docker, no
account. It writes its index to the folder named in config.ini's
`qdrant_path`. Before semantic search returns anything, embed the seeded
articles once:

```bash
python scripts/EmbedKnowledgeBase.py
```

Run it again any time you add or edit knowledge-base articles.

## LLM / Embeddings

- **LLM**: OpenRouter (OpenAI-compatible API) -- set `llm_model` and
  `llm_base_url` in config.ini's GENERAL section, and `llm_api_key` in
  ENVIRONMENT.
- **Embeddings**: local `sentence-transformers` model (`embedding_model`
  in GENERAL) -- free, no API key, runs on CPU. OpenRouter has no
  embeddings endpoint, so this is the only path either way.

## Run

```bash
uvicorn ticketpilot_das.main:app --reload
```

Then open `http://localhost:8000/docs` for the interactive API docs.

## What's a stub vs. real

- Everything in `ticket_management`, `approval_engine`, `auth` is real,
  working logic against the models in `entity/DbModels.py`.
- The payment/wallet integration for an approved refund/credit is a
  stub (an AuditLog row, not a real payment call) -- see design doc's
  Open Questions re: payment-gateway integration (out of scope for v1).
