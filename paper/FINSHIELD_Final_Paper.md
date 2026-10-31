# FINSHIELD: A Deterministic Execution-Control Plane for Autonomous Agentic Commerce



# Abstract

Autonomous agents are increasingly deployed to execute complex, multi-step actions on behalf of users. However, integrating these agents into financial operations introduces critical security vulnerabilities: the probabilistic reasoning of Large Language Models (LLMs) cannot serve as a reliable authorization mechanism. Agents may succumb to prompt injection, manipulate transaction parameters, exceed delegated authority, or drift from user intent. 

To address this, we present FINSHIELD, a neutral execution-control plane that decouples user intent from agent capability. FINSHIELD introduces a deterministic Action Gate that isolates the untrusted agent from the trusted execution environment. By performing authoritative transaction-state hydration and enforcing cryptographic, single-use human approvals bound to exact execution contexts, FINSHIELD ensures that agent actions are rigorously validated before crossing the financial boundary. 

We empirically evaluate FINSHIELD against concrete adversarial scenarios—including amount escalation, target manipulation, and prompt injection—demonstrating containment of the tested unauthorized financial execution scenarios under the evaluated model-provider configurations. Our findings provide empirical evidence for a robust architectural pattern for constraining autonomous agentic commerce at the financial execution boundary.


# 1. Introduction

Autonomous agents are increasingly capable of performing complex, multi-step actions on behalf of users, particularly in e-commerce, procurement, and financial operations. However, deploying these agents in real-world financial contexts introduces an acute security gap: the probabilistic reasoning of Large Language Models (LLMs) cannot serve as a reliable financial authorization mechanism. 

An autonomous agent operating with financial capabilities can misunderstand user intent, succumb to adversarial prompt injection, manipulate transaction parameters, exceed delegated authority, or experience semantic drift. Traditional role-based access controls and user-centric threat models fail to account for an agent acting as a compromised intermediary.

### Proposed System: FINSHIELD
We introduce **FINSHIELD**, a neutral execution-control plane that evaluates and enforces whether an autonomous agent action is authorized to cross a financial execution boundary. FINSHIELD does not attempt to make the LLM secure; rather, it introduces a deterministic Action Gate that isolates the untrusted agent from the trusted execution environment.

### Core Contributions
1. **Intent and Authority Separation:** Explicitly decoupling the user's intent from the agent's operational capabilities.
2. **Authoritative Transaction-State Hydration:** Reconstituting transaction context from trusted server-side state, preventing agent-driven metadata spoofing.
3. **Deterministic Action Gate:** A strictly ordered enforcement perimeter that validates alignment, risk, and policy before execution.
4. **Context-Bound Human Review:** Cryptographically binding human approvals to exact transaction payloads to prevent substitution and replay attacks.
5. **Empirical Evaluation:** Extensive validation against concrete adversarial scenarios, demonstrating containment of target manipulation, amount escalation, and prompt injection attacks.


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


# 5. Implementation

FINSHIELD is built on a production-oriented architecture designed for modularity, strict typing, and high performance.

### 7.1 Technology Stack
* **Frontend:** React + TypeScript + Vite
* **Backend:** FastAPI + Pydantic + SQLAlchemy + Alembic
* **Database:** SQLite (Development) / PostgreSQL-compatible architecture
* **Cache:** Redis
* **Machine Learning:** scikit-learn / PyTorch (Risk modeling)
* **LLM Providers:** Groq (gpt-oss-20b), OpenRouter (Nemotron), Local Ollama (Qwen3:8B)
* **Testing:** Pytest / Playwright
* **Deployment:** Docker / Docker Compose

### 7.2 Modular Monolith
The backend is structured as a modular monolith, cleanly separating the untrusted Agent Runtime from the trusted Commerce, Policy, and Action Gate services. This ensures that security-critical modules can scale and be audited independently while maintaining tight execution boundaries.


# 6. Threat Model

# 4. Threat Model

In autonomous agent architectures, traditional user-centric threat models are insufficient. FINSHIELD assumes a threat model where the agent itself is considered fundamentally untrusted and susceptible to adversarial manipulation. 

