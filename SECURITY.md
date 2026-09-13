# AKILI — Security Policy & Architecture

> **AKILI is designed to help people learn, understand, research, and make informed decisions across the Web3 and digital-asset ecosystem. Security is a core product requirement, not an afterthought.**

---

# 1. Security Philosophy

AKILI must be built on one fundamental principle:

> **The AI may reason, but it must never become the uncontrolled authority over a user's identity, data, wallet, or funds.**

AKILI will therefore use **defense in depth**.

No single security mechanism should be expected to protect the entire system.

```text
User
  ↓
Authentication
  ↓
Cloudflare / Edge Security
  ↓
API Security
  ↓
Authorization
  ↓
Application Validation
  ↓
AI Security
  ↓
Data Security
  ↓
Risk & Policy Controls
  ↓
Human Authorization
  ↓
Financial / Web3 Action
```

Every layer must remain capable of rejecting unsafe behavior even when another layer fails.

---

# 2. Security Goals

AKILI aims to protect:

* user accounts
* user identity
* authentication credentials
* API credentials
* learning history
* decision journals
* portfolio information
* market-related information
* private account information
* financial actions
* wallet-related actions
* system infrastructure
* AI capabilities
* third-party integrations

The primary security goals are:

### Confidentiality

Only authorized users and services should access protected information.

### Integrity

Data and actions must not be modified or executed without authorization.

### Availability

AKILI should remain available and resilient against abuse and infrastructure failures.

### Accountability

Sensitive actions should be attributable through appropriate audit records.

### Privacy

AKILI should minimize the personal and sensitive information it collects and stores.

---

# 3. Security by Design

Security must be considered before a feature is implemented.

Every significant new capability should follow:

```text
Threat Model
     ↓
Security Design
     ↓
Implementation
     ↓
Automated Tests
     ↓
Security Testing
     ↓
Review
     ↓
Controlled Release
     ↓
Monitoring
```

A feature is not considered complete merely because it works.

It must also be:

* understandable
* testable
* secure
* observable
* documented

---

# 4. Current Security Boundary

The current AKILI system is intentionally limited.

Current product capabilities are primarily:

* read-only market intelligence
* Binance Spot market data
* conversational explanations
* educational functionality
* trusted-resource discovery

Current conversational capabilities do **not** provide unrestricted financial execution.

This restricted boundary reduces the current attack surface.

The security architecture should become stricter as AKILI gains more capabilities.

---

# 5. Threat Model

AKILI must assume that attackers may attempt to:

* steal user credentials
* steal API credentials
* manipulate users
* exploit application vulnerabilities
* bypass authorization
* abuse APIs
* overwhelm infrastructure
* manipulate AI behavior
* inject malicious instructions
* exploit external content
* access another user's data
* execute unauthorized financial actions
* exploit third-party integrations
* abuse account recovery
* exploit dependencies
* submit malicious files or inputs
* cause excessive AI/API costs

AKILI must also assume that legitimate users can accidentally:

* expose secrets
* approve dangerous actions
* reuse passwords
* click phishing links
* connect unsafe applications
* misunderstand financial risks
* misconfigure API permissions

Security controls must account for both malicious and accidental behavior.

---

# 6. Authentication

Authentication must verify that a user is who they claim to be.

Long-term authentication should prioritize modern phishing-resistant mechanisms.

Preferred architecture:

```text
Passkey / WebAuthn
       ↓
Platform User Verification
       ↓
Device Biometric / PIN
       ↓
Authenticated Session
```

Where supported, users may use device-level:

* fingerprint authentication
* device PIN
* platform biometric verification
* hardware security keys

---

# 7. Biometric Security

AKILI should **not build or maintain its own biometric database** unless there is an extraordinary future requirement and a strong legal, privacy, and security justification.

AKILI should prefer platform authentication mechanisms such as:

* WebAuthn
* FIDO2
* passkeys

A fingerprint should remain under the control of the user's device.

AKILI should receive cryptographic proof of authentication rather than raw fingerprint data.

### Principle

> **Use biometrics to unlock secure credentials, not to create AKILI's biometric database.**

This reduces the consequences of a server compromise and minimizes sensitive data collection.

---

# 8. Step-Up Authentication

Authentication strength should increase with the sensitivity of an action.

