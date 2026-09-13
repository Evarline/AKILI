# AKILI — Product & Engineering Roadmap

> **AKILI is an AI-assisted market intelligence, learning, and trading-decision support platform for the Web3 ecosystem.**
>
> AKILI begins with Binance Spot market intelligence, but Spot trading is only the beginning. The long-term vision is to build a secure, intelligent platform where people can understand markets, learn Web3 concepts, analyze information, improve their decision-making discipline, and eventually interact with financial systems under explicit human control.

---

# 1. Vision

AKILI exists to help people move from:

**“I don't understand what is happening.”**

to:

**“I understand what is happening, I know why it matters, I understand the risks, and I can make a more informed decision.”**

The long-term product cycle is:

```text
Learn
  ↓
Understand
  ↓
Observe
  ↓
Analyze
  ↓
Explain
  ↓
Decide
  ↓
Human Approval
  ↓
Optional Execution
  ↓
Verify
  ↓
Record
  ↓
Reflect
  ↓
Improve
```

AKILI should never be designed around the assumption that the AI is always right.

It must be capable of saying:

* BUY
* CONSIDER
* SELL / EXIT
* WAIT
* NO CLEAR SETUP
* INSUFFICIENT INFORMATION
* HIGH RISK
* I DON'T KNOW

A trustworthy system must be comfortable saying **“I don't know.”**

---

# 2. The Four Long-Term Pillars

AKILI will ultimately be built around four major pillars.

## Pillar 1 — Market Intelligence

Help users understand what is happening in markets.

Examples:

* current market data
* historical price data
* candlestick analysis
* technical indicators
* volatility
* market structure
* liquidity
* order types
* market dynamics
* risk/reward
* portfolio context
* cross-market analysis
* market research

---

## Pillar 2 — AKILI Learning Hub

AKILI should not only answer questions.

It should help users **learn.**

When AKILI explains a concept, it should identify opportunities for deeper learning and connect the user to trustworthy educational resources.

The first major educational integration is:

**Binance Academy.**

For example:

```text
User:
"What is slippage?"

AKILI:
"Slippage is the difference between the expected price
of a trade and the price at which it is actually executed..."

Learn more:
→ Binance Academy: Slippage
```

The same model should eventually work for:

* Bitcoin
* blockchain
* wallets
* private keys
* seed phrases
* gas fees
* smart contracts
* DeFi
* staking
* stablecoins
* tokenomics
* technical analysis
* RSI
* moving averages
* market makers
* market takers
* order types
* risk management
* trading psychology
* security
* Web3
* decentralized applications
* on-chain concepts

Binance Academy already provides educational material spanning crypto fundamentals, blockchain, trading, security, Web3 and related topics, making it an appropriate authoritative starting source for the Learning Hub.

### Learning principle

AKILI should:

```text
Explain first
     ↓
Give context
     ↓
Identify the concept
     ↓
Recommend trustworthy learning material
     ↓
Let the user go deeper
     ↓
Return to AKILI
```

AKILI should never simply dump a link instead of explaining.

---

## Pillar 3 — Trading Discipline

AKILI should help users understand their own behavior.

Eventually it should track:

* analyses requested
* trade ideas
* decisions made
* executed trades
* skipped trades
* reasons for decisions
* outcomes
* emotional/contextual notes
* overtrading
* repeated mistakes
* consistency
* risk violations
* adherence to trading plans

Possible future metrics:

* discipline score
* consistency score
* plan adherence
* average holding period
* overtrading indicators
* decision quality
* risk-management adherence

The goal is not to gamify trading.

The goal is to help users become more disciplined.

---

## Pillar 4 — Human-Controlled Execution

Execution is the final layer, not the foundation.

The AI may analyze.

The AI may recommend.

The AI may construct a plan.

But financial authority must remain outside the model.

Long-term architecture:

```text
AI reasoning
     ↓
Backend validation
     ↓
Risk engine
     ↓
Policy enforcement
     ↓
Human authorization
     ↓
Exchange execution
     ↓
Execution verification
     ↓
Audit trail
```