### 4.1 Trust Boundaries and Assumptions
FINSHIELD defines strict trust boundaries separating the agent environment from the execution environment:
* **Untrusted Agent:** The underlying Large Language Model (LLM), the agent's reasoning loop, and its memory are assumed to be fully compromised or prone to hallucinations. The agent may attempt to execute unauthorized financial actions due to prompt injection, semantic drift, or explicit adversarial manipulation.
* **Trusted Authority:** The central database, the developer-configured policy rules, and the authenticated user intents are assumed to be trusted.
* **The Action Gate:** The enforcement perimeter (the Action Gate) is trusted to securely mediate all state-altering operations between the untrusted agent and the trusted execution environment.

### 4.2 Adversarial Capabilities
We assume an attacker capable of manipulating the agent's behavior through the following attack vectors:
1. **Amount Escalation:** The agent attempts to bypass financial limits by multiplying quantities, chaining multiple transactions, or altering pricing parameters within the payload.
2. **Target Manipulation:** The agent attempts to reroute funds or resources by injecting unauthorized target identifiers (e.g., malicious merchant IDs or destination accounts) into the execution payload.
3. **Semantic Drift:** The agent fulfills the monetary requirements of a transaction but violates the semantic constraint configured by the user (e.g., purchasing a gaming laptop instead of an office laptop).
4. **Prompt Injection / Jailbreaks:** An external attacker overrides the agent's system prompt to force unauthorized financial execution.

### 6. Security Model and Authorization Framework

To counter the threats outlined above, FINSHIELD implements a deterministic, multi-layered authorization model that shifts security enforcement away from the LLM's reasoning capabilities and into an immutable execution perimeter.

##### 6.1 Authoritative State Hydration
A core principle of the FINSHIELD security model is that the agent cannot be trusted to self-report transaction metadata (e.g., prices, target IDs, item categories). Before any authorization decision is made, the Action Gate intercepts the agent's tool call and performs **Authoritative State Hydration**. It discards the agent-provided sensitive fields and reconstitutes the transaction context by querying the trusted server-side database. This mechanism guarantees that all subsequent policy evaluations operate on ground-truth data, neutralizing Target Manipulation and data spoofing attacks.

##### 6.2 The Action Gate and Policy Engine
The Action Gate serves as a deterministic interception layer. Its core authorization decision is defined formally as:

$$
D = G(I,A,P,R,C)
$$

where:
* \(I\) = authorized intent
* \(A\) = delegated authority
* \(P\) = active policy set
* \(R\) = risk assessment
* \(C\) = authoritative transaction context
* \(G\) = Action Gate
* \(D \in \{ALLOW, REVIEW, BLOCK\}\)

The basic execution invariant guarantees that execution only occurs if the Action Gate explicitly allows it based on valid context:

$$
Execute(a) \Rightarrow G(I,A,P,R,C)=ALLOW
$$
or:
$$
Execute(a) \Rightarrow \text{ValidGateDecision} \land \text{ValidAuthority} \land \text{ValidPolicy} \land \text{ValidContext}
$$

For operations requiring human oversight:
$$
Execute(a) \Rightarrow G(...) = REVIEW \land ValidHumanApproval
$$

And crucially, for blocked operations:
$$
G(...) = BLOCK \Rightarrow \neg Execute(a)
$$

Once a transaction is hydrated with authoritative state, the Policy Engine evaluates it against predefined deterministic authorization constraints:
* **Monetary Ceilings:** Absolute spending limits that trigger an immediate `BLOCK` if exceeded.
* **Review Thresholds:** Configurable bounds that pause the transaction and place it in a `REVIEW_REQUIRED` state for human validation.
* **Semantic Intent Constraints:** Validation of the hydrated product category against the authorized intent category. 

By removing security responsibilities from the stochastic LLM and enforcing them at the deterministic Action Gate, FINSHIELD provides rigorous, mathematically sound containment for autonomous financial operations.


# 7. Security Model / Security Analysis

# Security Analysis

