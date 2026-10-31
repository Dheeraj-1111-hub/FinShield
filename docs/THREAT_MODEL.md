# FINSHIELD Threat Model & Security Controls

**Document Version:** 1.0.0-rc1  
**Classification:** STRIDE & Financial Security Architecture  
**Status:** Frozen for Release

---

## 1. Assets & Trust Boundaries

FINSHIELD establishes strict trust perimeters separating the non-deterministic agent loop from the financial execution layer:

```text
┌─────────────────────────────────────────────────────────────┐
│ UNTRUSTED ZONE (Stochastic / Hallucination-Prone)           │
│  - Large Language Model (Qwen / Nemotron / Groq / OpenAI)   │
│  - Agent Reasoning Loop & Tool Selector                     │
│  - In-Context Agent Memory & Unverified Tool Outputs        │
└──────────────────────────────┬──────────────────────────────┘
                               │ Tool Requests (Unverified)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ TRUST BOUNDARY: THE ACTION GATE PERIMETER                   │
│  - Authoritative State Hydration (Ground-Truth DB Overrides)│
│  - Intent Alignment Scoring & Proximity Checks              │
│  - Policy Engine & Deterministic Hard Constraints           │
│  - Risk Scoring & Anomaly Detection                         │
└──────────────────────────────┬──────────────────────────────┘
                               │ Signed HMAC Decision Tokens
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ TRUSTED ZONE (Deterministic Execution)                      │
│  - Central Database (SQLite / PostgreSQL)                   │
│  - Commerce Engine (Carts, Orders, Inventory)               │
│  - Payment Service (Intents, Authorization, Capture)        │
│  - Hash-Chained Audit Ledger & Human Approval Queue         │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 Protected Assets
1. **User Capital & Credit:** Account balances, cards, and payment instruments.
2. **Intent & Authority Integrity:** Configured spending ceilings, approval thresholds, and intent scopes.
3. **Commerce Ground Truth:** Authentic merchant assignments, catalog pricing, and inventory state.
4. **Audit Trail Immutability:** Historical forensics, forensic causality, and cryptographic event chains.
5. **Multi-Tenant Data Scoping:** Isolation between independent workspace environments.

---

## 2. Threat Actors & Attack Vectors

| Threat Actor | Motivation | Capability |
| :--- | :--- | :--- |
| **Compromised LLM / Jailbroken Agent** | Execute unauthorized purchases; leak system data | Submits malicious tool calls, injects poisoned parameters |
| **Malicious External Tool / Webpage** | Indirect prompt injection; prompt hijacking | Injects instructions into agent tool outputs (`TOOL_OUTPUT_POISONING`) |
| **Rogue / Substituted Merchant** | Reroute payments; hijack transactions | Modifies destination payment merchant IDs (`TARGET_MANIPULATION`) |
| **Internal Malicious Tenant** | Read/write foreign workspace records | Submits API calls targeting foreign workspace resources |
| **Privileged Storage Adversary** | Conceal fraudulent transactions | Attempts direct SQL modifications of historical audit records |

---

## 3. Security Controls & Enforcement Points

### 3.1 Amount Escalation & Budget Evading
- **Threat:** Agent attempts to exceed its delegated monetary limit by modifying quantities or chaining unauthorized orders.
- **Enforcement:** [`ActionGateService.evaluate`](file:///c:/Users/Sai%20Dheeraj/OneDrive/Desktop/Main_Projects/finshield/backend/app/services/action_gate_service.py) recalculates total hydrated monetary value against the active `DelegatedAuthority` limit. Transactions exceeding the ceiling trigger an immediate hard `BLOCK` with `AUTHORITY_EXCEEDED`. Downstream payment creation checks the HMAC-signed token amount.

### 3.2 Target Manipulation & Parameter Spoofing
- **Threat:** Agent or malicious tool returns spoofed prices, altered item categories, or fraudulent merchant IDs.
- **Enforcement:** **Authoritative State Hydration**. The Agent Runtime discards all agent-reported pricing, merchant, and product metadata. Ground-truth values are reconstituted from the trusted database before the Action Gate evaluates the action.

### 3.3 Prompt Injection & Intent Misalignment
- **Threat:** Adversarial prompt override via user or tool output instructs the agent to ignore user spending limits.
- **Enforcement:** The `AlignmentEngine` evaluates structured constraints independently of LLM reasoning. Even if the LLM declares an instruction overridden, the deterministic Action Gate halts execution with `INTENT_MISALIGNED`.

### 3.4 Direct Action Gate Bypass
- **Threat:** Agent or compromised client invokes internal payment or commerce APIs directly to evade gate evaluation.
- **Enforcement:** All mutating endpoints in `payment_service` and `CommerceService` require an `ExecutionContext` carrying a cryptographically valid `signed_decision_token`. Direct calls lacking a valid token or carrying forged signatures are rejected with `403 Forbidden`.

### 3.5 Replay Attacks & Stale Token Substitution
- **Threat:** An attacker re-uses a valid historical decision token or spent human approval for a new transaction.
- **Enforcement:** 
  - Decision tokens contain a cryptographically random `nonce` with a 5-minute TTL. Nonces are recorded and atomically consumed on first use.
  - Human approvals transition to `CONSUMED` upon first execution. Revalidation of a consumed approval is rejected by the Action Gate (`APPROVAL_INVALID_STATE`) and payment service.

### 3.6 Payment Idempotency Tampering
- **Threat:** Replaying identical transaction keys with altered amounts to force double-debiting or state confusion.
- **Enforcement:** `payment_service.create_payment_intent` caches idempotency keys with payload digests. Identical retries return existing payment records; key re-use against modified payloads yields `409 Conflict`.

### 3.7 Audit Log Tampering
- **Threat:** Altering historical audit events to conceal fraudulent transactions.
- **Enforcement:** 
  - Storage-level triggers (`prevent_audit_events_update`, `prevent_audit_events_delete`) abort direct SQL modifications.
  - Audit records maintain a SHA-256 hash chain verifying chronological ledger integrity.

---

## 4. Residual Risks & Unverified Assumptions

### 4.1 Trusted Backend Assumption
FINSHIELD assumes that the host operating system, database engine, and Action Gate runtime process are secure. If an attacker achieves arbitrary code execution on the backend host, they can bypass application-level controls.

### 4.2 Multi-Tenant Workspace Isolation Scope
As documented in the Security Verification Report, the Security Lab scenario for `workspace-isolation` tested SQL clause filtering against an unpersisted foreign workspace string under a single user context. Multi-user cross-tenant isolation is enforced at the route and service level via dependency injection (`RequireWorkspaceRole`), but true cross-tenant adversarial isolation remains an area for full cluster testing.

### 4.3 External Payment Processor Boundaries
FINSHIELD contains transactions up to the payment gateway boundary. Security risks originating within third-party payment gateways, bank settlement networks, or physical card networks are external and out of scope.

### 4.4 Non-Financial Side Effects
FINSHIELD enforces financial authorization boundaries (money, cart, orders, payments). It does not prevent an LLM from hallucinating conversational text or generating unaligned conversational outputs that do not touch financial execution APIs.