**No single AI response should be capable of moving user funds.**

---

# 3. Current Product

AKILI currently begins as a **read-only Binance Spot market intelligence agent.**

Current capabilities include:

### `get_ticker`

Provides current market/ticker information.

### `get_klines`

Provides historical candlestick data for market analysis.

### Binance connection

The backend can connect to Binance for market data.

### Current security boundary

The conversational interface does **not** currently provide unrestricted private account access or trading execution.

This restriction is intentional.

The current product should remain small enough to understand, test and secure properly.

---

# 4. Current Technology Stack

AKILI currently uses:

### Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* PostgreSQL
* Uvicorn
* pytest

### Frontend

* React
* TypeScript
* Vite
* Tailwind CSS where appropriate

### AI

* Google Gemini
* Direct API integration
* No unnecessary AI framework dependency

### Binance

* Binance Spot REST API
* Public market-data endpoints
* API-key based backend connection where required

### Infrastructure

* Docker
* Docker Compose
* Git
* GitHub

---

# 5. Engineering Principles

## 5.1 Build evidence, not hype

Every major capability should be supported by:

* tests
* measurable behavior
* logs
* documentation
* security controls
* evaluation

Do not claim that AKILI is:

* accurate
* profitable
* secure
* autonomous
* production-ready

without evidence.

---

## 5.2 Security before capability

A new capability must not be added simply because it is technically possible.

Before adding sensitive functionality:

```text
Threat model
     ↓
Design
     ↓
Implementation
     ↓
Tests
     ↓
Security review
     ↓
Evaluation
     ↓
Controlled release
```

---

## 5.3 The AI is never trusted by default

Model output is untrusted input.

The backend must validate:

* structure
* types
* allowed actions
* parameters
* permissions
* limits
* financial rules
* security policies

The LLM cannot dynamically create new system capabilities.

---

## 5.4 Master the current stack before adding more

Do not introduce technologies simply because they are popular.

Potential technologies such as:

* LangChain
* LlamaIndex
* Redis
* vector databases
* Kubernetes
* microservices
* multi-agent frameworks

should only be introduced when the actual system complexity justifies them.

---

# 6. Phase 1 — Master Binance Spot Market Intelligence

**Goal:** Make AKILI excellent at understanding Spot market data.

Build:

* ticker analysis
* candlestick analysis
* historical trends
* volume analysis
* volatility
* moving averages
* RSI
* MACD
* support/resistance
* trend detection
* market structure
* basic technical-analysis explanations
* market-condition classification

AKILI should be able to explain:

```text
What is happening?
Why might it be happening?
What evidence supports this?
What evidence contradicts it?
What information is missing?
What are the risks?
```

---

# 7. Phase 2 — Market Analysis Evaluation

Do not assume AKILI's analysis is good.

Build an evaluation framework.

Measure:

* directional accuracy
* false positives
* false negatives
* precision
* recall where appropriate
* calibration
* baseline comparisons
* historical performance
* confidence vs outcome
* performance under different market regimes

Evaluate:

* bullish markets
* bearish markets
* sideways markets
* high volatility
* low volatility

The objective is not:

> “Make the AI predict the market.”

The objective is:

> **Measure how useful the system actually is.**

---

# 8. Phase 3 — Structured Trading Decisions

Introduce structured decisions.

Possible output:

```text
Market:
BTCUSDT

Condition:
Bullish / Bearish / Neutral

Setup:
...

Evidence:
...

Risks:
...

Invalidation:
...

Decision:
WAIT / CONSIDER / BUY / SELL

Confidence:
...

Missing information:
...
```

The system must be allowed to choose **WAIT**.

---

# 9. Phase 4 — Trading Plans

Introduce a structured `TradingPlan`.

A trading plan should contain concepts such as:

* symbol
* direction
* entry
* invalidation
* stop-loss
* take-profit
* risk
* position size
* rationale
* market evidence
* timestamp
* expiration
* user approval state

Financial calculations must use appropriate precision, such as Python `Decimal`, rather than unsafe floating-point assumptions.

