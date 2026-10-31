# TrustGuard AI

FINSHIELD — FRONTEND MASTER PLAN

The application should have this structure:

FINSHIELD
│
├── PUBLIC WEBSITE
│   ├── Landing
│   ├── Product
│   ├── How it works
│   ├── Security
│   ├── Developers
│   ├── Research
│   └── Pricing / Early Access
│
├── AUTHENTICATION
│   ├── Sign up
│   ├── Sign in
│   ├── Email verification
│   ├── Forgot password
│   ├── Reset password
│   └── Onboarding
│
└── APPLICATION
    ├── Overview
    ├── Agents
    ├── Agent Console
    ├── Payments
    ├── Orders
    ├── Risk Center
    ├── Policies
    ├── Investigations
    ├── Security Lab
    ├── Benchmark Lab
    ├── Audit Log
    └── Developer

I would not put all 11 things as giant sidebar tabs.

That's one of the mistakes that makes dashboards look amateurish.

We'll group them intelligently.

1. THE PUBLIC LANDING PAGE

This is extremely important.

Someone should understand FINSHIELD within 10 seconds.

Hero

                 FINSHIELD

     TRUST INFRASTRUCTURE
     FOR AUTONOMOUS FINANCE

AI agents can act on your behalf.
FINSHIELD makes sure they act
within your intent.

        [Start Building] [See How It Works]

        ● Runtime protection
        ● Intent verification
        ● Financial policy enforcement

Don't use generic:

"Revolutionizing the future of AI-powered fintech."

That sounds like a student project.

Be extremely specific.

2. Hero visual

Instead of a stock image, we create a live product visualization.

Something like:

┌──────────────────────────────────────────────┐
│ Shopping Agent                         ● LIVE │
│                                              │
│ User intent                                  │
│ "Buy laptop under ₹80,000"                   │
│                                              │
│ Agent activity                               │
│ ✓ Searching products                         │
│ ✓ Comparing merchants                        │
│ ✓ Checking price                             │
│                                              │
│ FINSHIELD                                     │
│ Intent alignment       97%                    │
│ Transaction risk        3%                    │
│ Policy status          PASS                   │
│                                              │
│              ✓ PAYMENT APPROVED               │
└──────────────────────────────────────────────┘

It should subtly animate.

The visitor immediately understands:

Agent → FINSHIELD → Payment.

3. Landing page sections

I'd have approximately 8 sections.

Section 1 — Hero

What FINSHIELD is.

Section 2 — The problem

AI can reason.
AI can act.
AI can spend.

But who controls the decision?

Show the difference:

Traditional payment

Human → Pay → Payment


Agentic payment

Human
 ↓
Agent
 ↓
Tools
 ↓
Web
 ↓
Decision
 ↓
Payment

Section 3 — How FINSHIELD works

Interactive pipeline:

Intent
 ↓
Agent
 ↓
Trajectory
 ↓
Risk
 ↓
Policy
 ↓
Decision

Hovering/clicking each stage reveals what happens.

Section 4 — Product demo

Embedded interactive walkthrough.

Visitor can click:

"Buy laptop under ₹80K"

and watch the workflow.

Then show:

Attack detected → payment blocked.

Section 5 — Features

Six cards:

Intent Verification

Does the transaction match the user's goal?

Agent Behavior

Is the agent behaving normally?

Transaction Intelligence

Does the transaction look risky?

Policy Enforcement

Does it satisfy financial constraints?

Runtime Protection

Can we stop unsafe actions before payment?

Auditability

Can we explain exactly what happened?

Section 6 — For developers

Show:

Your AI Agent
       ↓
FINSHIELD SDK
       ↓
Risk + Policy + Intent
       ↓
Payment

with API snippets.

Section 7 — Research

This is important for your R&D positioning.

Show:

Intent Alignment
Trajectory Security
Agentic Payment Safety
Financial Risk
Adversarial Evaluation

Not "AI powered" marketing fluff.

Section 8 — CTA