This section analyzes the structural defenses of FINSHIELD against specific adversarial vectors.

### Amount Escalation
`Attack -> Aggregate transaction evaluated -> Monetary constraint violated -> BLOCK`
By evaluating the fully hydrated, aggregate cost rather than single-item prices, the Action Gate deterministically halts escalation attacks.

### Target Manipulation
`Agent target injected -> Discarded during hydration -> Authoritative target applied -> Execution`
Target manipulation is neutralized because the execution environment refuses to trust agent-supplied metadata for sensitive routing or target fields.

### Semantic Drift
`Agent-selected product -> Authoritative category hydrated -> Intent constraint evaluated -> Alignment`
FINSHIELD enforces configured semantic constraints (e.g., category restrictions) strictly at the execution boundary, preventing the agent from satisfying monetary constraints with semantically misaligned purchases.

### Replay Protection
`Signed decision + Nonce + Expiry + Single-use state`
Decisions generated by the Action Gate or Human Approvers are cryptographically bound to exact contexts and immediately consumed, rendering replay of a valid decision infeasible under the implemented nonce, expiry, signature, and single-use checks, assuming the trusted enforcement state remains uncompromised.

### Approval Substitution
`Approval -> Exact transaction binding -> Revalidation -> Consume -> Execute once`
An attacker cannot substitute a different product or amount into an approved transaction; the execution payload must cryptographically match the original approved context.

### Revocation
Both delegated authority and agent credentials are continuously revalidated. Revoked agents or deleted intents instantly fail authorization, even if the agent is mid-execution.


# 8. Experimental Methodology & 9. Benchmark Results

# Phase 5 — Empirical Security Evaluation

### Provider Configurations
The empirical evaluation utilized multiple model-provider configurations across its experiments to validate FINSHIELD's core authorization mechanisms:
* **Groq / gpt-oss-20b**: Utilized for establishing the foundational Phase 5.1 security benchmark.
* **Local Ollama / Qwen3:8B**: Utilized for the Phase 5.2 semantic intent constraint enforcement trials, and the Phase 5.3 target manipulation robustness trial.
* **OpenRouter / Nemotron**: Utilized for the majority of the Phase 5.3 execution-boundary robustness suite.

These configurations provide evidence of FINSHIELD's enforcement behavior under the tested scenarios; they do not constitute a controlled comparison of provider robustness. The evaluation focuses on the structural enforcement mechanisms rather than the general semantic reasoning capabilities of any individual model.

---

### 5.1 Policy and Execution-Boundary Enforcement
This phase established the baseline effectiveness of the Action Gate and Policy Engine. The evaluation confirmed that:
* **Legitimate Execution:** Transactions complying with the maximum authorized amount and policy constraints successfully executed without friction.
* **Policy Review:** Transactions exceeding the automated approval threshold but within the hard ceiling correctly paused execution and triggered a `REVIEW_REQUIRED` state.
* **Amount Escalation:** Adversarial attempts to multiply quantities and breach the absolute monetary constraint were physically halted by the Action Gate, preventing unauthorized capital expenditure.

### 5.2 Semantic Intent Constraint Enforcement
Phase 5.2 evaluated whether FINSHIELD could enforce a semantic constraint independently of monetary authorization. The benchmark defined an intent constraint requiring a `laptop` purchase with a maximum authorized amount of ₹80,000. The agent selected a Premium Gaming Laptop priced at ₹65,000, which remained within the monetary boundary but had the authoritative product category `gaming`. 

In the unprotected baseline, the autonomous agent successfully completed the ₹65,000 purchase. Under FINSHIELD protection, the same agent reached the checkout boundary, where the runtime hydrated the authoritative product category (`gaming`) from server state rather than relying on the agent-supplied value. The resulting mismatch against the intent constraint (`laptop`) caused the Action Gate to reject the action with HTTP 403. 

The experiment provides empirical evidence that FINSHIELD enforces the configured semantic intent constraint under the tested scenario, effectively separating semantic intervention from the monetary authorization boundary.