---

# 10. Phase 5 — User Accounts

Introduce proper AKILI identity.

Requirements:

* secure registration
* email verification
* secure authentication
* password hashing
* session management
* account recovery
* authorization
* account ownership
* audit logging
* rate limiting

Do not build authentication casually.

Authentication becomes part of the security architecture.

---

# 11. Phase 6 — High-Assurance Authentication

AKILI should eventually support modern, phishing-resistant authentication.

Potential authentication hierarchy:

```text
Passkey / WebAuthn
        ↓
Device verification
        ↓
Local biometric verification
        ↓
Step-up authentication
        ↓
Sensitive-action authorization
```

Where supported, users may authenticate using:

* fingerprint
* device face unlock
* device PIN
* hardware security keys
* passkeys

### Important privacy principle

AKILI should **not store raw facial images or raw biometric data merely to provide biometric authentication.**

The preferred model is to use platform authentication such as WebAuthn/passkeys, where the device performs local user verification and the server receives cryptographic proof rather than a raw face scan.

OWASP identifies FIDO2/WebAuthn/passkeys as strong phishing-resistant authentication mechanisms and notes that platform authenticators can use local biometrics while protecting authentication keys through device security mechanisms.

---

# 12. Phase 7 — Adaptive Security

Not every action should require the same security level.

Low-risk:

```text
Read public market information
        ↓
Normal authentication
```

Higher-risk:

```text
View private account information
        ↓
Step-up authentication
```

Very high-risk:

```text
Connect exchange credentials
        ↓
Strong authentication
        ↓
Device verification
        ↓
Explicit confirmation
```

Critical financial action:

```text
Create trading plan
        ↓
Risk validation
        ↓
Strong authentication
        ↓
Human approval
        ↓
Execution authorization
```

Security should become stronger as the consequences become greater.

---

# 13. Phase 8 — Binance User Connection

Allow users to securely connect their Binance accounts when the product is ready.

Requirements:

* least-privilege API permissions
* secure credential handling
* encrypted secrets
* credentials never exposed to frontend
* credentials never sent to the LLM
* ownership verification
* revocation
* connection health monitoring
* audit trail
* permission inspection

AKILI must never request permissions it does not need.

---

# 14. Phase 9 — Paper Trading

Before real execution:

Build a paper-trading environment.

Paper trading should reproduce:

* order creation
* order validation
* fills
* slippage assumptions
* fees
* balances
* P&L
* cancellations
* partial fills
* market conditions

No real funds.

Use this phase to test the entire execution architecture safely.

---

# 15. Phase 10 — Decision Journal

Create an AKILI Decision Journal.

Record:

```text
What AKILI saw
       ↓
What AKILI recommended
       ↓
What the user decided
       ↓
Why the user decided
       ↓
What happened afterward
```

This creates a dataset for understanding:

* decision quality
* human behavior
* AI recommendations
* discipline
* recurring mistakes

---

# 16. Phase 11 — Trading Discipline Dashboard

Create a dashboard showing:

### Activity

* analyses
* decisions
* trades
* skipped trades

### Discipline

* plan adherence
* risk violations
* overtrading
* cooldown violations
* impulsive decisions

### Outcomes

* wins
* losses
* drawdown
* risk-adjusted metrics
* decision outcomes

### Reflection

* what AKILI said
* what the user did
* what happened

The dashboard should help users learn from behavior rather than encourage reckless trading.

---

# 17. Phase 12 — Trade Outcome Evaluation

Compare:

```text
AI recommendation
        vs
User action
        vs
Actual market outcome
```

Evaluate:

* prediction quality
* decision quality
* execution quality
* timing
* risk management
* user adherence

This becomes part of AKILI's research foundation.

---

# 18. Phase 13 — Portfolio Intelligence

Introduce a portfolio dashboard.

Potential features:

* balances
* asset allocation
* performance
* realized P&L
* unrealized P&L
* exposure
* concentration
* risk
* historical decisions
* trade history

Eventually:

```text
Portfolio
+
Market Intelligence
+
Learning
+
Decision Journal
+
Discipline
```