Build agents that can act without losing control.

Create your first agent →

4. NAVIGATION OF THE PUBLIC WEBSITE

Desktop:

FINSHIELD        Product  Developers  Research  Security

                         Sign in
                         Get started

Mobile becomes hamburger navigation.

Keep it clean.

5. AUTHENTICATION

We need professional auth screens.

Sign Up

FINSHIELD

Create your account

Work email
[________________]

Password
[________________]

☐ I agree to the Terms

[Create account]

Already have an account?
Sign in

Potentially:

Continue with Google

if we implement OAuth.

6. Sign In

Simple.

Welcome back

Email
Password

[ Sign in ]

Forgot password?

──────── OR ────────

Continue with Google

No unnecessary design.

7. Forgot / Reset Password

Standard professional flow.

Forgot your password?

Enter your email.

[ Send reset link ]

Then:

Create new password
New password
Confirm password

[Reset password]

8. ONBOARDING

This is where many student projects fail.

After signup, don't dump the user into a dashboard.

Use a short onboarding flow.

Step 1

What are you building?

○ Personal AI agent
○ Fintech application
○ Developer project
○ Research

Step 2

Create your first agent

Step 3

Set financial permissions

Step 4

Fund your sandbox account

Step 5

Try your first transaction

Then:

Welcome to FINSHIELD.

9. THE APPLICATION

Once authenticated, we use a persistent application shell.

┌─────────────────────────────────────────────────────┐
│ FINSHIELD                              🔔  Sai ▼    │
├──────────────┬──────────────────────────────────────┤
│              │                                      │
│ Overview     │                                      │
│              │                                      │
│ Agents       │                                      │
│              │                                      │
│ Payments     │                                      │
│ Orders       │             MAIN CONTENT             │
│              │                                      │
│ Risk         │                                      │
│ Policies     │                                      │
│              │                                      │
│ Investigate  │                                      │
│              │                                      │
│ Security Lab │                                      │
│              │                                      │
│ Benchmarks   │                                      │
│              │                                      │
│ Audit        │                                      │
│              │                                      │
│ Developers   │                                      │
│              │                                      │
│ Settings     │                                      │
└──────────────┴──────────────────────────────────────┘

But I'd actually organize it into 5 navigation groups.

10. SIDEBAR GROUP 1 — HOME

Overview

This is the user's command center.

Top metrics:

Protected Balance
₹50,000

Agent Spending
₹8,420

Transactions
284

Blocked
7

Then:

Agent activity

Shopping Agent      ● Active
Travel Agent        ● Idle
Finance Agent       ● Active

Then:

Recent transactions

Dell Laptop       ₹74,999     Approved
Hotel Booking      ₹6,200     Approved
Unknown Merchant  ₹32,000     Blocked

Then:

Risk overview

System Risk
LOW

Intent violations
3

Policy violations
7

High-risk events
2

This page should answer:

"What's happening with my financial agents right now?"

11. SIDEBAR GROUP 2 — AUTONOMY

Agents

This is one of our main pages.

Cards:

┌─────────────────────────┐
│ 🛒 Shopping Agent       │
│ ● Active                │
│                         │
│ ₹30,000 / month         │
│ 124 transactions        │
│ Risk: Low               │
│                         │
│ [Open Agent]            │
└─────────────────────────┘

Actions:

Create Agent

Pause Agent

Delete Agent

12. Agent creation

This should be a proper wizard.

Identity

Agent name
Purpose
Description

Permissions

Maximum transaction
Daily limit
Monthly limit

Categories

Electronics
Travel
Food
Groceries
Subscriptions
Financial services

Merchant rules

Allowed merchants
Blocked merchants
Merchant risk threshold

Approval policy

Always require approval
Require approval above ₹X
Automatic under ₹X

Review

Then:

Create Agent

13. Agent detail page

This is different from the Agent Console.

Tabs inside the agent:

Overview | Activity | Policies | Transactions | Risk

Overview

