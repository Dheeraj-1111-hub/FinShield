# FINSHIELD Database Schema (PostgreSQL)

This document outlines the core database schema for the FINSHIELD platform.

## 1. Core Platform & Identity

### `users`
Represents the human users who own agents and accounts.
- `id` (UUID, PK)
- `email` (VARCHAR, Unique)
- `password_hash` (VARCHAR)
- `first_name` (VARCHAR)
- `last_name` (VARCHAR)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### `agents`
Represents the AI agents instantiated by users.
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id)
- `name` (VARCHAR) - e.g., "Shopping Agent"
- `status` (ENUM: 'ACTIVE', 'PAUSED', 'REVOKED')
- `daily_limit` (DECIMAL)
- `max_transaction_amount` (DECIMAL)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

## 2. Commerce System

### `merchants`
Entities selling products.
- `id` (UUID, PK)
- `name` (VARCHAR)
- `risk_score` (DECIMAL) - Base risk score of the merchant
- `status` (ENUM: 'ACTIVE', 'SUSPENDED')
- `created_at` (TIMESTAMP)

### `products`
Items available for purchase.
- `id` (UUID, PK)
- `merchant_id` (UUID, FK -> merchants.id)
- `name` (VARCHAR)
- `description` (TEXT)
- `category` (VARCHAR)
- `price` (DECIMAL)
- `currency` (VARCHAR, Default 'INR')
- `stock_status` (ENUM: 'IN_STOCK', 'OUT_OF_STOCK')
- `created_at` (TIMESTAMP)

### `orders`
The commerce order placed by an agent.
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id)
- `agent_id` (UUID, FK -> agents.id)
- `merchant_id` (UUID, FK -> merchants.id)
- `product_id` (UUID, FK -> products.id)
- `status` (ENUM: 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED')
- `total_amount` (DECIMAL)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

## 3. FINSHIELD Security Core

### `intents`
The structured objective the user gave the agent.
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id)
- `agent_id` (UUID, FK -> agents.id)
- `raw_text` (TEXT) - Original user prompt
- `structured_data` (JSONB) - e.g., `{"category": "laptop", "max_price": 80000}`
- `status` (ENUM: 'ACTIVE', 'COMPLETED', 'ABORTED')
- `created_at` (TIMESTAMP)

### `agent_events` (Trajectory)
Records every action the agent takes (search, tool call, external page).
- `id` (UUID, PK)
- `agent_id` (UUID, FK -> agents.id)
- `intent_id` (UUID, FK -> intents.id)
- `event_type` (VARCHAR) - e.g., 'TOOL_CALL', 'PAGE_VISIT'
- `payload` (JSONB) - Details of the action
- `timestamp` (TIMESTAMP)

### `policies`
Deterministic rules configured by the user.
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id)
- `agent_id` (UUID, FK -> agents.id, Nullable)
- `condition_logic` (JSONB) - e.g., `{"field": "amount", "operator": ">", "value": 50000}`
- `action` (ENUM: 'ALLOW', 'REVIEW', 'BLOCK')
- `is_active` (BOOLEAN)
- `created_at` (TIMESTAMP)

## 4. Payment Infrastructure

### `wallets`
Stores the user's available balance in the sandbox.
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id)
- `balance` (DECIMAL)
- `currency` (VARCHAR, Default 'INR')
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### `payment_intents` (FINSHIELD Evaluation)
The request for payment authorization, evaluated by FINSHIELD.
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id)
- `agent_id` (UUID, FK -> agents.id)
- `order_id` (UUID, FK -> orders.id)
- `amount` (DECIMAL)
- `currency` (VARCHAR)
- `risk_metrics` (JSONB) - `{"intent_alignment": 0.97, "transaction_risk": 0.03}`
- `policy_decision` (ENUM: 'ALLOW', 'REVIEW', 'BLOCK')
- `status` (ENUM: 'CREATED', 'PENDING_REVIEW', 'AUTHORIZED', 'REJECTED', 'FAILED')
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

### `ledger_transactions`
Double-entry accounting log for actual money movement (Sandbox).
- `id` (UUID, PK)
- `payment_intent_id` (UUID, FK -> payment_intents.id)
- `from_wallet_id` (UUID, FK -> wallets.id)
- `to_merchant_id` (UUID, FK -> merchants.id)
- `amount` (DECIMAL)
- `status` (ENUM: 'CAPTURED', 'REFUNDED')
- `created_at` (TIMESTAMP)

## 5. Investigations & Audit

### `investigations`
Created when a transaction is BLOCKED or marked for REVIEW.
- `id` (UUID, PK)
- `payment_intent_id` (UUID, FK -> payment_intents.id)
- `user_id` (UUID, FK -> users.id)
- `agent_id` (UUID, FK -> agents.id)
- `reason` (TEXT)
- `severity` (ENUM: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
- `status` (ENUM: 'OPEN', 'RESOLVED')
- `created_at` (TIMESTAMP)
- `resolved_at` (TIMESTAMP, Nullable)