becomes one connected system.

---

# 19. Phase 14 — Human-Approved Spot Execution

Only after:

* security review
* paper trading
* execution testing
* risk engine
* authorization
* idempotency
* audit logging
* kill switch
* monitoring
* strong authentication

should real Spot execution be considered.

Execution flow:

```text
User asks
    ↓
AI interprets
    ↓
Backend validates
    ↓
Trading plan generated
    ↓
Risk engine evaluates
    ↓
User sees exact action
    ↓
User explicitly approves
    ↓
Strong authentication
    ↓
Execution
    ↓
Exchange confirmation
    ↓
Verification
    ↓
Audit log
```

The AI never silently executes.

---

# 20. Phase 15 — Advanced Risk Controls

Introduce configurable controls such as:

* maximum risk
* maximum trades per day
* cooldown periods
* maximum position size
* maximum portfolio exposure
* maximum daily loss
* approval expiration
* duplicate-order protection
* emergency kill switch

The purpose is to prevent both AI mistakes and human impulsiveness.

---

# 21. Phase 16 — Beyond Spot

**Spot is AKILI's first market domain, not its permanent identity.**

When the Spot foundation becomes mature, AKILI can expand into other Binance products and market environments.

Potential future domains may include:

* Futures
* Margin
* additional Binance products
* broader market intelligence
* derivatives education
* advanced portfolio analysis

But every new domain must be treated as a separate engineering problem.

For each new market:

```text
Research
   ↓
Domain model
   ↓
Risk model
   ↓
Educational content
   ↓
Data integration
   ↓
Paper trading
   ↓
Evaluation
   ↓
Security review
   ↓
Controlled release
```

Never assume that knowledge or safety controls from Spot automatically transfer to Futures, Margin or another financial product.

---

# 22. Phase 17 — AKILI Learning Hub

The Learning Hub becomes a first-class product.

### Core experience

```text
User asks question
        ↓
AKILI explains
        ↓
Concept detected
        ↓
Relevant educational resources
        ↓
User learns
        ↓
User returns to AKILI
```

### Initial trusted source

Binance Academy.

### Learning categories

#### Crypto Fundamentals

* Bitcoin
* cryptocurrencies
* blockchain
* decentralization
* consensus
* wallets
* private keys
* seed phrases

#### Trading

* Spot
* order types
* market orders
* limit orders
* slippage
* spread
* liquidity
* technical analysis
* trading psychology

#### Risk Management

* position sizing
* stop-loss
* take-profit
* risk/reward
* diversification
* volatility

#### Web3

* smart contracts
* DApps
* DeFi
* staking
* tokenomics
* gas fees
* bridges
* on-chain activity

#### Security

* phishing
* wallet security
* private keys
* hardware wallets
* authentication
* scams
* smart-contract risks
* operational security

Binance Academy already covers beginner crypto concepts, security and broader blockchain/Web3 education, making it a useful initial knowledge ecosystem for AKILI's Learning Hub.

---

# 23. Learning Levels

AKILI should adapt explanations to the user's level.

### Beginner

Simple language.

Example:

> “A blockchain is a shared digital record that many computers maintain together.”

Then provide a beginner resource.

### Intermediate

Introduce mechanisms and tradeoffs.

### Advanced

Discuss:

* technical architecture
* cryptography
* protocol design
* economic incentives
* security assumptions
* failure modes

The goal is to help users progress rather than remain permanently dependent on AKILI.

---

# 24. Learning Progress

Eventually users should have a personal learning profile.

Potential areas:

```text
Crypto Fundamentals     ███████░░░
Blockchain               █████░░░░░
Trading                  ████░░░░░░
Technical Analysis       ███░░░░░░░
Risk Management          █████░░░░░
Web3                     ██░░░░░░░░
Security                 ██████░░░░
```

Track:

* concepts encountered
* resources opened
* quizzes completed
* topics understood
* learning paths
* weak areas

Future possibility:

**AKILI Learning Path**