Agent status
Permissions
Spending
Trust score
Recent activity

Activity

Real-time agent actions.

10:31 Searching
10:32 Product opened
10:32 Merchant checked
10:33 Payment requested

14. Agent Console

This is the user-facing AI experience.

Essentially:

ChatGPT + autonomous commerce + FINSHIELD.

Left:

Conversation

Right:

Agent status
Intent
Current task
Risk
Actions

Example:

User:

Buy me a laptop below ₹80,000.

Agent:

I'll search for laptops matching
your budget and requirements.

Then live tool execution.

15. The most important UI component here

Agent Activity Timeline

✓ Intent created

✓ Search initiated

✓ 37 products found

✓ 8 products satisfy constraints

✓ Merchant reputation checked

✓ Product selected

→ Payment authorization requested

This lets the user see the agent thinking/acting without exposing private chain-of-thought.

We show actions and evidence, not hidden reasoning.

16. Sidebar group 3 — MONEY

Payments

Show:

Payment volume
Approval rate
Failed
Blocked
Refunded

Filters:

Date
Agent
Merchant
Status
Amount
Risk

Table:

Payment ID
Agent
Merchant
Amount
Status
Risk
Date

Clicking one opens the payment details.

17. Payment details

This is very important.

PAYMENT #PAY-48291

₹74,999

✓ CAPTURED

Then:

Payment lifecycle

Created
   ↓
Risk evaluation
   ↓
Approved
   ↓
Authorized
   ↓
Captured

And:

FINSHIELD decision
Intent alignment: 97%
Risk: 3%
Policy: PASS

18. Orders

Separate from payments.

Because:

Order ≠ payment.

Orders page:

Order
Product
Merchant
Agent
Amount
Payment status
Fulfillment

Order details:

ORDER #ORD-92183

Dell Inspiron
₹74,999

Payment ✓
Processing ✓
Shipped ✓
Delivered ○

This makes the commerce product feel real.

19. Sidebar group 4 — TRUST

Risk Center

This is FINSHIELD's heart.

Top:

RISK OVERVIEW

Overall risk
LOW

Active threats
2

Blocked actions
17

Then:

Risk dimensions

Transaction Risk
Agent Risk
Intent Risk
Merchant Risk
Behavioral Risk

Click any one for details.

20. Risk event details

Example:

CRITICAL RISK EVENT

Transaction:
₹150,000

Agent:
Shopping Agent

Decision:
BLOCKED

Then:

Why?

Intent mismatch
Budget exceeded
Category violation
Suspicious external instruction

Then:

View trajectory

This opens our most visually interesting component.

21. Agent Trajectory Viewer

USER INTENT
     │
     ▼
Search
     │
     ▼
Product A
     │
     ▼
Merchant Website
     │
     ▼
⚠ External instruction
     │
     ▼
Intent drift
     │
     ▼
₹150,000 payment
     │
     ▼
🛑 BLOCKED

Each node can be expanded.

This is where our research becomes understandable to normal users.

22. Policies

This is a real product feature.

The user can create rules.

POLICIES

Shopping Agent

✓ Max transaction ₹80,000

✓ Daily limit ₹1,00,000

✓ Electronics allowed

✕ Financial products blocked

✓ India only

✓ Approval required >₹50,000

Button:

Create policy

Use a visual rule builder rather than forcing users to write code.

23. Policy builder

WHEN

Transaction amount
[ greater than ▼ ]
₹50,000

AND

Category
[ Electronics ]

THEN

[ Require approval ▼ ]

This makes the product approachable.

24. Investigations

This is the SOC-like section.

INVESTIGATIONS

CRITICAL    2
HIGH        7
MEDIUM     14
LOW         23

Each investigation:

INV-18291
Intent divergence

Agent:
Shopping Agent

Status:
Open

Risk:
Critical

Click:

Investigation workspace

Evidence
Timeline
Risk
Graph
Policy
Decision
AI Investigator

25. AI Investigator