### Low-risk

Examples:

* reading public educational material
* viewing public market information

Normal authentication may be sufficient.

### Medium-risk

Examples:

* viewing private account information
* changing account security settings

Additional authentication may be required.

### High-risk

Examples:

* connecting exchange credentials
* changing API permissions
* initiating financial actions

Require strong authentication and explicit confirmation.

### Critical actions

Potential future financial execution should require:

```text
Strong authentication
        ↓
Action review
        ↓
Risk validation
        ↓
Explicit human approval
        ↓
Execution authorization
```

---

# 9. Account Recovery

Account recovery must not become the weakest point in authentication.

Recovery mechanisms must be:

* secure
* rate limited
* auditable
* resistant to account takeover
* carefully designed around passkeys and authentication factors

Security-sensitive recovery events should trigger appropriate notifications and monitoring.

---

# 10. Authorization

Authentication answers:

> Who are you?

Authorization answers:

> What are you allowed to do?

AKILI must never assume that an authenticated user is automatically authorized to perform every operation.

Authorization should be enforced on the backend.

Examples:

```text
User A → User A's data
User B → User B's data
```

A user must never be able to access another user's:

* journal
* portfolio
* API connection
* learning history
* private information
* financial records

---

# 11. Least Privilege

Every component should receive only the permissions it needs.

This applies to:

* users
* backend services
* database users
* API keys
* Binance credentials
* cloud infrastructure
* third-party integrations
* AI tools

If a component only needs read access, it must not receive write access.

---

# 12. Cloudflare Security Layer

Cloudflare should form part of AKILI's edge-security architecture.

Potential protections include:

* TLS/HTTPS
* Web Application Firewall
* DDoS protection
* rate limiting
* bot protection
* abuse prevention
* edge-level filtering
* secure DNS
* traffic controls

Conceptually:

```text
Internet
   ↓
Cloudflare
   ↓
AKILI API
```

Cloudflare is **one security layer**, not the complete security model.

The backend must still validate every request.

---

# 13. API Security

All API endpoints must be designed with security in mind.

Controls should include:

* authentication where required
* authorization
* input validation
* schema validation
* rate limiting
* request-size limits
* safe error handling
* secure headers
* CORS restrictions
* request logging
* abuse detection

Never trust data simply because it came through the frontend.

---

# 14. Input Validation

All external input is untrusted.

Validate:

* types
* formats
* lengths
* ranges
* identifiers
* enumerations
* permissions
* business rules

Validation must occur on the backend.

Frontend validation improves user experience but is not a security boundary.

---

# 15. AI Security

The LLM must be treated as an **untrusted reasoning component**.

The model must not be trusted to:

* enforce authorization
* enforce financial limits
* protect secrets
* determine user identity
* decide whether an operation is permitted
* bypass application policies

The backend remains the final authority.

---

# 16. Prompt Injection

AKILI must defend against prompt injection.

Potential sources include:

* user messages
* web content
* educational resources
* documents
* market data
* external APIs
* third-party content

Rules:

1. External content is data, not instructions.
2. Retrieved content cannot override system policies.
3. Tool outputs must be validated.
4. Model-generated commands must be validated.
5. Sensitive actions require independent backend authorization.
6. The model cannot dynamically create capabilities.

---

# 17. Capability Allowlist

AKILI should use an explicit capability model.

For example:

```text
Allowed:
    get_ticker
    get_klines

Not automatically allowed:
    place_order
    withdraw
    change_security_settings
    access arbitrary account data
```

A model cannot invent:

```text
"execute_trade"
```

and cause the backend to execute it simply because the model generated that instruction.

Capabilities must exist explicitly in backend code.

---

# 18. Structured AI Output

Where the model produces machine-readable actions, the output must be:

1. parsed
2. schema validated
3. semantically validated
4. authorization checked
5. policy checked
6. risk checked where applicable

Malformed or unexpected output must be rejected.

---

# 19. Secrets Management

Never commit secrets to Git.

Examples include:

* Binance API keys
* Binance API secrets
* Gemini API keys
* database passwords
* session secrets
* encryption keys
* OAuth secrets
* access tokens

Use appropriate secret-management mechanisms for each environment.

Development may use environment variables.

Production should use a dedicated secrets-management solution where appropriate.

