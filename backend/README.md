# AKILI backend

Python + FastAPI service.

Scope so far: the application, typed configuration, async PostgreSQL access,
Alembic, health endpoints, the chat endpoint that has a configurable runtime
model interpret user messages, and a development-only identity foundation that
gives every conversation an owner. No Binance, MCP, real authentication,
approval, or execution logic yet.

## Layout

```
backend/
├── README.md
├── requirements.txt
├── alembic.ini                Alembic settings. Holds NO database URL.
├── alembic/
│   ├── env.py                 Reads DATABASE_URL from app settings; imports models
│   └── versions/              Migrations
└── app/
    ├── main.py                FastAPI app, health endpoints, exception handlers
    ├── api/
    │   ├── chat.py            POST /api/v1/chat — request/response models, routing
    │   ├── binance_oauth.py   GET /api/v1/binance/connect — redirect to Binance
    │   └── client_metadata.py GET /.well-known/akili-mcp-client.json — AKILI's OAuth client_id
    ├── agent/
    │   ├── schemas.py         The model↔AKILI contract (raw vs validated)
    │   ├── prompts.py         System instructions for the model
    │   └── service.py         Conversation, persistence, context, validation
    ├── auth/                  Identity foundation — DEVELOPMENT identity, not authentication
    │   ├── models.py          CurrentUser value object
    │   ├── principals.py      PrincipalResolver protocol; Disabled + DevelopmentFixedUser
    │   ├── dependencies.py    get_current_user (FastAPI dependency)
    │   ├── errors.py          NotAuthenticatedError → 401
    │   └── seed.py            `python -m app.auth.seed` creates the development user
    ├── llm/
    │   ├── base.py            Provider-neutral interface + error types
    │   ├── anthropic_provider.py
    │   └── factory.py         Builds the configured provider (FastAPI dependency)
    ├── oauth/                 Provider-neutral OAuth 2.1 client pieces (built on the mcp SDK)
    │   ├── discovery.py       PRM + ASM discovery → AuthorizationServer
    │   ├── pkce.py            S256 verifier/challenge, state
    │   ├── authorization.py   Authorization URL builder
    │   └── crypto.py          SecretBox: seal per-request secrets at rest (Fernet)
    ├── binance/               Binance adapter boundary
    │   └── authorization.py   begin_authorization(): persist owned request, return URL
    ├── core/
    │   └── config.py          Typed settings, loaded from the root .env
    └── db/
        ├── base.py            Declarative base
        ├── models.py          User, Conversation, Message, AgentRun, OAuthAuthorizationRequest
        └── session.py         Async engine, session factory, get_db dependency
```

`backend/` is the Python root, so the top-level package is `app`.

## Running

```bash
cd backend
uvicorn app.main:app --reload
```

PostgreSQL must be up (`docker compose up -d` at the repo root) and migrated
(`alembic upgrade head`, from this folder). Tests run from the repo root with
`pytest`.

## Configuration

`app/core/config.py` reads the single root `.env` via Pydantic Settings. Blank
values are treated as unset.

| Setting | Default | Notes |
|---|---|---|
| `APP_NAME`, `APP_ENV`, `APP_VERSION`, `DEBUG` | development-safe | |
| `BACKEND_HOST` | `127.0.0.1` | Declared listen address; checked by the identity guard |
| `AUTH_MODE` | `disabled` | `disabled` → protected routes 401; `development_fixed_user` → see Identity |
| `DEV_FIXED_USER_ID` | **none** | UUID of the development user; required only in that mode |
| `DATABASE_URL`, `TEST_DATABASE_URL` | **none** | `postgresql+asyncpg://…`; no fallback database |
| `LLM_PROVIDER` | `anthropic` | The only provider implemented |
| `LLM_MODEL` | **none** | Provider model ID; deliberately not defaulted in code |
| `LLM_API_KEY` | **none** | `SecretStr` — masked in repr and logs |
| `LLM_TIMEOUT_SECONDS` | `60` | |
| `LLM_MAX_OUTPUT_TOKENS` | `4096` | Covers the model's reasoning plus the JSON answer |
| `AGENT_HISTORY_MESSAGES` | `10` | Conversation window sent to the model |
| `BINANCE_OAUTH_ENABLED` | `false` | Off → CIMD document and connect route answer 404 |
| `BINANCE_MCP_SERVER_URL` | **none** | `https://agent.binance.com/mcp/agentic`; required when enabled |
| `BINANCE_CIMD_URL` | **none** | AKILI's `client_id`; https, must end in `/.well-known/akili-mcp-client.json` |
| `BINANCE_REDIRECT_URI` | **none** | https, or http on a loopback host in development |
| `OAUTH_ENCRYPTION_KEY` | **none** | `SecretStr` Fernet key; seals the PKCE verifier (later: tokens) at rest |