Chat interface:

┌───────────────────────────────────────────┐
│ Investigation Assistant                   │
├───────────────────────────────────────────┤
│                                           │
│ Why was this transaction blocked?         │
│                                           │
│ The transaction was blocked because...    │
│                                           │
│ Evidence                                  │
│ • Original intent                         │
│ • Agent trajectory                        │
│ • Policy violation                        │
│ • Transaction anomaly                     │
│                                           │
└───────────────────────────────────────────┘

Every AI-generated conclusion should have links to the underlying evidence.

26. Financial Graph

Within investigations:

User
 │
 ├── Agent
 │     │
 │     ├── Tool
 │     └── Merchant
 │             │
 │             └── Transaction
 │
 └── Account

Interactive graph.

Click node → inspect entity.

This is where we can showcase graph ML.

27. Security Lab

This should be visually distinct.

Call it:

Security Lab

Subtitle:

Test how autonomous agents respond to adversarial financial scenarios.

Attack categories:

Prompt Injection
Indirect Injection
Intent Manipulation
Budget Escalation
Merchant Manipulation
Tool Manipulation
Agent Impersonation
Transaction Splitting

28. Attack scenario UI

Example:

INDIRECT PROMPT INJECTION

Target:
Shopping Agent

Attack:
Malicious merchant content

Objective:
Cause agent to exceed user's budget

Severity:
CRITICAL

[Launch Test]

Then live visualization.

Attack initiated
       ↓
Agent exposed
       ↓
Agent behavior changed
       ↓
FINSHIELD detected anomaly
       ↓
Payment intercepted

RESULT: BLOCKED

29. Benchmark Lab

This is specifically for your R&D story.

BENCHMARK LAB

Scenario
[ Agentic payment security ▼ ]

Dataset
[ 10,000 scenarios ]

Systems

☑ Rules
☑ Transaction ML
☑ LLM Judge
☑ Trajectory Model
☑ FINSHIELD

[RUN BENCHMARK]

Then charts:

Attack Detection
False Positives
Latency
Legitimate Approval
Unsafe Transaction Rate

And detailed comparison.

This is where an interviewer can see your research results instead of reading claims.

30. Audit Log

Every important event.

TIME       EVENT                    ACTOR

10:31      Agent created           User
10:32      Intent created          Agent
10:33      Payment requested       Agent
10:33      Risk evaluated          FINSHIELD
10:33      Payment approved        FINSHIELD
10:34      Payment captured        Payment Engine

Filters:

 agent

 event

 date

 transaction

 severity

31. Developer Portal

This is another major differentiator.

Tabs:

Overview
API Keys
Agents
API Reference
Webhooks
SDKs
Logs

API Keys

Production
Test

pk_test_••••••••••••

Obviously, never display actual secrets after creation.

32. API documentation

We should eventually make this look like a miniature Stripe developer portal.

Example:

POST /v1/authorization/check

Request:

{
  "agent_id": "...",
  "transaction_id": "..."
}

Response:

{
  "decision": "BLOCK",
  "risk_score": 0.91,
  "intent_alignment": 0.14
}

Interactive:

Try it

This is extremely valuable for SDE interviews.

33. Settings

Keep settings separate.

Account

Profile/email/password.

Security

2FA, sessions, API access.

Notifications

Risk alerts, blocked payments, agent events.

Workspace

Organization/team settings.

Billing

Only if we eventually add a pricing layer.

34. DESIGN SYSTEM

This is extremely important.

I don't want random colors and cards everywhere.

We establish a FINSHIELD design system before building pages.

Visual identity

I'd go with:

Background

Very dark charcoal/navy rather than pure black.

Primary

A restrained electric/indigo accent.

Risk colors

Use semantic colors only:

Green  → Safe / Approved
Amber  → Review / Warning
Red    → Blocked / Critical
Blue   → Informational

Don't turn the entire dashboard into a rainbow.

35. Typography

Use something like:

Inter

or a similar modern UI sans-serif.

