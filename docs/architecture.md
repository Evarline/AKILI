# AKILI architecture

This document records the decisions the repository is built on. It is
specification, not implementation — nothing here has been coded yet.

## The agent loop

```
UNDERSTAND → SEARCH → REASON → ASK → EXPLAIN → PLAN
→ VALIDATE → PROPOSE → APPROVE → EXECUTE → VERIFY
```

The three stages that carry the safety guarantee are **VALIDATE** (backend, not the
model, decides whether something is permissible), **APPROVE** (a human, not the
model, authorizes it), and **VERIFY** (AKILI confirms what Binance actually did).

## Principles

1. The runtime AI model reasons and generates structured proposals.
2. The AI model is **not** the final authority for financial execution.
3. AKILI's backend owns validation and policy decisions.
4. A proposal is **not** the same thing as user authorization.
5. Explicit human approval is required before financial execution.
6. Binance performs the actual Spot execution.
7. AKILI verifies the result after execution.
8. PostgreSQL stores durable application data.
9. Redis is deferred — not part of Phase 1.
10. Sensitive credentials must never be placed into LLM prompts or context.
11. Binance integration must be isolated behind an integration/adapter boundary.
12. Binance Agent OS / MCP is the integration path. Tool names and API behavior
    are taken from official documentation — never invented or assumed.
13. The exact runtime model is selected later. No model name is hard-coded in this
    repository, so that nothing obsolete gets baked in.

## Stack

- **Backend:** Python + FastAPI
- **Frontend:** React + TypeScript + Vite
- **Database:** PostgreSQL, via SQLAlchemy, migrated with Alembic
- **Binance:** Binance Agent OS / MCP, behind an adapter boundary
- **Runtime AI:** configurable LLM provider
- **Infrastructure:** Docker / Docker Compose

## Phase 1 boundary

Phase 1 delivers the repository foundation only: layout, ignore rules, environment
placeholders, local PostgreSQL, and this documentation.

Explicitly **not** present yet: FastAPI routes, SQLAlchemy models, Alembic
migrations, agent code, MCP client code, Binance integration, approval logic,
trading logic, authentication, voice features, React components, trading UI, the
state machine, and the policy engine.