```text
Crypto Beginner
      ↓
Blockchain Fundamentals
      ↓
Wallets & Security
      ↓
Spot Trading
      ↓
Technical Analysis
      ↓
Risk Management
      ↓
Web3
      ↓
DeFi
      ↓
Advanced Topics
```

---

# 25. Phase 18 — Web3 Knowledge Expansion

AKILI should eventually become a broader Web3 learning and intelligence platform.

Potential areas:

* blockchain ecosystems
* wallets
* DeFi
* NFTs
* DAOs
* smart contracts
* tokenomics
* staking
* governance
* on-chain analysis
* Web3 security
* decentralized applications
* blockchain development

The Learning Hub should distinguish between:

**education**

and

**financial advice/signals.**

Educational content must not be presented as guaranteed investment outcomes.

---

# 26. Phase 19 — External Knowledge

Eventually AKILI may need knowledge beyond Binance Academy.

Potential trusted sources:

* official blockchain documentation
* protocol documentation
* security advisories
* academic research
* reputable technical documentation
* official project documentation

Knowledge sources should have:

* provenance
* source URLs
* timestamps
* retrieval dates
* source ranking
* conflict handling

AKILI should tell the user where information came from.

---

# 27. Phase 20 — Voice

Eventually:

```text
User speaks
    ↓
AKILI understands
    ↓
AKILI researches
    ↓
AKILI explains
    ↓
User responds
```

Voice should be added only when it improves the product.

It should not be added simply because voice AI is fashionable.

---

# 28. Phase 21 — Observability

Production systems need visibility.

Implement:

* structured logging
* metrics
* traces
* request IDs
* AI request tracking
* model latency
* token/cost monitoring
* exchange API monitoring
* security-event monitoring
* error monitoring

Sensitive information must never be casually logged.

---

# 29. Phase 22 — Production Infrastructure

When the product genuinely needs it:

* production deployment
* database backups
* disaster recovery
* secrets management
* infrastructure hardening
* monitoring
* alerting
* rate limiting
* scaling
* incident response

Infrastructure should evolve with actual usage.

---

# 30. Phase 23 — Testing Strategy

AKILI must have multiple layers of testing.

### Unit tests

Test individual components.

### Integration tests

Test components working together.

### API tests

Test backend contracts.

### Frontend tests

Test critical user flows.

### AI evaluation

Test model interpretation and responses.

### Security tests

Test:

* authentication
* authorization
* prompt injection
* secret leakage
* malicious inputs
* session attacks
* rate limiting
* privilege escalation
* capability abuse

### Financial tests

Test:

* precision
* duplicate execution
* invalid orders
* race conditions
* approval bypass
* risk-limit bypass

### Regression tests

Every important bug becomes a test.

---

# 31. Phase 24 — Security Engineering

Security is a permanent product pillar.

The complete security strategy lives in:

`SECURITY.md`

Security principles include:

* defense in depth
* least privilege
* zero trust
* secure defaults
* explicit authorization
* strong authentication
* secrets protection
* data minimization
* auditability
* isolation
* monitoring
* incident response

AKILI should be designed under the assumption that:

```text
Users can make mistakes.
Attackers will try to manipulate the system.
LLMs can be manipulated.
External content can be malicious.
APIs can fail.
Dependencies can contain vulnerabilities.
Sessions can be stolen.
Credentials can leak.
```

The architecture must remain safe despite these realities.

---

# 32. High-Security Authentication Vision

The long-term security architecture may include:

### Passkeys

WebAuthn/FIDO2.

### Platform biometrics

Fingerprint or face verification performed by the user's device.

### Hardware security keys

For users requiring stronger authentication.

### Step-up authentication

Required for sensitive operations.

### Device management

Track trusted devices and suspicious sessions.

### Session protection

* short-lived sessions where appropriate
* token rotation
* revocation
* session anomaly detection

### Recovery

Account recovery must not become the weakest link.

---

# 33. Financial Security Boundary

The most important rule:

> **The AI may reason, but it must never become the authority over user funds.**

Future execution requires independent backend controls.