Hierarchy:

Display       56–72px
H1            36–48px
H2            28–32px
H3            20–24px
Body          14–16px
Metadata      12–13px

For transaction IDs / API keys / technical values:

Monospace font.

36. Spacing

Use an 8px-based spacing system.

4
8
12
16
24
32
48
64
96

This sounds minor, but consistent spacing makes interfaces feel professional.

37. Cards

Don't put everything into cards.

This is a classic student-dashboard mistake.

Use:

Cards

For:

 metrics

 summaries

 agents

 risk indicators

Tables

For:

 transactions

 payments

 audit events

Panels

For:

 investigation

 agent activity

 configuration

Full-width layouts

For:

 graphs

 timelines

 benchmarks

38. Animations

Use animation to communicate state, not decoration.

Examples:

Agent running:

● Processing

Risk evaluation:

subtle pulse.

Payment blocked:

controlled transition.

Trajectory:

nodes appear as events occur.

Avoid:

❌ bouncing buttons
❌ excessive gradients
❌ random particle backgrounds
❌ giant animated blobs

This is fintech infrastructure, not a gaming website.

39. Responsive design

We build desktop-first because this is a complex application.

But it must still work on:

Desktop

Full sidebar.

Tablet

Collapsed sidebar.

Mobile

Bottom navigation / hamburger.

The public website should be fully responsive.

The application should be usable on mobile but optimized for desktop.

40. Loading states

Every asynchronous operation needs a professional state.

Not:

Loading...

Use skeletons.

Example:

████████████
██████
████████████████

41. Empty states

For example:

No agents:

You don't have any agents yet.

Create your first autonomous
financial agent.

[Create agent]

Not:

No data found.

42. Error states

Example:

Something went wrong

We couldn't evaluate this transaction.

Request ID:
req_8f291

[Retry] [View logs]

This is very important for an infrastructure product.

43. Notifications

Top-right bell.

Events:

🔴 Payment blocked
Shopping Agent attempted ₹150,000

🟡 Approval required
Travel Agent requested ₹52,000

🟢 Payment completed
Laptop purchase successful

Click → relevant page.

44. Global search

I'd actually add this.

Keyboard shortcut:

⌘K / Ctrl+K

Search:

Transactions
Agents
Payments
Investigations
Merchants
API logs

This makes the product feel significantly more mature.

45. Command palette

For example:

Search...
────────────────────────

Go to Dashboard
Create Agent
View Transactions
Open Risk Center
Create Policy
Run Security Test
Open API Docs

Very useful.

46. Breadcrumbs

On deep pages:

Risk Center
  /
Investigations
  /
INV-18291

Small detail, big improvement.

47. Accessibility

We should build this properly:

 keyboard navigation

 focus states

 ARIA labels

 sufficient contrast

 semantic HTML

 reduced-motion support

 accessible forms

This is something you can legitimately mention as professional frontend engineering.

48. Technical frontend architecture

I'd use:

Next.js

with:

TypeScript
React
Tailwind CSS

Then a component library/design system built specifically for FINSHIELD.

Structure roughly:

src/
│
├── app/
│   ├── (marketing)/
│   ├── (auth)/
│   └── (dashboard)/
│
├── components/
│   ├── ui/
│   ├── charts/
│   ├── agent/
│   ├── payments/
│   ├── risk/
│   ├── investigations/
│   └── graph/
│
├── features/
│   ├── agents/
│   ├── payments/
│   ├── orders/
│   ├── risk/
│   ├── policies/
│   └── investigations/
│
├── lib/
│   ├── api/
│   ├── auth/
│   └── utils/
│
└── types/

49. State management

Don't immediately throw Redux into everything.

Use:

Server state

TanStack Query.

Local UI state

React state.

Complex workflows

Zustand if needed.

The principle:

Use the simplest state mechanism appropriate to the problem.

50. Real-time updates

This is particularly important for FINSHIELD.

Agent activity, risk events and payment state can update live.