Secrets should be:

* rotated
* scoped
* protected
* monitored
* revoked when compromised

---

# 20. Binance API Security

When AKILI eventually accesses private Binance functionality, API credentials must be handled with extreme care.

Requirements:

* least-privilege permissions
* no unnecessary withdrawal permissions
* no credentials in frontend code
* no credentials sent to the LLM
* secure backend storage
* encryption where appropriate
* credential rotation
* revocation
* ownership verification
* connection monitoring
* audit logging

AKILI should request the minimum permissions required for a specific capability.

---

# 21. Financial Execution Security

Financial execution is a separate security boundary.

The architecture should eventually resemble:

```text
User Request
     ↓
LLM Interpretation
     ↓
Structured Trading Plan
     ↓
Backend Validation
     ↓
Authorization
     ↓
Risk Engine
     ↓
Policy Engine
     ↓
User Review
     ↓
Strong Authentication
     ↓
Explicit Approval
     ↓
Execution Service
     ↓
Exchange
     ↓
Execution Verification
     ↓
Audit Record
```

The AI must not have unrestricted authority to execute transactions.

---

# 22. Human-in-the-Loop

For consequential financial actions:

> **Human approval is mandatory.**

The user must see the action before it occurs.

The confirmation should clearly communicate relevant details such as:

* asset
* direction
* quantity
* price assumptions
* estimated fees
* risk
* stop-loss where applicable
* take-profit where applicable
* expiration
* consequences

The user must explicitly approve.

---

# 23. Approval Expiration

Approvals should not remain valid indefinitely.

For example:

```text
Trading Plan Created
        ↓
Approval Request
        ↓
Expiration Timer
        ↓
Approved
        ↓
Execute
```

If important conditions change, the system should require a new approval.

---

# 24. Double-Execution Protection

Financial systems must protect against duplicate actions.

Potential causes include:

* retries
* network failures
* double clicks
* race conditions
* duplicate requests
* service restarts

Use appropriate:

* idempotency keys
* unique identifiers
* state transitions
* database constraints
* execution reconciliation

---

# 25. Financial Precision

Financial calculations must use appropriate numerical representations.

Where exact financial arithmetic is required, use `Decimal` or an equivalent safe representation rather than relying blindly on binary floating-point arithmetic.

This applies to:

* quantities
* prices
* fees
* balances
* P&L
* risk calculations

---

# 26. Risk Engine

Before any future financial execution, an independent risk layer should evaluate the proposed action.

Potential controls:

* maximum position size
* maximum daily risk
* maximum daily loss
* maximum number of trades
* cooldown periods
* portfolio exposure
* concentration limits
* available balance
* minimum/maximum order size
* market conditions
* user-defined restrictions

The LLM should never be the final risk authority.

---

# 27. Kill Switch

AKILI should eventually provide an emergency mechanism capable of disabling sensitive operations.

A kill switch may be used when:

* an exchange integration behaves unexpectedly
* suspicious activity is detected
* credentials may be compromised
* a serious vulnerability is discovered
* an execution bug occurs
* abnormal trading behavior is detected

The system should fail safely.

---

# 28. Execution Verification

Submitting an action is not the same as successfully completing it.

After a future financial action:

```text
Request
 ↓
Exchange response
 ↓
Verify actual state
 ↓
Record result
```

AKILI should verify the resulting exchange state rather than assuming execution succeeded.

---

# 29. Database Security

Protect the PostgreSQL database through:

* strong credentials
* least privilege
* encrypted connections where appropriate
* restricted network access
* migrations
* backups
* backup testing
* input validation
* parameterized queries / ORM protections
* access controls

Sensitive data should not be exposed through error messages or debugging output.

---

# 30. User Data Isolation

Every user's private data must be isolated.

Application queries must enforce ownership.

Sensitive records include:

* account information
* learning history
* decision journals
* portfolio data
* trading history
* exchange connections

A user's identifier must never be trusted merely because it was supplied by the client.

---

# 31. Privacy by Design

AKILI should collect the minimum data necessary.

Avoid collecting sensitive information simply because it might be useful someday.

Principles:

```text
Collect less.
Store less.
Expose less.
Retain only when justified.
Delete when no longer necessary.
```

Biometric information is especially important to minimize.

---

# 32. Web3 Security