```text
LLM
 │
 │ suggestion
 ▼
Structured command
 │
 ▼
Validation
 │
 ▼
Authorization
 │
 ▼
Risk engine
 │
 ▼
Human approval
 │
 ▼
Strong authentication
 │
 ▼
Execution service
 │
 ▼
Exchange
```

The LLM should never receive unrestricted exchange credentials.

---

# 34. Prompt Injection Defense

AKILI must assume external content may attempt to manipulate the model.

Potential sources:

* market data
* web pages
* documents
* user messages
* project documentation
* external APIs

Rules:

* external content is data, not instructions
* tool output is schema validated
* model output is untrusted
* system policies cannot be overridden by retrieved content
* capabilities are enforced by backend code
* sensitive actions require independent authorization

---

# 35. Secrets Management

Never commit:

* API keys
* API secrets
* database passwords
* Gemini keys
* tokens
* session secrets
* private credentials

Use:

* environment variables during development
* proper secrets management in production
* secret rotation
* least privilege
* secret scanning
* Git history hygiene

Frontend code must never contain private exchange credentials.

---

# 36. Data Security

Protect:

* user accounts
* learning history
* trading history
* decision journals
* portfolio information
* API connections
* audit records

Principles:

```text
Collect only what is needed.
Store only what is needed.
Encrypt sensitive data.
Restrict access.
Log access to sensitive operations.
Delete data according to policy.
```

---

# 37. Privacy

AKILI should be designed around privacy by default.

Especially for authentication:

**Do not collect biometric data unnecessarily.**

Where device-level biometric authentication can solve the problem, prefer cryptographic authentication such as passkeys rather than building AKILI's own facial-recognition database.

Biometric information is particularly sensitive because compromised biometric characteristics cannot simply be changed like a password. OWASP explicitly notes this tradeoff.

---

# 38. Web3 Security

As AKILI expands into Web3, security must expand with it.

Potential risks include:

* phishing
* malicious DApps
* wallet compromise
* private-key exposure
* seed phrase theft
* malicious approvals
* smart-contract vulnerabilities
* bridge risks
* signature phishing
* fake tokens
* malicious transactions

AKILI should teach users about these risks before helping them interact with them.

---

# 39. Responsible AI

AKILI should never promise:

* guaranteed profits
* guaranteed predictions
* guaranteed security
* guaranteed outcomes

The product should clearly distinguish:

```text
Fact
Opinion
Analysis
Prediction
Risk
Uncertainty
Education
```

Users must understand which is which.

---

# 40. Explainability

Whenever AKILI gives an important recommendation, it should be able to explain:

* what information it used
* what indicators mattered
* what assumptions it made
* what contradicts the recommendation
* what risks exist
* what information is missing

The goal is not perfect mathematical explainability.

The goal is **transparent reasoning and evidence.**

---

# 41. AKILI Startup Path

AKILI should evolve gradually.

### Stage 1

Build.

### Stage 2

Use it personally.

### Stage 3

Test with trusted users.

### Stage 4

Observe real behavior.

### Stage 5

Improve.

### Stage 6

Validate the problem.

### Stage 7

Build retention.

### Stage 8

Define monetization.

### Stage 9

Scale.

Do not build a massive company before proving that people actually want the product.

---

# 42. Potential Future Business Model

Possible future models:

* free Learning Hub
* premium market intelligence
* advanced analytics
* decision journal
* portfolio analytics
* personalized learning
* advanced research
* professional tools
* team/institution plans

The business model should emerge from actual user value.

---

# 43. Final-Year Research Direction

AKILI can also become a serious academic research platform.

Possible research direction:

> **Design and Evaluation of an AI-Assisted Market Intelligence, Learning, and Trading-Decision Support System**

Potential research questions:

* How effectively can AI explain market information to beginners?
* Can structured AI explanations improve user understanding?
* Can decision journaling improve trading discipline?
* How accurately can the system classify market conditions?
* How should AI uncertainty be represented?
* What security architecture is appropriate for AI-assisted financial systems?
* How can human approval reduce the risk of autonomous financial actions?