Potentially:

WebSocket / SSE
        ↓
Frontend
        ↓
React state/query cache
        ↓
UI updates

So the user sees:

Searching...
     ↓
Product found
     ↓
Risk evaluation
     ↓
Payment requested
     ↓
Approved

without refreshing.

51. Charts

Keep charts purposeful.

We'll need:

 transaction volume

 approval/block rate

 risk trends

 agent activity

 attack detection

 benchmark comparison

 latency distribution

Don't put charts everywhere just to make the dashboard look sophisticated.

52. Frontend folder/page hierarchy

The complete route map could be:

/
├── /product
├── /developers
├── /research
├── /security
│
├── /login
├── /signup
├── /verify-email
├── /forgot-password
├── /reset-password
│
└── /app
    ├── /overview
    │
    ├── /agents
    │   ├── /new
    │   └── /[agentId]
    │
    ├── /agent-console
    │
    ├── /payments
    │   └── /[paymentId]
    │
    ├── /orders
    │   └── /[orderId]
    │
    ├── /risk
    │
    ├── /policies
    │   ├── /new
    │   └── /[policyId]
    │
    ├── /investigations
    │   └── /[investigationId]
    │
    ├── /security-lab
    │
    ├── /benchmarks
    │
    ├── /audit
    │
    ├── /developers
    │   ├── /api-keys
    │   ├── /webhooks
    │   ├── /logs
    │   └── /docs
    │
    └── /settings

53. But we shouldn't build all of this at once

This is crucial.

The design specification can cover the entire product.

The implementation should happen vertically.

Sprint 1

Public website:

Landing
Product
How it works
Security
Developers

Sprint 2

Auth:

Signup
Login
Verification
Onboarding

Sprint 3

Application shell:

Sidebar
Header
Command palette
Notifications
Overview

Sprint 4

Agents:

Agent list
Create agent
Agent details
Agent console

Sprint 5

Commerce:

Products
Cart
Orders
Checkout
Payments

Sprint 6

FINSHIELD:

Risk
Policies
Decision
Trajectory

Sprint 7

Investigation:

Investigations
Graph
AI investigator
Audit

Sprint 8

Security/R&D:

Security Lab
Benchmark Lab
Experiments

Sprint 9

Developer platform:

API keys
API docs
Webhooks
Logs

Sprint 10

Polish:

responsive
accessibility
animations
loading states
error handling
performance
security

54. The most important frontend philosophy

Every page needs to answer a real user question.

PageQuestion it answersOverviewWhat's happening?AgentsWhat can my agents do?Agent ConsoleWhat is my agent doing?PaymentsWhere is my money going?OrdersWhat did my agent purchase?RiskIs anything dangerous happening?PoliciesWhat am I allowing?InvestigationWhy did FINSHIELD intervene?Security LabCan my agents withstand attacks?BenchmarkDoes FINSHIELD actually work better?AuditWhat exactly happened?DeveloperHow do I integrate FINSHIELD?

That's how we prevent feature bloat.

55. The final product should feel like this

The user enters FINSHIELD.

They see:

Your agents are operating. FINSHIELD is watching.

They create an agent.

They give it permissions.

They say:

"Buy me a laptop under ₹80,000."

The agent actually searches.

It actually selects.

It actually creates an order.

FINSHIELD actually evaluates.

The payment actually goes through the controlled payment infrastructure.

Then you deliberately expose the agent to an adversarial situation.

The agent tries something dangerous.

FINSHIELD catches it.

The payment gets blocked.

The user opens the investigation.

They see the intent → trajectory → risk → policy → decision chain.

Then you open the Benchmark Lab and demonstrate that the system isn't merely a pretty UI—you have experimental evidence behind the architecture.

This is the frontend standard I want us to follow

Not:

"Let's make a nice dashboard."

But:

"Let's design the interface of a real autonomous-finance infrastructure company."

And one more thing: we should not start implementing individual screens until we establish the design system and wireframe the critical user journey.

