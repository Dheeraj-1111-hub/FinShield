# 5. FINSHIELD Architecture

The FINSHIELD architecture inserts a deterministic execution boundary between the autonomous agent and the financial execution context. 

### 5.1 System Overview
The lifecycle of a FINSHIELD transaction flows sequentially through isolated trust zones:
`User -> Intent -> Delegated Authority -> Agent -> Agent Runtime -> Risk -> Policy -> Action Gate -> Payment/Commerce -> Audit`

### 5.2 Agent Runtime
The Agent Runtime manages the untrusted LLM's execution loop, coordinating actions, capabilities, and tool execution. It enforces idempotency and API rate limits while isolating the agent's memory from the actual execution state.

### 5.3 Intent and Authority
FINSHIELD explicitly separates distinct user concepts:
`USER REQUEST ≠ INTENT ≠ DELEGATED AUTHORITY ≠ AGENT ACTION`
A user request translates into a formal Intent, which is backed by Delegated Authority, strictly limiting the scope of any subsequent Agent Action.

### 5.4 Risk Engine
The Risk Engine evaluates real-time signals (e.g., transaction velocity, anomaly detection) against configurable thresholds to dynamically flag high-risk operations before policy evaluation.

### 5.5 The Action Gate
The Action Gate is the core deterministic enforcement perimeter. Its lifecycle is strictly ordered:
`Hydrate -> Validate -> Align -> Risk -> Policy -> Decision (ALLOW/REVIEW/BLOCK) -> Signed Decision -> Execution`

### 5.6 Approval Mechanism
When the Action Gate issues a `REVIEW_REQUIRED` decision, human approval is bound to the exact, hydrated transaction context. Approvals are single-use, cryptographically verified, and immediately consumed to prevent replay or substitution attacks.

### 5.7 Audit and Investigations
Every action, decision, and state change is immutably logged, enabling full forensic reconstruction of any transaction lifecycle.