Missing database or LLM configuration fails at the point of use with a clear,
credential-free error that the app turns into a 503. `/health` never depends on
either.

## Identity (development only — not authentication)

AKILI has **no authentication yet**. What it has is the seam authentication will
plug into, so that user-owned data (conversations now, a Binance connection in a
later phase) is owned by a specific AKILI user from day one.

```
request ─► get_principal_resolver()          chosen once from AUTH_MODE
             ├─ DisabledResolver            → None            → 401 "Not authenticated"
             └─ DevelopmentFixedUserResolver→ Principal(DEV_FIXED_USER_ID)   (ignores the request)
         ─► get_current_user()
             ├─ load User; must exist and be ACTIVE          else 401 (same body, no enumeration)
             ├─ origin DEVELOPMENT outside APP_ENV=development → 503 + security log
             └─ CurrentUser(id)  ─► route ─► service ─► every query filtered by user_id
```

- **`users`** holds an opaque id, `status` (`ACTIVE`/`DISABLED`), `origin`
  (`DEVELOPMENT`/`PROVISIONED`) and timestamps. No credential, no login method.
- **`AUTH_MODE=disabled`** is the default. Every route that needs a user answers
  401; `/health` does not need one.
- **`AUTH_MODE=development_fixed_user`** serves every request as one user. It is
  only constructible with `APP_ENV=development`, a loopback `BACKEND_HOST`, and a
  `DEV_FIXED_USER_ID`; otherwise `Settings` raises and the process never starts.
  The request cannot choose a user: no header, cookie, or body field is read.
  Create the user once with `python -m app.auth.seed` (refuses outside that mode).
- **Ownership.** A conversation belongs to exactly one user. Continuing one you
  do not own is a 404 identical to an unknown id. Another user's conversation is
  never loaded, even briefly — ownership is in the `WHERE` clause.
- **Later.** Real authentication is another `PrincipalResolver` plus a
  `user_identities` table. `get_current_user`, `CurrentUser`, the services, and
  the ownership columns do not change.

## Binance: AKILI as its own OAuth client (Phase 6.2)

AKILI authorizes with Binance's Agentic MCP server as an **independent public
OAuth 2.1 client**. It has no client secret and no pre-registration; its
identity is the Client ID Metadata Document it serves at
`/.well-known/akili-mcp-client.json`, whose URL is the `client_id`. AKILI never
uses, reads, or proxies any other application's Binance authorization.

What exists so far is the *start* of the flow:

```
GET /api/v1/binance/connect   (404 while BINANCE_OAUTH_ENABLED=false)
  ├─ get_current_user → CurrentUser(u)                       401 if anonymous
  ├─ oauth.discovery: PRM at the MCP server origin → authorization server;
  │                   ASM there; issuer, resource, S256 and CIMD support checked
  ├─ oauth.pkce: verifier + S256 challenge; random state
  ├─ persist oauth_authorization_requests(state, user u, client_id, redirect_uri,
  │            resource, expected_issuer, verifier SEALED, expires in 10 min)
  └─ 302 → <authorization_endpoint>?response_type=code&client_id=<CIMD URL>
           &redirect_uri=…&state=…&code_challenge=…&code_challenge_method=S256
           &resource=https://agent.binance.com/mcp/agentic        (no scope)
```