As AKILI expands beyond trading into broader Web3 functionality, it must account for risks such as:

* phishing
* wallet compromise
* private-key theft
* seed phrase theft
* malicious DApps
* malicious smart contracts
* malicious transaction signing
* token approval abuse
* fake tokens
* bridge risks
* signature phishing
* impersonation
* social engineering

AKILI should educate users about these risks before helping them interact with potentially dangerous systems.

---

# 33. Wallet Security

If wallet functionality is introduced in the future:

AKILI should never casually request:

* seed phrases
* private keys
* wallet passwords

The preferred model is to allow secure external wallet signing where appropriate.

Sensitive signing operations should clearly show:

* what is being signed
* which network
* which contract/application
* what assets may be affected
* what permissions are being granted

Users should understand the action before signing.

---

# 34. Learning Hub Security

The Learning Hub introduces another security concern:

**information quality.**

AKILI should not treat every website as authoritative.

Resources should be evaluated according to:

* source authority
* relevance
* freshness
* technical quality
* reputation
* provenance

Potential source hierarchy:

### Tier 1 — Official sources

Examples:

* Binance Academy
* Binance documentation
* Ethereum documentation
* Bitcoin documentation
* BNB Chain documentation
* official protocol documentation
* official security advisories

### Tier 2 — High-quality educational resources

Examples:

* universities
* established educational organizations
* reputable technical organizations

### Tier 3 — Research

Examples:

* academic papers
* technical papers
* protocol specifications
* security research

### Tier 4 — Community content

Community material may be useful but should be clearly identified as such.

---

# 35. Source Provenance

When AKILI recommends educational resources, it should eventually maintain metadata such as:

* title
* source
* URL
* topic
* authority level
* publication/update date where available
* retrieval date
* relevance

AKILI should never falsely imply that a source is official when it is not.

---

# 36. AI + Learning Safety

Educational explanations should distinguish between:

* established facts
* interpretations
* opinions
* predictions
* uncertainty
* financial advice

AKILI should not present educational content as guaranteed financial outcomes.

For example:

```text
Education:
"RSI is a momentum indicator..."

Analysis:
"BTC currently has an RSI of..."

Prediction:
"The market may..."

Uncertainty:
"This does not establish that price will rise..."
```

---

# 37. Logging and Auditability

Security-sensitive events should be logged appropriately.

Potential events include:

* login
* failed login
* authentication-factor changes
* passkey registration
* account recovery
* API connection
* credential changes
* permission changes
* sensitive data access
* financial approval
* execution
* security-policy violations
* suspicious activity

Logs must not contain secrets.

Never log:

* API secrets
* passwords
* private keys
* seed phrases
* authentication tokens

---

# 38. Monitoring

Production AKILI should monitor:

* authentication failures
* unusual login patterns
* API abuse
* rate-limit violations
* suspicious requests
* unusual exchange activity
* AI errors
* capability violations
* failed authorization
* infrastructure failures
* unusual financial behavior

Security monitoring should produce actionable alerts rather than unnecessary noise.

---

# 39. Rate Limiting and Abuse Prevention

Rate limits should protect:

* authentication endpoints
* account recovery
* AI requests
* market-data requests
* resource retrieval
* sensitive operations

Cloudflare can provide an important edge layer, while backend rate limits provide application-level protection.

---

# 40. AI Cost Protection

AI systems can be abused to create excessive costs.

AKILI should eventually implement:

* request limits
* token limits
* model-specific limits
* user quotas
* timeout controls
* retry limits
* anomaly detection

Never allow an uncontrolled loop to consume unlimited AI/API resources.

---

# 41. Dependency Security

Dependencies are part of the attack surface.

Practices should include:

* keep dependencies updated
* remove unused dependencies
* review security advisories
* pin versions where appropriate
* scan dependencies
* avoid unnecessary packages
* review new dependencies before introduction

Do not add a library merely because it is popular.

---

# 42. Frontend Security

The frontend must never be treated as a trusted environment.

Security controls must remain server-side.

Protect against:

* XSS
* unsafe HTML rendering
* token exposure
* insecure storage
* malicious redirects
* unsafe URL handling
* CSRF where applicable
* dependency vulnerabilities

The frontend should never contain private exchange credentials.

---

# 43. CORS

