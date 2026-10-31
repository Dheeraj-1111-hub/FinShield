from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.core.dependencies import get_current_workspace
from app.models.workspace import Workspace
from app.services.investigation_service import InvestigationService
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationResponse,
    InvestigationUpdate,
    InvestigationResolution,
    InvestigationEvidenceCreate,
    InvestigationEvidenceResponse,
    InvestigationTimelineEventResponse,
    InvestigationNoteCreate,
    InvestigationNoteResponse,
    InvestigationExportResponse,
    SecurityEventCreate,
    SecurityEventResponse
)
from app.models.investigation import InvestigationStatus

router = APIRouter(tags=["investigations"])

@router.post("/events", response_model=SecurityEventResponse)
async def create_security_event(
    event_in: SecurityEventCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    event_in.workspace_id = workspace.id
    svc = InvestigationService(db)
    return await svc.create_security_event(event_in)

@router.get("", response_model=List[InvestigationResponse])
async def get_investigations(
    skip: int = 0,
    limit: int = 50,
    status: Optional[InvestigationStatus] = None,
    priority: Optional[str] = None,
    type: Optional[str] = None,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    filters = {
        "status": status,
        "priority": priority,
        "type": type,
        "agent_id": agent_id,
        "run_id": run_id,
        "assigned_to": assigned_to
    }
    results, _ = await svc.get_investigations(workspace.id, skip, limit, filters)
    return await svc.enrich_investigations(results)

@router.get("/by-run/{run_id}", response_model=Optional[InvestigationResponse])
async def get_investigation_by_run(
    run_id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    inv = await svc.get_investigation_by_run(workspace.id, run_id)
    if inv:
        return await svc.enrich_investigation(inv)

    # Check if this run exists in this workspace and was blocked
    from app.models.agent_runtime import AgentRun, AgentAction, ActionStatus, RunStatus
    from app.models.gate import GateDecision
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    run_stmt = select(AgentRun).options(joinedload(AgentRun.actions)).where(AgentRun.id == run_id, AgentRun.workspace_id == workspace.id)
    run_res = await db.execute(run_stmt)
    run = run_res.unique().scalar_one_or_none()

    if run and (run.status == RunStatus.BLOCKED or any(a.status == ActionStatus.DENIED for a in (run.actions or []))):
        denied_action = next((a for a in (run.actions or []) if a.status == ActionStatus.DENIED), None)
        action_name = denied_action.tool_name if denied_action else "agent_action"
        action_id = denied_action.id if denied_action else None

        gate_dec = None
        if action_id:
            gate_stmt_act = select(GateDecision).where(GateDecision.agent_action_id == action_id).order_by(GateDecision.created_at.desc())
            gate_res_act = await db.execute(gate_stmt_act)
            gate_dec = gate_res_act.scalars().first()

        if not gate_dec:
            gate_stmt = select(GateDecision).where(GateDecision.agent_run_id == run.id).order_by(GateDecision.created_at.desc())
            gate_res = await db.execute(gate_stmt)
            gate_dec = gate_res.scalars().first()

        gate_id = gate_dec.id if gate_dec else f"gdec_{run.id}"
        explanation = (denied_action.error_message if (denied_action and denied_action.error_message) else (gate_dec.explanation if gate_dec else "Action was blocked by policy"))
        reasons = (gate_dec.reason_codes if (gate_dec and hasattr(gate_dec, 'reason_codes') and gate_dec.reason_codes) else (getattr(gate_dec, 'reasons', None) or ["ACTION_BLOCKED"]))
        snapshot = (gate_dec.evaluation_snapshot if (gate_dec and hasattr(gate_dec, 'evaluation_snapshot') and gate_dec.evaluation_snapshot) else (getattr(gate_dec, 'snapshot', None) or {}))

        inv = await svc.ensure_investigation_for_blocked_action(
            workspace_id=workspace.id,
            agent_id=run.agent_id,
            agent_run_id=run.id,
            agent_action_id=action_id,
            gate_decision_id=gate_id,
            action_type=action_name,
            explanation=explanation,
            reasons=reasons,
            snapshot=snapshot,
            intent_id=run.intent_id,
            authority_id=run.authority_id,
        )
        return await svc.enrich_investigation(inv)

    return None

@router.post("", response_model=InvestigationResponse)
async def create_investigation(
    inv_in: InvestigationCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    # in a real app, actor_id comes from auth, here we mock it
    inv = await svc.create_investigation(inv_in, workspace.id, created_by="user_mock")
    return await svc.enrich_investigation(inv)

@router.get("/{id}", response_model=InvestigationResponse)
async def get_investigation(
    id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    inv = await svc.get_investigation(id, workspace.id)
    return await svc.enrich_investigation(inv)

@router.post("/{id}/start", response_model=InvestigationResponse)
async def start_investigation(
    id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.update_status(id, workspace.id, InvestigationStatus.IN_REVIEW, "user_mock")

@router.post("/{id}/escalate", response_model=InvestigationResponse)
async def escalate_investigation(
    id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.update_status(id, workspace.id, InvestigationStatus.ESCALATED, "user_mock")

@router.post("/{id}/resolve", response_model=InvestigationResponse)
async def resolve_investigation(
    id: str,
    resolution_in: InvestigationResolution,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.resolve_investigation(id, workspace.id, resolution_in, "user_mock")

@router.post("/{id}/close", response_model=InvestigationResponse)
async def close_investigation(
    id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.update_status(id, workspace.id, InvestigationStatus.CLOSED, "user_mock")

@router.post("/{id}/reopen", response_model=InvestigationResponse)
async def reopen_investigation(
    id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.update_status(id, workspace.id, InvestigationStatus.OPEN, "user_mock")

class AssignRequest(BaseModel):
    assigned_to: str

@router.post("/{id}/assign", response_model=InvestigationResponse)
async def assign_investigation(
    id: str,
    req: AssignRequest,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.assign_investigation(id, workspace.id, req.assigned_to, "user_mock")

@router.get("/{id}/evidence", response_model=List[InvestigationEvidenceResponse])
async def get_evidence(
    id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.get_evidence(id, workspace.id)

@router.get("/{id}/timeline", response_model=List[InvestigationTimelineEventResponse])
async def get_timeline(
    id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.get_timeline(id, workspace.id)

@router.get("/{id}/notes", response_model=List[InvestigationNoteResponse])
async def get_notes(
    id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.get_notes(id, workspace.id)

@router.post("/{id}/notes", response_model=InvestigationNoteResponse)
async def add_note(
    id: str,
    note_in: InvestigationNoteCreate,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    return await svc.add_note(id, workspace.id, note_in, "user_mock")

@router.get("/{id}/export", response_model=InvestigationExportResponse)
async def export_investigation(
    id: str,
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    svc = InvestigationService(db)
    inv = await svc.get_investigation(id, workspace.id)
    inv_enriched = await svc.enrich_investigation(inv)
    evidence = await svc.get_evidence(id, workspace.id)
    timeline = await svc.get_timeline(id, workspace.id)
    notes = await svc.get_notes(id, workspace.id)
    
    return {
        "investigation": inv_enriched,
        "evidence": evidence,
        "timeline": timeline,
        "notes": notes
    }