`scope` is omitted on purpose: Binance publishes no `scopes_supported` and no
scope challenge, and the MCP authorization spec says to omit the parameter in
that case. The user picks Market data / Account on Binance's consent screen.

Not implemented yet, by design: the callback, the token exchange, token
storage, any MCP session, any account read. Those are Phase 6.3 and start only
after the redirect above has been shown to reach Binance's consent screen.

## The agent request path

```
POST /api/v1/chat  →  api/chat.py  →  agent/service.handle_chat
                                         ├─ get_current_user → CurrentUser (401 if none)
                                         ├─ find *this user's* / create owned Conversation, store user Message
                                         ├─ open AgentRun (RUNNING), commit
                                         ├─ build LLMRequest: system prompt + last N messages
                                         ├─ llm.factory → provider.complete()      (untrusted text back)
                                         ├─ parse_interpretation(): JSON → RawInterpretation → Interpretation
                                         └─ COMPLETED (+ assistant Message, interpretation JSON, tokens)
                                            or FAILED (+ error_class), re-raise → 502/503
```

**Contract.** `agent/schemas.py` defines two models. `RawInterpretation` is what
the model must return: a strict JSON schema (unknown keys rejected) with plain
types. `Interpretation` is what AKILI accepts after `Interpretation.from_raw`
normalises it — decimals as `Decimal`, tickers upper-cased — and enforces the
cross-field rules of the contract (a complete `BUY_SPOT` needs asset and amount,
clarification needs a question, parameters only on `BUY_SPOT`, and so on).
Anything that fails is rejected with a 502; nothing is repaired by guesswork.

**Provenance.** Every `Interpretation` carries `provenance:
MODEL_INTERPRETATION`. IDs are application-generated. There is no field in which
a Binance fact could travel, because there are none yet; the system prompt says
so explicitly, and a model that invents e.g. `btc_price` fails schema validation.

**Context.** The model sees the static system prompt and the most recent
`AGENT_HISTORY_MESSAGES` messages of *this* conversation, always starting at a
user turn. No settings, no other conversations, no credentials.

**Secrets.** `LLMRequest` has no field for a credential. The API key is a
constructor argument of the provider's SDK client. Tests plant canary secrets in
settings and the environment and assert they never appear in the request.

**Failures.** Provider exceptions are mapped in `llm/anthropic_provider.py` to
`LLMError` subclasses with an `error_class`; `main.py` maps those to 503
(timeout, rate limit, connection, provider error, not configured) or 502
(unusable answer, contract violation). The run is marked `FAILED` with the class.
Raw provider messages never reach the client.

## Database

Five tables (see `db/models.py`): `users` (opaque id, status, origin),
`conversations` (owned by a user, `ON DELETE CASCADE`), `messages` (role `user`
or `assistant`), `agent_runs` (status, intent, provider, model, error class,
validated interpretation as JSONB, token counts, timestamps), and
`oauth_authorization_requests` (one in-flight OAuth request: `state` as key,
owner, what was sent, expected issuer, PKCE verifier sealed with
`OAUTH_ENCRYPTION_KEY`, expiry; no tokens). Raw prompts and raw provider
responses are not stored.

The `users` migration (`a3c1d9e7f2b4`) gives pre-existing conversations an
owner rather than deleting them: in development, with `DEV_FIXED_USER_ID` set,
they are assigned to that user (created if needed). Otherwise it stops with a
clear message and changes nothing.

```bash
cd backend
alembic upgrade head
alembic check            # confirm models and migrations agree
```

## Python environment

- Python **3.13**; one virtual environment at the repository root, `.venv/`.
- Direct dependencies pinned in `backend/requirements.txt`. One LLM SDK
  (`anthropic`), the official MCP SDK (`mcp`, used so far only for its OAuth
  metadata models, discovery rules and PKCE), and `cryptography` for sealing
  secrets at rest — all on `httpx2` like the test client. No voice, Redis, or
  authentication packages.