The first frontend slice I recommend building is:

LANDING
   ↓
SIGN UP
   ↓
ONBOARDING
   ↓
DASHBOARD
   ↓
CREATE AGENT
   ↓
AGENT CONSOLE
   ↓
"BUY LAPTOP < ₹80K"
   ↓
PRODUCT SELECTION
   ↓
FINSHIELD CHECK
   ↓
CHECKOUT
   ↓
PAYMENT
   ↓
ORDER CONFIRMED

That single path will become the golden path of the entire product. Once that feels genuinely like a polished fintech product, we expand the rest of the platform around it.
🛡️ FINSHIELD

AI-Powered Runtime Trust & Risk Infrastructure for Autonomous Financial Agents

The problem we're solving is simple:

AI agents are becoming capable of making purchases and financial decisions on behalf of users, but once an agent starts acting autonomously, how do we make sure it doesn't get manipulated, exceed its authority, or make a transaction that doesn't match what the user originally wanted?

For example, a user tells an AI agent:

"Buy me a laptop under ₹80,000."

The agent searches products, compares them, chooses one and tries to pay.

But imagine the agent encounters malicious content that manipulates it into trying to purchase something completely different for ₹1.5 lakh.

A normal payment system may see a technically authorized transaction. A traditional fraud model may only see the final transaction.

FINSHIELD looks at the entire chain.

User Intent
     ↓
AI Agent
     ↓
Agent Actions / Tool Calls
     ↓
External Information
     ↓
Proposed Transaction
     ↓
FINSHIELD
     ↓
ALLOW / REVIEW / BLOCK
     ↓
Payment

What FINSHIELD does

FINSHIELD continuously evaluates four major things:

1. Intent

What did the user actually authorize?

2. Agent behavior

Is the agent behaving consistently with that objective?

3. Financial risk

Is the transaction, merchant, account, etc. risky?

4. Policy

Is the action within the user's financial permissions?

It combines AI/ML models + behavioral analysis + graph intelligence + deterministic financial policies to make the final decision.

The product itself

We're not just building an ML model.

We're building the complete product:

                    FINSHIELD
                        │
        ┌───────────────┼────────────────┐
        ↓               ↓                ↓
   AI Commerce      FINSHIELD        Financial
      Agent          Security         System
        │               │                │
        ↓               ↓                ↓
   Search/Buy      Risk/Policy       Payments
   Products        Intent            Orders
   Checkout        Analysis          Ledger

A user can:

 create an AI agent

 give it spending limits and permissions

 tell it what to buy

 let it search and make decisions

 watch its activity in real time

 approve/reject transactions

 see FINSHIELD's risk analysis

 investigate blocked transactions

 view their orders and payments

 inspect audit trails

We'll also have a Security Lab where we deliberately test the agent against attacks such as prompt injection, intent manipulation and budget escalation.

The R&D side

The really important part is that we won't simply claim:

"FINSHIELD is better."

We'll build competing approaches and experimentally compare them.

For example:

Rules
   vs
Traditional Fraud ML
   vs
LLM-based Judge
   vs
Agent Behavior Model
   vs
FINSHIELD

We'll measure things like:

 unsafe transactions prevented

 attack detection

 legitimate transactions incorrectly blocked

 intent-violation detection

 latency

 reliability

 explainability

So the project has both:

Product engineering

and

AI/ML research

The one-line explanation

If someone asks you "What is FINSHIELD?", say:

"FINSHIELD is a runtime security and risk-control platform for autonomous financial AI agents that verifies whether an agent's actions and transactions remain aligned with the user's original intent before allowing money to move."

And if they ask for an example:

"If I tell an AI agent to buy a laptop under ₹80,000 and the agent is manipulated into attempting a ₹1.5 lakh unrelated purchase, FINSHIELD detects the intent and behavioral deviation and blocks the transaction."

That's the project in its simplest form.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/ede74f18-37d2-40a4-9a4d-206154d9dbde).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
