# AKILI

AKILI is a voice-first, human-in-the-loop AI agent for Binance Spot workflows.
It is a Binance Agent OS hackathon project.

## Human-in-the-loop architecture

An AI model reasons about the user's intent and produces a **structured proposal**.
It is not the authority that executes anything. AKILI's backend owns validation and
policy; a proposal is not user authorization; explicit human approval is required
before any financial execution. Binance performs the execution, and AKILI verifies
the result afterwards.

The agent loop:

```
UNDERSTAND → SEARCH → REASON → ASK → EXPLAIN → PLAN
→ VALIDATE → PROPOSE → APPROVE → EXECUTE → VERIFY
```

See [docs/architecture.md](docs/architecture.md) for the full set of architectural
principles this repository is held to, and
[docs/01-AGENT-CONTRACT.md](docs/01-AGENT-CONTRACT.md) for the normative agent
contract: state machine, intents, proposal schema, approval, and policy rules.

## Target stack

| Layer               | Choice                                  |
| ------------------- | --------------------------------------- |
| Backend             | Python + FastAPI                        |
| Frontend            | React + TypeScript + Vite               |
| Database            | PostgreSQL                              |
| ORM / migrations    | SQLAlchemy + Alembic                    |
| Binance integration | Binance Agent OS / MCP, behind an adapter |
| Runtime AI          | Configurable LLM provider               |
| Infrastructure      | Docker / Docker Compose                 |

Redis is **deferred** and deliberately absent.

## Status: Phase 5 — runtime AI integrated

- **Phase 1 (done):** repository foundation.
- **Phase 2 (done):** the agent contract in
  [docs/01-AGENT-CONTRACT.md](docs/01-AGENT-CONTRACT.md) — specification only.
- **Phase 3 (done):** a minimal FastAPI backend — typed configuration and a
  health endpoint.
- **Phase 4 (done):** PostgreSQL foundation — async SQLAlchemy, Alembic, and a
  database health check.
- **Phase 5 (done):** runtime AI. `POST /api/v1/chat` has a configurable LLM
  interpret a user message into a **validated, structured interpretation**
  (intent, clarification, extracted parameters). Conversations, messages, and
  agent runs are persisted. The model reasons only — it executes nothing, sees
  no credentials, and its output is treated as untrusted input.

- **Identity foundation (done, development only):** a `users` table and a
  `get_current_user` dependency. Every conversation is owned by one user and is
  invisible to every other user. The only identity mode implemented is a
  **development fixed user** that can only run with `APP_ENV=development` on a
  loopback host; the default mode is `disabled`, where every protected route
  answers 401. **This is not authentication** — it is the seam real
  authentication will plug into, so that the coming Binance connection is owned
  by a specific user from day one.

- **Phase 6.2 (done): AKILI is a recognisable OAuth client.** AKILI serves its
  own OAuth Client ID Metadata Document at `/.well-known/akili-mcp-client.json`
  and `GET /api/v1/binance/connect` sends the signed-in user to Binance's
  authorization endpoint with PKCE (S256), a persisted per-user `state`, and
  the MCP `resource` indicator. AKILI is an **independent** public client: it
  never uses any other application's Binance authorization. Off by default
  (`BINANCE_OAUTH_ENABLED=false`).

**Binance account access and MCP are intentionally NOT connected yet.** The
OAuth callback, token exchange, token storage, and the first MCP call are
Phase 6.3. The model is told it has no market, account, or symbol data and
must not invent any; the backend rejects output that claims otherwise. Also
still absent by design: real authentication (login, sessions), voice, approval
and policy logic, trading execution, Redis, and the UI.

## Repository layout

