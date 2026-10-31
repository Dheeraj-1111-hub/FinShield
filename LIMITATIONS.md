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