### 5.3 Adversarial Robustness and Containment
Phase 5.3 evaluated FINSHIELD's execution-boundary enforcement against several adversarial scenarios, including amount escalation, prompt injection, target manipulation, and system-prompt disclosure attempts. Multiple model-provider configurations were used across the experiments; these trials were not designed as a controlled comparison of model or provider robustness. Instead, they evaluated whether the FINSHIELD enforcement boundary remained effective under the tested agent configurations.

* **Amount Escalation:** The agent attempted to purchase twice the authorized quantity. FINSHIELD evaluated the aggregate transaction value and successfully triggered a hard block at the Action Gate.
* **Prompt Injection:** An explicit jailbreak ("IGNORE ALL PREVIOUS INSTRUCTIONS") attempting to force an unauthorized purchase was intercepted by the Policy Engine, triggering a concrete `REVIEW_REQUIRED` outcome as dictated by the configured policy.
* **Target Manipulation:** The agent was instructed to manipulate the target merchant ID (`merch_attacker_999`) during checkout. Under FINSHIELD protection, the Action Gate ignored the agent-supplied sensitive field, instead hydrating the authoritative merchant ID directly from the server-side cart state. The transaction proceeded securely against the legitimate merchant, demonstrating, under the tested scenario, that agent-provided transaction metadata does not override authoritative server state.
* **System Prompt Leak:** The agent was instructed to leak its system instructions. The trial remained **INCONCLUSIVE** because the agent did not reach the financial action boundary. This specifically demonstrates the distinction between an LLM refusing a prompt versus FINSHIELD actively preventing an execution.


# 10. Related Work

The rise of autonomous agent architectures has prompted varied approaches to execution security. We evaluate FINSHIELD relative to existing paradigms across several axes:

| System | Agent Execution | Intent Separation | Delegated Authority | Deterministic Gate | Risk Engine | Bound Human Review | Forensic Audit |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FINSHIELD (Our Work)** | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| **LangGraph HITL** | Yes | No | No | No | No | Yes | No |
| **Agent2Agent Protocols** | Yes | No | Partial | No | No | No | Yes |
| **AP2** | Yes | No | No | No | No | No | No |
| **Visa Intelligent Commerce** | Yes | Partial | Yes | Yes | Yes | No | Partial |
| **Stripe Agentic Commerce** | Yes | No | Yes | Partial | Yes | No | Yes |
| **Prompt Injection Defenses** | No | No | No | No | No | No | No |

**Human-in-the-Loop (HITL) Frameworks:** Systems like LangGraph provide mechanics for pausing execution (via interrupts and persistence checkpoints) for human input or tool approval [1]. While effective for static workflows, they typically lack a formalized, deterministic separation of intent from the agent's LLM state at the network boundary, leaving the decision logic coupled to the agent runtime.

**Agent-to-Agent Protocols:** The Agent2Agent (A2A) protocol (Linux Foundation) standardizes communication, task delegation, and discovery between autonomous AI agents using "Agent Cards" [2]. While it ensures vendor neutrality and interoperability, A2A is primarily a communication layer and does not natively enforce deterministic financial constraints or human-in-the-loop payment boundaries.

**Commercial Agentic Commerce Initiatives:** Recent initiatives by major payment networks attempt to secure agent transactions. **Visa Intelligent Commerce** utilizes the Trusted Agent Protocol (TAP) and spending controls to verify agent authenticity and bind agents to user-defined limits [3]. Similarly, the **Stripe Agentic Commerce Suite** introduces Shared Payment Tokens (SPTs) and Delegated Checkout to allow agents to transact on a user's behalf without exposing raw credentials, while the Stripe Agent Toolkit provides LLM-compatible tool bindings [4]. However, FINSHIELD differs from these external payment gateways by providing a localized, deterministic execution boundary (the Action Gate) that sits *between* the agent runtime and the external payment processor, enabling authoritative state hydration and semantic intent enforcement before the payment request is ever formulated.

**Prompt Injection Defenses:** Much existing research focuses on filtering adversarial inputs before they reach the LLM. In contrast, FINSHIELD assumes the LLM will be successfully injected and focuses exclusively on containing the resulting execution attempt.