```
akili/
├── backend/            Python + FastAPI service
│   ├── requirements.txt
│   ├── alembic.ini         Alembic settings (no credentials — see alembic/env.py)
│   ├── alembic/versions/   Migrations
│   └── app/
│       ├── main.py         FastAPI app, health endpoints, error handlers
│       ├── api/chat.py     POST /api/v1/chat
│       ├── agent/          Contract schemas, system prompt, chat service
│       ├── auth/           Identity foundation (development fixed user; NOT authentication)
│       ├── oauth/          Provider-neutral OAuth 2.1 client pieces (discovery, PKCE, sealing)
│       ├── binance/        Binance adapter boundary (authorization start)
│       ├── llm/            Provider interface, Anthropic adapter, factory
│       ├── core/config.py  Typed settings from the root .env
│       └── db/             Engine/session, declarative base, ORM models
├── frontend/           React + TypeScript + Vite app (not initialized yet)
├── docs/
│   ├── architecture.md         Phase 1 principles and stack
│   └── 01-AGENT-CONTRACT.md    Phase 2 agent contract (normative)
├── tests/backend/      Backend tests
├── .env.example        Environment placeholders — copy to .env
├── .gitignore
├── docker-compose.yml  Local PostgreSQL for development
├── pyproject.toml      pytest configuration only
└── README.md
```

## Getting started

Setup runs from the repository root: there is a **single** virtual environment
at `.venv/` and a **single** `.env` file, both at the root. Each app is then run
from inside its own folder — the backend from `backend/`, the frontend from
`frontend/`.

### 1. Environment variables

```bash
cp .env.example .env         # then fill in local values
```

Set `POSTGRES_PASSWORD` to any local value, then put the same password into
`DATABASE_URL` and `TEST_DATABASE_URL`. They must use the `postgresql+asyncpg://`
scheme — the backend accesses the database asynchronously.

