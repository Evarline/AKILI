# AKILI

AKILI is a conversational AI agent for Binance Spot market research and explanation.
The current application can interpret a user's message, fetch selected Binance Spot
market data, and explain that data. It is read-only: it does not place orders or
perform other financial actions.

## What AKILI Currently Does

- Provides a React + TypeScript chat interface.
- Sends chat messages to a FastAPI backend for structured interpretation.
- Answers conceptual questions and asks clarifying questions when needed.
- Retrieves one Binance Spot market reading when a market question requires it.
- Explains a ticker or recent candlestick data returned by Binance.
- Shows the latest fetched reading and its observation time in the UI.
- Persists users, conversations, messages, and agent runs in PostgreSQL.
- Validates model output against strict Pydantic schemas before returning it.
- Reports provider, database, Binance, and validation failures instead of fabricating a response.

The frontend starts with an empty conversation. Its conversation sidebar contains
only conversations created or opened during that browser session; there is no
conversation-listing API yet.

## Current Implementation

### Architecture

```text
User
  |
  v
React + TypeScript + Vite frontend
  |
  v
FastAPI backend
  |
  +--> Agent service and Pydantic contract validation
  |       |
  |       +--> Google Gemini HTTP provider
  |       |
  |       +--> Read-only market-data capability layer
  |                    |
  |                    v
  |              Binance Spot REST API
  |                    |
  |                    v
  |              Market facts returned to the agent and frontend
  |
  +--> Async SQLAlchemy -> PostgreSQL
```

The browser communicates with the AKILI backend only. In local development, Vite
proxies `/api`, `/health`, and `/.well-known` to the backend. Binance credentials
and LLM credentials remain server-side.

### Agent Workflow

The implemented workflow is deliberately small:

| Stage | State | What is implemented |
| --- | --- | --- |
| Understand | Implemented | The model classifies the message and extracts only stated parameters. |
| Research | Implemented | The backend may make one allow-listed ticker or kline read. |
| Explain | Implemented | A second model call can answer from the fetched Binance facts. |
| Plan | Not built | There is no trading plan or resolved order specification. |
| Validate | Not built | There is no order validation or policy workflow. |
| Approve | Not built | There is no user approval gate. |
| Execute | Not built | No write capability or order endpoint exists. |
| Verify | Not built | No execution-result verification exists. |

The model requests market data, but the model does not call Binance directly.
The backend validates the request, makes the read, labels the result as a Binance
fact, and supplies it to the explanation turn. Model output remains advisory and
is validated again before it is returned.

## Binance Integration

AKILI uses Binance Spot REST endpoints through `BinanceRESTProvider`.

### Public market data

The unauthenticated endpoints currently used are:

- `GET /api/v3/ticker/24hr?symbol=...` for the last price, 24-hour change, high,
  low, and volume.
- `GET /api/v3/klines?symbol=...&interval=...&limit=...` for candlesticks.

The supported kline intervals exposed by the agent are `1h`, `4h`, and `1d`.
Kline requests are bounded to 24 candles by the capability layer. Symbols are
normalized and validated before the request. These values come from Binance
responses; they are not seeded or hardcoded application data. Each result includes
an `observed_at` timestamp and is a point-in-time reading, not a live market feed.

### Authenticated Spot account read

The backend also implements a server-side, signed `GET /api/v3/account` request.
It uses `BINANCE_API_KEY` and `BINANCE_API_SECRET` to return a restricted Spot
account shape containing `account_type`, `can_trade`, and balances. The connection
check invokes this read and reports whether the configured credentials work.

This account path is implemented and covered by backend tests, but it requires
valid server-side credentials and the development identity mode described below
when called locally. The current chat capability allow-list does not expose
account data to the model, and the current frontend does not display balances.

No Binance write request is implemented. The backend contains no order, withdrawal,
Futures, Margin, leverage, or transfer capability.

### OAuth and MCP status

There is partial Binance OAuth client infrastructure: when explicitly enabled,
AKILI can publish a Client ID Metadata Document and redirect an authenticated
request to Binance using PKCE. The callback, authorization-code exchange, token
storage, and account access through that flow are not implemented.

The active data path is REST. AKILI does not currently make MCP client calls. The
MCP Python package is used by OAuth helper code, and MCP/OAuth configuration exists
for the incomplete authorization path; this should not be interpreted as a
working Binance MCP integration.

## AI/LLM Integration

The active configured provider is Google Gemini. The backend sends an HTTP request
to the Google Generative Language API's `generateContent` endpoint and requests a
JSON response matching the AKILI schema. The model name is supplied through
`LLM_MODEL`; it is not hardcoded. `LLM_API_KEY`, `LLM_TIMEOUT_SECONDS`, and
`LLM_MAX_OUTPUT_TOKENS` configure the request.

The response is parsed as JSON and validated locally. Provider errors, empty or
truncated responses, and schema violations become explicit API errors. Chat needs
`LLM_MODEL` and `LLM_API_KEY`; without them the backend returns a configuration
failure rather than using a fallback provider.

An Anthropic adapter and its dependency remain in the repository, but the current
settings and provider factory select Google. Anthropic is not the current runtime
provider.

## Technology Stack

- Frontend: React 19, TypeScript, Vite, Vitest, Testing Library
- Backend: Python, FastAPI, Uvicorn, Pydantic, pydantic-settings
- LLM: Google Gemini via direct HTTP with `httpx2`
- Binance: Binance Spot REST API
- Database: PostgreSQL via async SQLAlchemy and `asyncpg`
- Migrations: Alembic
- Local database development: Docker Compose
- Tests: pytest and Vitest

## API

