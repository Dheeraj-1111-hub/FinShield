# Phase 9: Risk Engine Walkthrough

> [!NOTE]
> We have fully implemented the Risk Engine (Phase 9) for FINSHIELD.

## Completed Work

1. **Risk Models and Schemas**: We successfully migrated away from the mock `SecurityEvent` model to a structured `RiskAssessment` model in SQLite using Alembic.
2. **Risk Signals**: We built deterministic evaluation logic for 4 key risk vectors in `backend/app/services/risk_signals`:
   - `intent.py`: Leverages Phase 8's Intent Engine to determine action alignment.
   - `authority.py`: Calculates proportional distance (proximity) to delegated limits.
   - `transaction.py`: Assesses raw transaction size impact.
   - `merchant.py`: Assesses counterparty trust.
   - `velocity_behavior.py`: Monitors high-frequency agent actions.
3. **Risk Orchestrator**: Aggregates signals into a final score (0-100) and maps it to a `RiskLevel` and `DecisionHint`.
4. **Agent Runtime Integration**: Updated `backend/app/services/agent_runtime_service.py` to route all agent actions through the Risk Orchestrator and block if the decision hint is `BLOCK_AND_ALERT`.
5. **Frontend API**: Refactored `risk.ts` to match the new endpoints for `RiskAssessment`.
6. **Risk Center UI**: Rebuilt `risk.tsx` with KPI dashboards, active threat feeds, and engine module status indicators.
7. **Threat Details Drawer**: Built a slide-out drawer to view full `feature_snapshots` and signal-level breakdowns.
8. **Risk Simulator**: Added a live interactive simulator (`RiskSimulator.tsx`) to manually test variables like transaction size and agent ID against the orchestrator.

## Verification

- The backend Alembic migration ran successfully and schema version `4f53eec10a35_add_riskassessment` is active.
- `RiskSimulator` is integrated in the frontend UI header.

## Next Steps

With Phase 9 completed, the Risk Engine is fully scoring agent actions deterministically. The next phase (Phase 10) will introduce the **Action Gate**, completing the ALLOW / REVIEW / BLOCK operational loop.
