# FINSHIELD 🛡️

**FINSHIELD** is an authoritative, deterministic execution-control plane that secures autonomous agent operations across financial boundaries.

---

## 1. Executive Summary

Autonomous AI agents executing commercial transactions introduce critical failure modes: prompt injection, semantic drift, parameter manipulation, and unconstrained financial delegation. Treating Large Language Model (LLM) reasoning as an authorization layer is fundamentally flawed.

**FINSHIELD enforces an external, fail-closed policy enforcement boundary** between autonomous agents and commercial execution endpoints (carts, orders, payment gateways). Every financial state transition is gated by cryptographically signed HMAC-SHA256 action tokens, strict delegated authority boundaries, human-in-the-loop review thresholds, and immutable hash-chained audit logging.

```
+-----------------------------------------------------------------------------------+
| UNTRUSTED ZONE                                                                    |
| Autonomous Agent (LLM: Qwen / Nemotron / Claude via LangGraph)                   |
| Intent: "Buy laptop up to ₹70,000"                                               |
+-----------------------------------------------------------------------------------+
                                         │
                         Tool Call Request (order_id, amount)
                                         ▼
+-----------------------------------------------------------------------------------+
| ACTION GATE CONTROL PLANE (Deterministic Policy Engine)                           |
| 1. Authoritative Database Hydration (DB State != LLM Claims)                      |
| 2. Intent & Authority Boundary Check (Hard limits, category constraints)         |
| 3. Approval Revalidation (PENDING -> APPROVED -> CONSUMED)                        |
| 4. Cryptographic HMAC-SHA256 Action Token Generation                             |
| 5. Hash-Chained Append-Only Audit Logging (SHA-256 with SQLite Trigger Guard)     |
+-----------------------------------------------------------------------------------+
                                         │
                              Signed Action Token
                                         ▼
+-----------------------------------------------------------------------------------+
| TRUSTED EXECUTION ZONE                                                            |
| 1. Token Signature Verification                                                   |
| 2. Payment Gateway (Two-Phase Capture, Idempotency-Key Enforced)                  |
| 3. Final Order State Transition (PENDING_PAYMENT -> COMPLETED)                    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Security Invariants

1. **Untrusted Agent Boundary:** Agent reasoning, chat output, or tool arguments are never treated as trusted authorization tokens.
2. **Authoritative Hydration:** The Action Gate ignores agent-supplied price or category parameters, fetching actual state directly from authoritative database records.
3. **Formal Decision Gate:**
   $$\text{Decision } D = \mathcal{G}(I, A, P, R, C)$$
   Where $I$ is user intent, $A$ is agent authority, $P$ is system policy, $R$ is human approval record, and $C$ is execution context.
4. **Cryptographic Action Tokens:** Downstream execution endpoints (orders, payments) strictly require an HMAC-SHA256 token signed by the Gate secret with a 300-second TTL.
5. **Two-Phase Payment & Database Idempotency:** Payments require authoritative state validation and enforce unique idempotency keys at the database schema level.
6. **Immutable Audit Trail:** Every decision, order change, and payment capture is recorded in a forward SHA-256 hash chain protected by SQLite triggers preventing row mutation or deletion.

---

## 3. Verified Security Verification Lab

The Security Lab subjects FINSHIELD to automated adversarial exploits, policy-bypass attacks, and state-manipulation scenarios. 

### Empirical Verification Results

| Scenario ID | Attack Vector / Invariant Under Test | Engine Assertions | Verified Status |
|:---|:---|:---:|:---:|
| `authority-escalation` | Agent attempts to purchase an item exceeding delegated single-transaction limit (₹5,000 threshold vs ₹12,000 item). | 9 / 9 | **PASSED** |
| `prompt-injection-authority` | Injected prompt payload attempts to manipulate agent into bypassing spending boundaries and calling payment directly. | 11 / 11 | **PASSED** |
| `gate-bypass-attempt` | Adversary attempts direct API calls to payment capture without a gate token or with a forged HMAC token. | 8 / 8 | **PASSED** |
| `payment-idempotency` | Adversary replays identical payment capture requests and attempts key collision across different orders. | 8 / 8 | **PASSED** |
| `workspace-isolation` | Multi-tenant access controls across workspace boundaries. *(See limitation note below)* | 7 / 7 | **INCONCLUSIVE** |
| `audit-integrity-tamper` | Direct adversarial attempt to alter or delete historical audit log rows. SQLite triggers block modification. | 7 / 7 | **PASSED** |
| `failure-safety` | Action Gate behavior when dependencies (database/cache/LLM) throw unhandled exceptions. Fails closed deterministically. | 7 / 7 | **PASSED** |
| `approval-replay` | Adversary captures an `APPROVED` review token and attempts to execute multiple purchases using the same approval. | 9 / 9 | **PASSED** |

> **Limitations & Scope Disclosures:**
> - **Workspace Isolation:** Marked **INCONCLUSIVE** because the current test fixture evaluates access using a single authenticated user session against synthetic workspace IDs. While engine-level checks passed (7/7), true multi-tenant separation requires verification across distinct authenticated identities.
> - **Currency Tampering:** Verified via unit and regression test suites (`backend/tests/test_commerce.py`); it is not currently registered as a separate automated scenario in the Security Lab suite.

For complete execution logs, run IDs, assertion traces, and forensic details, see the [Security Verification Report](docs/SECURITY_VERIFICATION_REPORT.md).

---

## 4. Documentation Suite

- 📐 [**System Architecture**](docs/ARCHITECTURE.md) – Subsystem design, state machines, token lifecycle, and mathematical formulation.
- 🛡️ [**Threat Model**](docs/THREAT_MODEL.md) – Trust boundaries, adversarial capabilities, STRIDE-aligned mitigations, and residual risks.
- 🧪 [**Security Verification Report**](docs/SECURITY_VERIFICATION_REPORT.md) – Full verification audit, assertion matrices, Run IDs, and limitation analysis.
- 🚀 [**Deployment & Setup Guide**](docs/DEPLOYMENT.md) – Step-by-step local setup, Docker Compose configuration, environment variables, and troubleshooting.
- 🎬 [**Demonstration Guide**](docs/DEMO_GUIDE.md) – Reproducible 7-step walkthrough for technical reviews and live demonstrations.
- 📋 [**API Contracts**](docs/api_contracts.md) – OpenAPI specifications, request/response models, and error envelopes.
- 🗄️ [**Database Schema**](docs/database_schema.md) – Relational entity-relationship design, foreign keys, and trigger definitions.

---

## 5. Technology Stack

- **Backend:**
  - Python 3.11+ / FastAPI (Asynchronous REST API)
  - SQLAlchemy 2.0 (ORM) with SQLite (WAL Mode & Immutable Triggers)
  - Pydantic v2 (Input validation & schema contracts)
  - LangGraph & LangChain (Deterministic agent execution harnesses)
  - Cryptography / hashlib (HMAC-SHA256 token signing and hash-chain audit)
- **Frontend:**
  - React 18 with TypeScript & Vite
  - Tailwind CSS & Radix UI / shadcn/ui
  - TanStack Query v5 (Data fetching and cache synchronization)
  - Lucide React (Visual telemetry)
- **Security & Reliability:**
  - Double-capture prevention via unique DB constraints (`idempotency_key`)
  - Fail-closed exception handlers on all execution boundaries
  - Append-only hash-chained audit log with tamper detection verification

---

## 6. Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Git

### 1. Backend Setup
```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API and Swagger UI will be available at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The web dashboard will be available at `http://localhost:5173`.