CORS should allow only trusted origins.

Development and production configurations must be separated.

Do not use unrestricted origins in production merely for convenience.

---

# 44. Secure Headers

Where appropriate, AKILI should implement security headers such as:

* Content-Security-Policy
* Strict-Transport-Security
* X-Content-Type-Options
* Referrer-Policy
* appropriate frame protections

Header configuration should be tested against the actual application's requirements.

---

# 45. Error Handling

Errors should provide useful information to legitimate users without exposing internal details.

Do not expose:

* stack traces in production
* database credentials
* API credentials
* internal secrets
* sensitive infrastructure information
* private user information

Detailed debugging information should remain in controlled development/observability systems.

---

# 46. File and Content Security

If AKILI eventually accepts:

* documents
* images
* URLs
* external content

those inputs must be treated as untrusted.

Controls may include:

* file-size limits
* content-type validation
* malware scanning where appropriate
* sandboxing
* safe parsing
* isolated processing
* URL validation
* SSRF protection

---

# 47. SSRF Protection

If AKILI eventually retrieves external URLs, the system must protect against Server-Side Request Forgery.

Do not allow arbitrary user-controlled URLs to access:

* internal services
* cloud metadata endpoints
* private network resources
* localhost services
* administrative interfaces

External fetching must be deliberately constrained.

---

# 48. Security Testing

Security must be tested continuously.

### Unit tests

Test security-sensitive functions.

### Integration tests

Test authentication, authorization and service boundaries.

### API tests

Test malicious and unauthorized requests.

### AI security tests

Test:

* prompt injection
* jailbreak attempts
* malicious tool outputs
* malformed structured output
* capability abuse
* data leakage

### Authentication tests

Test:

* login
* logout
* session expiration
* recovery
* passkeys
* step-up authentication
* authorization

### Financial security tests

Test:

* approval bypass
* duplicate execution
* race conditions
* risk-limit bypass
* invalid orders
* expired approvals
* unauthorized actions

---

# 49. Security Regression Tests

Every discovered security bug should produce a regression test where practical.

The goal is:

```text
Vulnerability discovered
        ↓
Fix implemented
        ↓
Regression test added
        ↓
Vulnerability cannot silently return
```

---

# 50. Incident Response

AKILI must eventually have a documented incident-response process.

Potential incidents include:

* credential exposure
* account takeover
* unauthorized financial action
* data breach
* infrastructure compromise
* malicious dependency
* AI capability bypass
* serious API vulnerability

Response should include:

```text
Detect
  ↓
Contain
  ↓
Investigate
  ↓
Remediate
  ↓
Rotate credentials where necessary
  ↓
Verify recovery
  ↓
Document
  ↓
Add preventative controls
```

---

# 51. Vulnerability Disclosure

Security vulnerabilities should be reported responsibly.

A future production deployment should provide a clear security contact and vulnerability-reporting process.

Security reports should be handled privately before public disclosure when appropriate.

---

# 52. Backups and Recovery

Important data should have appropriate backups.

Backups should be:

* protected
* access controlled
* encrypted where appropriate
* monitored
* tested through restoration procedures

A backup that has never been restored successfully should not be assumed to work.

---

# 53. Infrastructure Isolation

Sensitive services should be isolated where practical.

Potential boundaries include:

* frontend
* API
* AI service
* database
* exchange integration
* execution service
* background workers

Isolation should be introduced when justified by actual risk and complexity.

Do not create microservices merely for architectural appearance.

---

# 54. Production Security Principle

Production infrastructure should follow:

> **Secure by default.**

Examples:

* HTTPS
* restricted network access
* protected secrets
* least privilege
* strong authentication
* monitoring
* backups
* rate limiting
* safe error handling
* secure configuration

Development convenience must not accidentally become production configuration.

---

# 55. Security and the Roadmap

Security requirements evolve alongside AKILI.

### Learning Hub

Focus on:

* trustworthy sources
* malicious content
* source provenance
* safe external links

### Market Intelligence

Focus on:

* data integrity
* API security
* model-output validation

### User Accounts

Focus on:

* authentication
* authorization
* session security
* account recovery

### Binance Connections

Focus on:

* API credential security
* least privilege
* ownership
* revocation

### Paper Trading

Focus on:

