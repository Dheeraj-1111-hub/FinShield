# Phase 2 — Complete Testing Plan

This document tracks the objective completion record of Phase 2 (Workspace & Settings) validation. Phase 2 is not complete until every item is checked and verified in a clean database environment.

## The Test Matrix

| Area          | Test                        | Result |
|---------------|-----------------------------|--------|
| Auth          | Login                       | ⬜ |
| Auth          | Logout                      | ⬜ |
| Auth          | Protected settings          | ⬜ |
| Profile       | Read profile                | ⬜ |
| Profile       | Update profile              | ⬜ |
| Profile       | Invalid profile             | ⬜ |
| Workspace     | Read workspace              | ⬜ |
| Workspace     | Update workspace            | ⬜ |
| Workspace     | Slug uniqueness             | ⬜ |
| Config        | Currency                    | ⬜ |
| Config        | Timezone                    | ⬜ |
| Config        | Risk thresholds             | ⬜ |
| Config        | Notifications               | ⬜ |
| Config        | Security                    | ⬜ |
| Config        | Retention                   | ⬜ |
| Validation    | Invalid payloads            | ⬜ |
| Authorization | Owner update                | ⬜ |
| Authorization | Member blocked              | ⬜ |
| Security      | IDOR                        | ⬜ |
| Security      | Cross-workspace isolation   | ⬜ |
| Security      | API bypass                  | ⬜ |
| Database      | Persistence                 | ⬜ |
| Audit         | Configuration changes       | ⬜ |
| Reliability   | API failure                 | ⬜ |
| Reliability   | Network failure             | ⬜ |
| UX            | Loading state               | ⬜ |
| UX            | Error state                 | ⬜ |
| UX            | Unsaved changes             | ⬜ |
| UX            | Duplicate save              | ⬜ |
| Concurrency   | Stale update                | ⬜ |
| E2E           | User A journey              | ⬜ |
| E2E           | User B isolation            | ⬜ |
| Deployment    | Clean DB                    | ⬜ |
| Deployment    | Docker startup              | ⬜ |
| Regression    | Phase 1 still works         | ⬜ |

## Automated Test Pyramid

- **E2E (Playwright)**: Full browser journeys.
- **Integration**: Services to Database mapping.
- **API/Security (Pytest)**: Endpoint logic, 401/403/IDOR, validation constraints.
- **Unit**: Individual validator rules.

## The Clean Database Final Test
The final sign-off is a full deployment and manual E2E run on a completely fresh `finshield.db`.
