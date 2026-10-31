# FINSHIELD API Contracts

This document outlines the core RESTful APIs that power the FINSHIELD platform, serving as the bridge between the Frontend, Agent Service, Payment Service, and Risk/Policy Engines.

## 1. Authentication & Users

### `POST /v1/auth/register`
Create a new user account and initialize a sandbox wallet.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword",
    "first_name": "Alice",
    "last_name": "Smith"
  }
  ```
- **Response** (201 Created):
  ```json
  {
    "token": "jwt_token_string",
    "user_id": "uuid"
  }
  ```

### `POST /v1/auth/login`
- **Request Body**: `email`, `password`
- **Response** (200 OK): `token`, `user_id`

## 2. Agent Management

### `POST /v1/agents`
Create a new AI agent with specific financial boundaries.
- **Request Body**:
  ```json
  {
    "name": "Shopping Agent",
    "daily_limit": 100000.00,
    "max_transaction_amount": 80000.00
  }
  ```
- **Response** (201 Created): `agent_id`, `name`, `status`

### `GET /v1/agents/{agent_id}`
Retrieve agent details, current status, and risk metrics.
- **Response** (200 OK):
  ```json
  {
    "id": "uuid",
    "name": "Shopping Agent",
    "status": "ACTIVE",
    "monthly_spend": 24000.00,
    "risk_level": "LOW"
  }
  ```

## 3. Intents & Agent Interaction (Agent Service)

### `POST /v1/agents/{agent_id}/intents`
User provides a natural language objective to the agent.
- **Request Body**:
  ```json
  {
    "raw_text": "Buy me a laptop under ₹80,000 with 16GB RAM"
  }
  ```
- **Response** (201 Created):
  ```json
  {
    "intent_id": "uuid",
    "structured_data": {
      "category": "laptop",
      "max_amount": 80000,
      "currency": "INR",
      "requirements": {"ram": "16GB"}
    }
  }
  ```

### `GET /v1/agents/{agent_id}/trajectory/{intent_id}`
Stream or poll the agent's actions as it works on the intent.
- **Response** (200 OK):
  ```json
  {
    "events": [
      {"type": "SEARCH", "details": "Searched laptops on Merchant A", "timestamp": "..."},
      {"type": "TOOL_CALL", "details": "compare_price", "timestamp": "..."}
    ]
  }
  ```

## 4. FINSHIELD Core (Decision Engine)

### `POST /v1/authorization/check`
**Internal API**: Called by the Agent before making a final payment. Evaluates intent, risk, and policy.
- **Request Body**:
  ```json
  {
    "agent_id": "uuid",
    "intent_id": "uuid",
    "order_id": "uuid",
    "amount": 74999.00,
    "currency": "INR"
  }
  ```
- **Response** (200 OK):
  ```json
  {
    "decision": "BLOCK", // ALLOW, REVIEW, BLOCK
    "risk_score": 0.91,
    "intent_alignment": 0.14,
    "policy_violations": ["MAX_AMOUNT_EXCEEDED"]
  }
  ```

## 5. Payment & Orders (Payment Service)

### `GET /v1/wallets/me`
Retrieve user's sandbox balance.
- **Response** (200 OK):
  ```json
  {
    "balance": 50000.00,
    "currency": "INR",
    "held_amount": 0.00
  }
  ```

### `GET /v1/payments`
List all payments, their statuses, and FINSHIELD risk scores.
- **Response** (200 OK):
  ```json
  {
    "payments": [
      {
        "id": "uuid",
        "amount": 74999.00,
        "status": "CAPTURED",
        "risk_metrics": {"intent_alignment": 0.97}
      }
    ]
  }
  ```

## 6. Policies (Policy Service)

### `POST /v1/policies`
Create a deterministic rule.
- **Request Body**:
  ```json
  {
    "agent_id": "uuid", 
    "condition_logic": {
      "field": "amount",
      "operator": ">",
      "value": 50000
    },
    "action": "REVIEW"
  }
  ```
- **Response** (201 Created): Policy Object
