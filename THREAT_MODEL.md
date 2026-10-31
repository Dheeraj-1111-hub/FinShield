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

# 6. Security Model and Authorization Framework

To counter the threats outlined above, FINSHIELD implements a deterministic, multi-layered authorization model that shifts security enforcement away from the LLM's reasoning capabilities and into an immutable execution perimeter.

### 6.1 Authoritative State Hydration
A core principle of the FINSHIELD security model is that the agent cannot be trusted to self-report transaction metadata (e.g., prices, target IDs, item categories). Before any authorization decision is made, the Action Gate intercepts the agent's tool call and performs **Authoritative State Hydration**. It discards the agent-provided sensitive fields and reconstitutes the transaction context by querying the trusted server-side database. This mechanism guarantees that all subsequent policy evaluations operate on ground-truth data, neutralizing Target Manipulation and data spoofing attacks.

### 6.2 The Action Gate and Policy Engine
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