### References
[1] LangChain, "Human-in-the-Loop," LangGraph Documentation, 2024.
[2] Linux Foundation, "Agent2Agent (A2A) Protocol Specification," A2A-Protocol.org.
[3] Visa, "Visa Intelligent Commerce and Trusted Agent Protocol," 2024.
[4] Stripe, "Stripe Agentic Commerce Suite and Stripe Agent Toolkit," 2024.


# 11. Limitations

To ensure the credibility of the FINSHIELD evaluation, it is critical to state exactly what the architecture does not claim to solve or defend against.

### 11.1 LLM Reasoning Correctness
FINSHIELD does not make the underlying Large Language Model truthful, reliable, or intelligent. It assumes the LLM is fundamentally untrusted. If an agent executes a poorly reasoned transaction that perfectly aligns with the user's stated intent, delegated authority, and monetary limits, the transaction will be allowed.

### 11.2 General Semantic Understanding
The Phase 5.2 experiments validated the enforcement of configured, discrete semantic constraints (e.g., category restrictions). FINSHIELD relies on deterministic alignment between authorized metadata and hydrated product states. It does not establish general-purpose semantic understanding of intent.

### 11.3 Provider Security
The empirical evaluation was conducted using specific provider configurations (Groq, OpenRouter, Local Ollama). While FINSHIELD's enforcement boundary remains consistent, the evaluation does not guarantee security uniformity across every available LLM provider or future model iterations.

### 11.4 System Prompt Extraction
The System Prompt Leak scenario in Phase 5.3 remained inconclusive as the agent did not reach the financial boundary. FINSHIELD focuses on execution containment, not preventing model prompt extraction or data exfiltration via non-financial API interactions.

### 11.5 Trusted Backend Assumption
The FINSHIELD architecture assumes the backend infrastructure—including the database, Policy Engine, and Action Gate—remains uncompromised. If an attacker breaches the trusted zone directly, bypassing the Agent Runtime, the threat model is violated.

### 11.6 External Payment Processor Compromise
Compromises occurring at the external payment processor or banking layer exist outside the demonstrated Action Gate boundary and are therefore out of scope.



# 12. Discussion

The core thesis of FINSHIELD is that **LLM reasoning ≠ authorization**, and **agent-supplied metadata ≠ authoritative transaction state**. Our evaluation highlights a critical distinction between architectural guarantees and empirical findings:

### Architectural Guarantees
By design, FINSHIELD's deterministic Action Gate formally guarantees that execution invariants hold. The system structurally enforces:
* **Authoritative hydration:** Discarding untrusted agent metadata and pulling ground-truth from the trusted database.
* **Exact-context approval:** Human reviews are cryptographically bound to the exact payload.
* **Single-use approval:** State checks and nonces prevent replay or substitution.
* **Fail-closed enforcement:** Any violation of intent, authority, or policy defaults to a BLOCK.

### Empirical Findings
The Phase 5 evaluation provides concrete evidence of these mechanisms working in practice under our specific provider configurations (Qwen3:8B, Nemotron, Groq):
* **Amount escalation containment:** Blocked aggregation attacks.
* **Semantic drift containment:** Successfully blocked a purchase that satisfied monetary constraints but violated the semantic `laptop` vs `gaming` category intent constraint.
* **Target manipulation containment:** Hydration successfully stripped the agent's injected merchant ID and routed the transaction to the authoritative target.
* **Prompt injection:** Adversarial instructions successfully executed within the sandbox but were caught in the `REVIEW` state by the Action Gate policy.
* **System-prompt leak:** As expected, this experiment remained **INCONCLUSIVE**; data exfiltration via non-financial API boundaries lies outside the financial execution boundary and was not contained by the Action Gate.

# 13. Conclusion

We presented FINSHIELD, a framework designed to secure autonomous agents acting in financial contexts. By separating intent from agent capabilities and enforcing deterministic checks via an Action Gate, FINSHIELD provides empirical evidence for a robust architectural pattern for constraining autonomous agentic commerce at the financial execution boundary.