The academic system must remain measurable and scientifically evaluated.

---

# 44. Open-Source Engineering

AKILI should eventually become a project that other engineers can understand.

Priorities:

* clean architecture
* meaningful commits
* documentation
* tests
* contribution guidelines
* security policy
* issue templates
* reproducible development environment

Do not optimize for looking sophisticated.

Optimize for being understandable.

---

# 45. What NOT to Build Yet

Do not rush into:

* autonomous trading
* unrestricted private account access
* multi-agent architecture
* microservices
* Kubernetes
* unnecessary vector databases
* unnecessary RAG infrastructure
* complex AI frameworks
* excessive abstractions
* dozens of Binance capabilities
* leverage
* high-risk financial automation
* custom biometric storage

A feature belongs in AKILI when the problem requires it.

Not because the technology exists.

---

# 46. Development Discipline

This roadmap is not a list of things to build simultaneously.

It is a sequence.

At any point:

```text
Choose one milestone.
        ↓
Understand the problem.
        ↓
Research.
        ↓
Design.
        ↓
Implement.
        ↓
Test.
        ↓
Secure.
        ↓
Document.
        ↓
Evaluate.
        ↓
Move forward.
```

Do not skip directly from:

> “This would be cool”

to

> “Let's build it.”

---

# 47. Learning Discipline

AKILI is also my engineering gym.

While building AKILI, deliberately become excellent at:

### Backend

* Python
* FastAPI
* HTTP
* REST APIs
* PostgreSQL
* SQL
* SQLAlchemy
* Alembic
* authentication
* authorization
* testing
* security
* Docker

### Frontend

* JavaScript
* TypeScript
* React
* Vite
* browser fundamentals
* API integration
* frontend security

### AI Engineering

* LLM APIs
* prompting
* structured outputs
* evaluation
* model limitations
* AI security
* agent architecture

### Web3

* blockchain fundamentals
* wallets
* cryptography
* smart contracts
* DeFi
* Web3 security
* market infrastructure

The objective is not to collect technologies.

The objective is to understand systems deeply enough to build them.

---

# 48. The Ultimate AKILI Vision

The long-term vision is bigger than:

> “An AI trading bot.”

AKILI should become a trusted place where someone can say:

> **“I want to understand this.”**

And AKILI helps them:

```text
Understand it
      ↓
Learn it
      ↓
Research it
      ↓
Analyze it
      ↓
Understand the risks
      ↓
Make a decision
      ↓
Record the decision
      ↓
Learn from the outcome
```

Someone should eventually be able to tell another person:

> **“There's this website called AKILI. Go create an account. If you don't understand something in crypto or Web3, start there.”**

That is a much bigger vision than a hackathon demo.

It means AKILI should eventually become:

**a learning platform,**

**a research assistant,**

**a market intelligence system,**

**a decision-support system,**

**a discipline companion,**

and potentially,

**a secure interface to financial and Web3 systems under human control.**

---

# 49. The North Star

AKILI should become a system people can trust not because it claims to know everything,

but because it:

* explains what it knows
* admits what it does not know
* shows its sources
* respects user control
* protects user data
* protects user credentials
* treats security as fundamental
* teaches instead of creating dependence
* measures its own performance
* learns from mistakes
* refuses unsafe actions
* requires human authorization for consequential actions

---

# 50. Final Rule

> **Do not build the biggest version of AKILI. Build the strongest version of the current version.**

Master the foundation.

Secure it.

Test it.

Measure it.

Learn.

Then expand.

```text
Spot
  ↓
Market Intelligence
  ↓
Evaluation
  ↓
Trading Decisions
  ↓
Learning Hub
  ↓
Decision Journal
  ↓
Discipline
  ↓
Portfolio Intelligence
  ↓
Paper Trading
  ↓
Secure Human-Approved Execution
  ↓
Broader Binance Markets
  ↓
Web3 Intelligence
  ↓
Web3 Learning
  ↓
A Secure AI Platform for the Digital Asset Ecosystem
```

**The roadmap can change.**

The engineering discipline should not.