The backend currently exposes these application routes:

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/health` | Process health and application version. Does not require the database. |
| `GET` | `/health/db` | Checks PostgreSQL with `SELECT 1`. |
| `POST` | `/api/v1/chat` | Creates or continues an owned conversation and returns a validated interpretation, with optional Binance market facts. |
| `GET` | `/api/v1/binance/connection` | Performs the configured signed Spot account read and returns safe connection metadata. |
| `GET` | `/api/v1/binance/account` | Returns the restricted authenticated Spot account shape. |
| `GET` | `/api/v1/binance/connect` | Optional OAuth start redirect; returns 404 unless Binance OAuth is enabled. |
| `GET` | `/.well-known/akili-mcp-client.json` | Optional public OAuth client metadata; returns 404 unless Binance OAuth is enabled. |

Protected routes require a current AKILI user. There is no login, session, or
production authentication implementation.

## Data & Persistence

PostgreSQL is required for database-backed routes; there is no in-memory database
fallback. SQLAlchemy uses its asynchronous PostgreSQL driver, and Alembic manages
the schema.

The current schema stores:

- Users with an origin and status.
- User-owned conversations.
- User and assistant message text.
- Agent runs, including status, provider/model, validated interpretation, token
  counts, and an error class when a run fails.
- Short-lived OAuth authorization requests, when the incomplete OAuth flow is used.

Raw model responses, credentials, and raw Binance payloads are not stored by the
agent run model. There is no persistence for proposals, approvals, orders, or
execution results.

## Security

- LLM and Binance credentials are backend environment configuration only.
- The frontend receives no API key, API secret, OAuth encryption key, or LLM key.
- Binance API secrets are used only to sign the authenticated account request.
- Model output is treated as untrusted input and rejected if it violates the
  contract.
- Market data is passed through an allow-listed capability layer and normalized
  into typed domain models.
- Development identity is a fixed seeded user and is permitted only with
  `APP_ENV=development` and a loopback backend host. It is not authentication.

## Current Limitations

- No Binance order execution or trade execution.
- No autonomous trading.
- No Futures, Margin, leverage, withdrawals, transfers, or other write actions.
- No approval or policy workflow.
- No plan or execution-verification workflow.
- No real user authentication, login, or sessions.
- No completed OAuth callback, token exchange, or OAuth-based Binance account connection.
- No operational Binance MCP client integration.
- No live streaming market feed, market overview, gainers/losers list, or portfolio view.
- Account reads exist behind signed REST credentials, but the chat agent does not
  use them and the frontend does not show balances.
- Chat depends on valid Gemini configuration and a reachable provider.

## Local Development

### Prerequisites

- Python 3.13 or a compatible supported Python version
- Node.js and npm
- Docker with Compose, for local PostgreSQL

### Configure the environment

From the repository root:

```bash
cp .env.example .env
```

Use local placeholder values like these. Never commit real credentials:

```dotenv
APP_ENV=development
BACKEND_HOST=127.0.0.1
AUTH_MODE=development_fixed_user
DEV_FIXED_USER_ID=<uuid>

POSTGRES_USER=akili
POSTGRES_PASSWORD=<local-password>
POSTGRES_DB=akili
POSTGRES_PORT=5433
DATABASE_URL=postgresql+asyncpg://akili:<url-encoded-password>@127.0.0.1:5433/akili
TEST_DATABASE_URL=postgresql+asyncpg://akili:<url-encoded-password>@127.0.0.1:5433/akili_test

LLM_PROVIDER=google
LLM_MODEL=<gemini-model-id>
LLM_API_KEY=<google-api-key>

BINANCE_API_KEY=<read-only-spot-api-key>
BINANCE_API_SECRET=<spot-api-secret>
BINANCE_USE_TESTNET=false
```

`AUTH_MODE=disabled` is the default and makes protected routes return `401`.
With development fixed-user mode enabled, create the user after PostgreSQL and
the schema are ready:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
docker compose up -d
cd backend
alembic upgrade head
python -m app.auth.seed
```

Create the separate test database once if running database tests:

```bash
createdb -h 127.0.0.1 -p 5433 -U akili akili_test
```

### Run the backend

From `backend/`:

```bash
uvicorn app.main:app --reload
```

Useful URLs:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/health/db`
- `http://127.0.0.1:8000/docs`

Example chat request:

```bash
curl -s http://127.0.0.1:8000/api/v1/chat \
  -H 'content-type: application/json' \
  -d '{"message":"What is the current price of BTC?"}'
```

### Run the frontend

From `frontend/`:

```bash
npm install
npm run dev
```

Vite serves the UI on its configured development port, normally
`http://127.0.0.1:5173`, and proxies backend paths to `http://127.0.0.1:8000`.
Set `AKILI_BACKEND_URL` when the backend is running elsewhere.

### Run tests

From the repository root:

```bash
pytest
cd frontend && npm test
```

The backend tests replace the LLM at the provider boundary for deterministic
tests. The optional provider integration test is explicitly enabled with:

```bash
AKILI_LLM_INTEGRATION=1 pytest tests/backend/test_llm_integration.py
```

## Project Status

The repository contains a runnable frontend and backend foundation for
conversation, market research, fact-grounded explanation, and read-only Spot
account connectivity. Identity is development-only, and trading-related stages
remain unimplemented.

## Future Work

Potential future capabilities, clearly separate from the current implementation,
include:

- Real user authentication and sessions.
- Completing the Binance OAuth callback and token exchange.
- Account-aware research in the agent workflow.
- A plan, validation, and explicit approval gate.
- Order execution followed by independent verification.
- Additional Binance integrations and voice interaction.