* simulation integrity
* state consistency
* financial precision

### Real Execution

Focus on:

* authorization
* human approval
* strong authentication
* risk engine
* idempotency
* execution verification
* kill switch
* auditability

### Broader Web3

Focus on:

* wallet security
* signing
* smart contracts
* phishing
* protocol risks

Every expansion requires a new threat-model review.

---

# 56. Security Review Gate

A capability involving sensitive data, credentials, wallets or financial actions must not move to production without a security review.

The review should answer:

```text
What can go wrong?

Who can abuse it?

What happens if the AI is manipulated?

What happens if the user is compromised?

What happens if the external API fails?

What happens if the network fails?

What happens if the database is compromised?

What happens if credentials leak?

Can the action be reversed?

Can the action be stopped?

Can we detect abuse?

Can we audit what happened?
```

If these questions cannot be answered, the capability is not ready.

---

# 57. Security Maturity Levels

AKILI security should mature progressively.

## Level 1 — Read-only

* public market data
* Learning Hub
* trusted resources
* basic API protection
* AI guardrails

## Level 2 — User accounts

* secure authentication
* authorization
* session management
* account recovery

## Level 3 — Strong authentication

* passkeys
* WebAuthn
* platform biometrics
* step-up authentication

## Level 4 — Private data

* secure Binance connection
* least privilege
* credential protection
* auditability

## Level 5 — Paper trading

* execution simulation
* risk controls
* state integrity

## Level 6 — Real execution

* human authorization
* strong authentication
* risk engine
* idempotency
* execution verification
* kill switch

## Level 7 — Broader Web3

* wallet security
* transaction/signature safety
* smart-contract risk controls
* Web3 threat modeling

---

# 58. Security Is a Product Feature

Users should not have to understand the entire security architecture to benefit from it.

AKILI should make secure behavior easy.

Examples:

* secure login
* clear permissions
* understandable confirmations
* visible account connections
* obvious security settings
* clear warnings
* easy credential revocation
* transparent audit history

Good security should reduce user anxiety rather than create unnecessary complexity.

---

# 59. Security Education

Because AKILI is also a Learning Hub, security itself becomes something users can learn.

Potential lessons:

* password security
* passkeys
* phishing
* wallet security
* private keys
* seed phrases
* API keys
* authentication
* smart-contract risks
* transaction signing
* Web3 scams
* social engineering

AKILI should teach users:

> **How to protect themselves, not just how to use AKILI.**

---

# 60. Final Security Principle

AKILI should never optimize for the appearance of security.

It should optimize for **measurable security**.

That means:

```text
Threat model
    +
Secure architecture
    +
Least privilege
    +
Strong authentication
    +
Backend enforcement
    +
AI guardrails
    +
Testing
    +
Monitoring
    +
Human control
    +
Continuous improvement
```

---

# 61. North Star

AKILI should become a platform where users can confidently say:

> **“I trust this system to help me understand the ecosystem without giving the AI uncontrolled authority over me or my assets.”**

The goal is not to make AKILI impossible to attack.

That is unrealistic.

The goal is to make AKILI:

* difficult to abuse
* difficult to compromise
* difficult to misuse
* transparent when something goes wrong
* resilient when a component fails
* recoverable after incidents
* continuously improved

---

# 62. The Rule That Governs Everything

> **Every increase in AKILI's capability must be accompanied by an increase in its security maturity.**

More capability means more attack surface.

More access means more responsibility.

More automation means stronger authorization.

More financial power means stronger human control.

More users means stronger privacy and infrastructure.

More Web3 integration means deeper security engineering.

Therefore:

```text
Capability ↑
     ↓
Risk ↑
     ↓
Security Requirements ↑
     ↓
Testing ↑
     ↓
Monitoring ↑
     ↓
Maturity ↑
```

**AKILI will grow only as fast as its security architecture can responsibly support.**


        AKILI SECURITY CENTER

        Security Health
             92/100
              🔒

Authentication
  ✅ Email verified
  ✅ Passkey enabled
  ⚠️ Add backup authentication

Account Protection
  ✅ 2FA enabled
  ✅ Active sessions reviewed

Binance Connection
  ✅ Read-only permissions
  ✅ Credentials protected
  ⚠️ Review connection

Privacy
  ✅ Data controls reviewed