For detailed setup instructions, Docker Compose deployment, and environment variable references, consult [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## 7. Interactive Demo Workflow

To observe FINSHIELD's policy enforcement in real time:

1. **Access Dashboard:** Open `http://localhost:5173` and log in (`testuser` / `testpassword`).
2. **Configure Authority:** In the Agents tab, select an agent (e.g., *Shopping Agent QA*) with an explicit spending limit (e.g., ₹5,000) and approved categories.
3. **Execute Bounded Purchase:** Execute a purchase under ₹5,000. Observe instant `ALLOW` decision and automatic order completion.
4. **Trigger Approval Gate:** Request a purchase over ₹5,000 (e.g., ₹12,000). Observe immediate `REQUIRE_APPROVAL` intercept; order remains in `PENDING_APPROVAL`.
5. **Human Approval Review:** Review the pending transaction under the Approvals tab. Approve or reject with structured rationale.
6. **Token Capture & Replay Guard:** Finalize payment capture. Re-submitting the same token or approval ID triggers deterministic rejection.
7. **Inspect Audit Chain:** Review the Audit Log tab to verify cryptographic hash-chain continuity and immutable SQLite trigger protection.

For full demonstration instructions, refer to the [Demonstration Guide](docs/DEMO_GUIDE.md).

---

## 8. Limitations & Honest Disclosures

FINSHIELD is an engineering prototype and research demonstrator designed to validate deterministic execution controls for AI commerce. Current limitations include:
- **Local Storage Triggers:** Audit log immutability relies on SQLite triggers on the local filesystem. Production deployment requires distributed append-only storage, WORM drives, or hardware security modules (HSMs).
- **Workspace Isolation Scope:** Cross-workspace leakage prevention has been empirically tested using synthetic headers within single-user contexts, but requires multi-tenant isolation testing before multi-organization production use.
- **Synchronous LLM Interception:** Dynamic prompt inspection adds latency to agent reasoning steps (1.2s - 2.8s depending on model provider).

---

## 9. License

This project is licensed under the Apache 2.0 License. See `LICENSE` for details.