For the runtime AI, set `LLM_PROVIDER` (currently `anthropic`), `LLM_MODEL` (a
model ID from the provider's documentation — nothing is defaulted in code), and
`LLM_API_KEY`. These are read by the **backend only**. The key is handed to the
provider SDK client and is never part of a prompt, a log line, an error, or an
API response; the frontend never receives it. While `LLM_API_KEY` is blank, the
chat endpoint answers 503 "not configured" and everything else keeps working.

The backend also starts without `.env`: application settings have development
defaults, and the database URLs have **no** default. There is no silent fallback
to another database — a missing `DATABASE_URL` makes `/health/db` return 503 and
Alembic stop with a clear message, while `/health` keeps working. Secrets stay
server-side; the frontend never receives them.

### 2. Virtual environment

```bash
python3 -m venv .venv                    # only if .venv does not exist yet
source .venv/bin/activate                # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Start PostgreSQL

AKILI stores its durable data in PostgreSQL. For local development it runs in
Docker, bound to `127.0.0.1` only, with data kept in a named volume
(`akili_pgdata`) so it survives container restarts.

```bash
docker compose up -d           # start (first run pulls the image)
docker compose ps              # wait for "healthy"
docker compose stop            # stop, keeping the data
```

It listens on host port **5433**, not the usual 5432, so it never collides with
a PostgreSQL you may already have on this machine.

Create the test database once (it is separate from the development database, so
the test suite never touches development data):

```bash
createdb -h 127.0.0.1 -p 5433 -U akili akili_test
```

If Docker reports `Cannot connect to the Docker daemon`, your Docker CLI may be
pointed at a Docker Desktop socket that is not running while the system daemon
is. Check with `docker context ls`; `docker context use default` fixes it.

### 5. Run the backend development server

From inside the `backend/` folder:

```bash
cd backend
uvicorn app.main:app --reload
```

- Health check: <http://127.0.0.1:8000/health> → `{"status": "ok", "version": "0.1.0"}`
- Database check: <http://127.0.0.1:8000/health/db> → `{"status": "ok", "database": "reachable"}`
  (503 `Database unavailable` when PostgreSQL cannot be reached; never exposes
  connection details)
- Interactive API docs: <http://127.0.0.1:8000/docs>

The root `.env` is still picked up — the config resolves it from the source file
location, not the working directory.

**Enable the development identity** (needs PostgreSQL migrated). AKILI has no
login yet; in development, every request is served as one fixed user. This is
a development convenience with hard guards, **not authentication**:

```bash
# in the root .env
AUTH_MODE=development_fixed_user
DEV_FIXED_USER_ID=<a UUID you choose once, e.g. `uuidgen`>

cd backend
python -m app.auth.seed        # creates that user (idempotent)
```

With `AUTH_MODE=disabled` (the default) the chat endpoint answers
`401 Not authenticated`. The fixed-user mode refuses to start unless
`APP_ENV=development` and `BACKEND_HOST` is a loopback address, and no header
or body field can select a different user.

**Talk to the agent** (needs the identity above and an LLM key configured):

```bash
curl -s http://127.0.0.1:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message": "I have $20 and want to buy some Bitcoin."}'
```

```json
{
  "conversation_id": "…",
  "agent_run_id": "…",
  "response": {
    "intent": "BUY_SPOT",
    "requires_clarification": false,
    "message": "…",
    "question": null,
    "parameters": {"asset": "BTC", "quote_amount": "20", "quote_currency": "USD"},
    "provenance": "MODEL_INTERPRETATION"
  }
}
```

Pass the returned `conversation_id` in later requests to continue the
conversation. Conversations belong to the user who started them; continuing
someone else's is a 404, the same as an unknown id. Everything under
`response` is the model's interpretation — it is
a proposal for later phases to validate, never an action. Amounts are decimal
strings. The asset is reported as the user named it; resolving it to a Binance
symbol is a backend job for when Binance is connected. Failures are honest:
provider problems are 503, an answer that fails the contract is 502, never a
made-up 200.

**Connect AKILI to Binance (Phase 6.2, optional).** Binance must be able to
fetch AKILI's client metadata document over public HTTPS, so local development
needs a stable HTTPS tunnel to the backend. Then, in the root `.env`:

```bash
BINANCE_OAUTH_ENABLED=true
BINANCE_MCP_SERVER_URL=https://agent.binance.com/mcp/agentic
BINANCE_CIMD_URL=https://<your-tunnel-host>/.well-known/akili-mcp-client.json
BINANCE_REDIRECT_URI=https://<your-tunnel-host>/api/v1/binance/oauth/callback
OAUTH_ENCRYPTION_KEY=<python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
```

Opening `/api/v1/binance/connect` in a browser redirects to Binance's
authorization page. The callback that completes the flow does not exist yet;
this step only proves Binance recognises AKILI as a client.

### 6. Database migrations (Alembic)

Alembic is run from `backend/` and reads `DATABASE_URL` from the same settings
the application uses. `alembic.ini` deliberately contains no URL, so no
credentials are ever committed.

```bash
cd backend
alembic current                # show the applied revision (proves connectivity)
alembic upgrade head           # apply all migrations
```

Run `alembic upgrade head` once after cloning and after pulling new migrations.
The current schema holds users, conversations (owned by a user), messages, and
agent runs. Proposals, approvals, and executions are not modelled yet. If you
already have conversations from before the `users` migration, set
`DEV_FIXED_USER_ID` first: the migration assigns them to that development user
rather than deleting them, and refuses to run (changing nothing) if it cannot. New migrations are generated
with `alembic revision --autogenerate -m "describe the change"`, reviewed by
hand, and checked with `alembic check` before being applied.

### 7. Run the frontend development server

Not initialized yet. When it is, it runs the same way, from inside its own
folder (`cd frontend && npm run dev`), with `frontend/package.json` as its
manifest.

### 8. Run the tests

From the repository root:

```bash
pytest
```

The tests are deterministic and need no network access and no LLM key: the
model is replaced by a fake at the provider boundary, so the suite exercises
AKILI's own behaviour — validation, persistence, failure handling, secret
isolation. Database tests use `TEST_DATABASE_URL`, create their tables on the
test database and drop them afterwards, and are skipped when the URL is not
configured.

One test talks to the real provider and is **off by default**; it costs money:

```bash
AKILI_LLM_INTEGRATION=1 pytest tests/backend/test_llm_integration.py
```

See [backend/README.md](backend/README.md) for the backend layout and
[frontend/README.md](frontend/README.md) for what happens to the frontend next.
