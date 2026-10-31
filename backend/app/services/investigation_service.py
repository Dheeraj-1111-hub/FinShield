import uuid
import json
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_, func
from fastapi import HTTPException, status

from app.models.investigation import (
    Investigation,
    InvestigationEvidence,
    InvestigationTimelineEvent,
    InvestigationNote,
    SecurityEvent,
    InvestigationStatus,
    InvestigationPriority,
    InvestigationType,
    ResolutionType
)
from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.audit_service import AuditService
from app.schemas.investigation import (
    SecurityEventCreate,
    InvestigationCreate,
    InvestigationUpdate,
    InvestigationResolution,
    InvestigationEvidenceCreate,
    InvestigationTimelineEventCreate,
    InvestigationNoteCreate,
    InvestigationNoteUpdate,
    InvestigationResponse
)

class InvestigationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_security_event(self, event_in: SecurityEventCreate) -> SecurityEvent:
        db_event = SecurityEvent(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            **event_in.model_dump()
        )
        self.db.add(db_event)
        await self.db.commit()
        await self.db.refresh(db_event)
        
        return db_event

    async def create_investigation(self, inv_in: InvestigationCreate, workspace_id: str, created_by: Optional[str] = None) -> Investigation:
        db_inv = Investigation(
            id=f"inv_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            created_by=created_by,
            **inv_in.model_dump()
        )
        self.db.add(db_inv)
        await self.db.commit()
        await self.db.refresh(db_inv)
        
        await self.add_timeline_event(
            investigation_id=db_inv.id,
            workspace_id=workspace_id,
            event_in=InvestigationTimelineEventCreate(
                timestamp=db_inv.created_at,
                sequence_number=0,
                event_type="INVESTIGATION_CREATED",
                entity_type="INVESTIGATION",
                entity_id=db_inv.id,
                actor_type="USER" if created_by else "SYSTEM",
                actor_id=created_by,
                severity=db_inv.priority.value,
                title=f"Investigation Created: {db_inv.title}",
                description=db_inv.description
            )
        )
        
        audit_service = AuditService(self.db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type="INVESTIGATION_CREATED",
            event_category=EventCategory.INVESTIGATION,
            severity=EventSeverity.WARNING,
            actor_type=ActorType.USER if created_by else ActorType.SYSTEM,
            actor_id=created_by,
            entity_type="INVESTIGATION",
            entity_id=db_inv.id,
            payload={"title": db_inv.title, "priority": db_inv.priority.value}
        )
        await self.db.commit()
        
        return db_inv

    async def get_investigations(self, workspace_id: str, skip: int = 0, limit: int = 50, filters: dict = None) -> Tuple[List[Investigation], int]:
        query = select(Investigation).where(Investigation.workspace_id == workspace_id)
        
        if filters:
            if filters.get("status"):
                query = query.where(Investigation.status == filters["status"])
            if filters.get("priority"):
                query = query.where(Investigation.priority == filters["priority"])
            if filters.get("type"):
                query = query.where(Investigation.type == filters["type"])
            if filters.get("agent_id"):
                query = query.where(Investigation.agent_id == filters["agent_id"])
            if filters.get("agent_run_id"):
                query = query.where(Investigation.agent_run_id == filters["agent_run_id"])
            if filters.get("run_id"):
                query = query.where(Investigation.agent_run_id == filters["run_id"])
            if filters.get("assigned_to"):
                query = query.where(Investigation.assigned_to == filters["assigned_to"])
                
        # Get count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()
        
        # Get results
        query = query.order_by(desc(Investigation.created_at)).offset(skip).limit(limit)
        results = await self.db.execute(query)
        
        return results.scalars().all(), total

    async def get_investigation(self, investigation_id: str, workspace_id: str) -> Investigation:
        query = select(Investigation).where(
            Investigation.id == investigation_id,
            Investigation.workspace_id == workspace_id
        )
        result = await self.db.execute(query)
        inv = result.scalar_one_or_none()
        
        if not inv:
            raise HTTPException(status_code=404, detail="Investigation not found")
        return inv

    async def enrich_investigation(self, inv: Investigation) -> InvestigationResponse:
        from app.models.intent import Intent
        from app.models.agent_runtime import AgentRun, AgentAction
        from app.models.commerce import Order

        original_intent: Optional[str] = None
        executed_intent: Optional[str] = None
        proposed_action: Optional[str] = None
        decision_reason: Optional[str] = inv.description
        outcome: Optional[str] = None
        intent_alignment: Optional[int] = None
        divergence_signals: List[Dict[str, Any]] = []
        alignment_signals: List[Dict[str, Any]] = []

        # 1. Resolve Original User Intent
        if inv.intent_id:
            intent_obj = await self.db.get(Intent, inv.intent_id)
            if intent_obj:
                original_intent = intent_obj.natural_language_request or intent_obj.title

        if not original_intent and inv.agent_run_id:
            run_obj = await self.db.get(AgentRun, inv.agent_run_id)
            if run_obj and run_obj.input:
                original_intent = run_obj.input

        # 2. Resolve Agent Action
        action_obj = None
        if inv.agent_action_id:
            action_obj = await self.db.get(AgentAction, inv.agent_action_id)
        elif inv.agent_run_id:
            act_stmt = (
                select(AgentAction)
                .where(AgentAction.run_id == inv.agent_run_id)
                .order_by(desc(AgentAction.sequence_number))
            )
            act_res = await self.db.execute(act_stmt)
            actions = act_res.scalars().all()
            action_obj = next((a for a in actions if a.status.value in ["DENIED", "FAILED"]), actions[0] if actions else None)

        # 3. Format proposed / executed action
        if action_obj:
            tool_name = action_obj.tool_name
            order_id = None
            amount_str = ""
            if action_obj.input:
                inp = action_obj.input if isinstance(action_obj.input, dict) else (json.loads(action_obj.input) if isinstance(action_obj.input, str) else {})
                order_id = inp.get("order_id")
            if order_id:
                order_obj = await self.db.get(Order, order_id)
                if order_obj:
                    amount_str = f" (INR {order_obj.total:.2f})" if order_obj.currency == "INR" else f" ({order_obj.currency} {order_obj.total:.2f})"
                proposed_action = f"{tool_name} for order {order_id}{amount_str}"
            else:
                proposed_action = f"{tool_name}"
            executed_intent = proposed_action
        elif inv.agent_action_id or inv.agent_run_id:
            executed_intent = "pay_order"
            proposed_action = "pay_order"
        else:
            executed_intent = None
            proposed_action = None

        # 4. Resolve Decision Reason & Outcome (Human approval rejection vs Policy block)
        if action_obj and action_obj.error_message:
            decision_reason = action_obj.error_message
        elif inv.description:
            decision_reason = inv.description
        else:
            decision_reason = "Action blocked by Action Gate"

        is_approver_rejection = "rejected by approver" in (decision_reason or "").lower()
        if is_approver_rejection:
            outcome = "REJECTED"
        elif inv.status == InvestigationStatus.OPEN or "blocked" in (inv.title or "").lower():
            outcome = "BLOCKED"
        else:
            outcome = inv.status.value

        # 5. Calculate Intent Alignment & Divergence Signals from Actual Evidence
        if action_obj and action_obj.alignment_signals:
            raw_signals = action_obj.alignment_signals
            if isinstance(raw_signals, str):
                try:
                    raw_signals = json.loads(raw_signals)
                except Exception:
                    raw_signals = []
            if isinstance(raw_signals, list):
                divergence_signals = [s for s in raw_signals if s.get("status") != "ALIGNED"]
                alignment_signals = [s for s in raw_signals if s.get("status") == "ALIGNED"]
                if len(raw_signals) > 0:
                    intent_alignment = int((len(alignment_signals) / len(raw_signals)) * 100)
                else:
                    intent_alignment = 100 if action_obj.alignment_result == "ALIGNED" else 0
        elif action_obj and action_obj.alignment_result == "ALIGNED":
            intent_alignment = 100
            divergence_signals = []
            alignment_signals = [
                {"type": "ACTION", "status": "ALIGNED", "reason": f"Action '{action_obj.tool_name}' matches intent constraints"}
            ]
        elif is_approver_rejection:
            # Action was verified and sent for human review, then rejected by human approver
            intent_alignment = 100
            divergence_signals = []
            alignment_signals = [
                {"type": "ACTION", "status": "ALIGNED", "reason": "Proposed action was within authorized intent; execution was blocked by human approver rejection"}
            ]
        elif inv.type == InvestigationType.INTENT_DRIFT:
            intent_alignment = 0
            divergence_signals = [
                {"type": "INTENT_DRIFT", "reason": inv.description or "Action diverged from authorized intent"}
            ]
            alignment_signals = []
        else:
            intent_alignment = None
            divergence_signals = []
            alignment_signals = []

        resp = InvestigationResponse.model_validate(inv)
        resp.original_intent = original_intent
        resp.executed_intent = executed_intent
        resp.proposed_action = proposed_action
        resp.decision_reason = decision_reason
        resp.outcome = outcome
        resp.intent_alignment = intent_alignment
        resp.divergence_signals = divergence_signals
        resp.alignment_signals = alignment_signals
        return resp

    async def enrich_investigations(self, invs: List[Investigation]) -> List[InvestigationResponse]:
        return [await self.enrich_investigation(inv) for inv in invs]


    def _require_valid_transition(self, current: InvestigationStatus, next_status: InvestigationStatus):
        valid_transitions = {
            InvestigationStatus.OPEN: [InvestigationStatus.IN_REVIEW, InvestigationStatus.ESCALATED, InvestigationStatus.RESOLVED],
            InvestigationStatus.IN_REVIEW: [InvestigationStatus.RESOLVED, InvestigationStatus.ESCALATED],
            InvestigationStatus.ESCALATED: [InvestigationStatus.IN_REVIEW, InvestigationStatus.RESOLVED],
            InvestigationStatus.RESOLVED: [InvestigationStatus.CLOSED, InvestigationStatus.IN_REVIEW],
            InvestigationStatus.CLOSED: [InvestigationStatus.OPEN]
        }
        
        if next_status not in valid_transitions.get(current, []):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid transition from {current.value} to {next_status.value}"
            )

    async def update_status(self, investigation_id: str, workspace_id: str, status: InvestigationStatus, actor_id: str) -> Investigation:
        inv = await self.get_investigation(investigation_id, workspace_id)
        
        if inv.status == status:
            return inv
            
        self._require_valid_transition(inv.status, status)
        
        old_status = inv.status
        inv.status = status
        
        if status == InvestigationStatus.CLOSED:
            inv.closed_at = datetime.now(timezone.utc)
        elif old_status == InvestigationStatus.CLOSED and status == InvestigationStatus.OPEN:
            inv.closed_at = None
            inv.resolved_at = None
            inv.resolution = None
            inv.resolution_reason = None
            
        await self.db.commit()
        await self.db.refresh(inv)
        
        await self.add_timeline_event(
            investigation_id=inv.id,
            workspace_id=workspace_id,
            event_in=InvestigationTimelineEventCreate(
                timestamp=datetime.now(timezone.utc),
                event_type=f"STATUS_CHANGED_{status.value}",
                entity_type="INVESTIGATION",
                entity_id=inv.id,
                actor_type="USER",
                actor_id=actor_id,
                title=f"Status changed to {status.value}",
                description=f"Status updated from {old_status.value} to {status.value}"
            )
        )
        
        audit_service = AuditService(self.db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type="INVESTIGATION_STATUS_UPDATED",
            event_category=EventCategory.INVESTIGATION,
            severity=EventSeverity.INFO,
            actor_type=ActorType.USER,
            actor_id=actor_id,
            entity_type="INVESTIGATION",
            entity_id=inv.id,
            payload={"old_status": old_status.value, "new_status": status.value}
        )
        await self.db.commit()
        
        return inv

    async def resolve_investigation(self, investigation_id: str, workspace_id: str, resolution_in: InvestigationResolution, actor_id: str) -> Investigation:
        inv = await self.get_investigation(investigation_id, workspace_id)
        
        self._require_valid_transition(inv.status, InvestigationStatus.RESOLVED)
        
        inv.status = InvestigationStatus.RESOLVED
        inv.resolution = resolution_in.resolution
        inv.resolution_reason = resolution_in.resolution_reason
        inv.resolved_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(inv)
        
        await self.add_timeline_event(
            investigation_id=inv.id,
            workspace_id=workspace_id,
            event_in=InvestigationTimelineEventCreate(
                timestamp=datetime.now(timezone.utc),
                event_type="INVESTIGATION_RESOLVED",
                entity_type="INVESTIGATION",
                entity_id=inv.id,
                actor_type="USER",
                actor_id=actor_id,
                title=f"Investigation Resolved: {resolution_in.resolution.value}",
                description=resolution_in.resolution_reason
            )
        )
        
        audit_service = AuditService(self.db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type="INVESTIGATION_RESOLVED",
            event_category=EventCategory.INVESTIGATION,
            severity=EventSeverity.INFO,
            actor_type=ActorType.USER,
            actor_id=actor_id,
            entity_type="INVESTIGATION",
            entity_id=inv.id,
            payload={"resolution": resolution_in.resolution.value}
        )
        await self.db.commit()
        
        return inv

    async def assign_investigation(self, investigation_id: str, workspace_id: str, assignee_id: str, actor_id: str) -> Investigation:
        inv = await self.get_investigation(investigation_id, workspace_id)
        
        inv.assigned_to = assignee_id
        
        if inv.status == InvestigationStatus.OPEN:
            inv.status = InvestigationStatus.IN_REVIEW
            
        await self.db.commit()
        await self.db.refresh(inv)
        
        await self.add_timeline_event(
            investigation_id=inv.id,
            workspace_id=workspace_id,
            event_in=InvestigationTimelineEventCreate(
                timestamp=datetime.now(timezone.utc),
                event_type="INVESTIGATION_ASSIGNED",
                entity_type="INVESTIGATION",
                entity_id=inv.id,
                actor_type="USER",
                actor_id=actor_id,
                title="Investigation Assigned",
                description=f"Assigned to {assignee_id}"
            )
        )
        return inv

    async def add_evidence(self, investigation_id: str, workspace_id: str, evidence_in: InvestigationEvidenceCreate) -> InvestigationEvidence:
        await self.get_investigation(investigation_id, workspace_id)
        
        query = select(InvestigationEvidence).where(
            InvestigationEvidence.investigation_id == investigation_id
        ).order_by(desc(InvestigationEvidence.sequence_number)).limit(1)
        result = await self.db.execute(query)
        last_evidence = result.scalar_one_or_none()
        
        seq = (last_evidence.sequence_number + 1) if last_evidence else 0
        
        db_ev = InvestigationEvidence(
            id=f"evd_{uuid.uuid4().hex[:12]}",
            investigation_id=investigation_id,
            sequence_number=seq,
            **evidence_in.model_dump(exclude={"sequence_number"})
        )
        self.db.add(db_ev)
        await self.db.commit()
        await self.db.refresh(db_ev)
        
        await self.add_timeline_event(
            investigation_id=investigation_id,
            workspace_id=workspace_id,
            event_in=InvestigationTimelineEventCreate(
                timestamp=evidence_in.source_timestamp,
                event_type="EVIDENCE_COLLECTED",
                entity_type=evidence_in.entity_type,
                entity_id=evidence_in.entity_id,
                actor_type="SYSTEM",
                title=f"Evidence Attached: {evidence_in.title or evidence_in.entity_type}",
                description=evidence_in.description
            )
        )
        return db_ev

    async def get_evidence(self, investigation_id: str, workspace_id: str) -> List[InvestigationEvidence]:
        await self.get_investigation(investigation_id, workspace_id)
        query = select(InvestigationEvidence).where(
            InvestigationEvidence.investigation_id == investigation_id
        ).order_by(InvestigationEvidence.sequence_number)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def add_timeline_event(self, investigation_id: str, workspace_id: str, event_in: InvestigationTimelineEventCreate) -> InvestigationTimelineEvent:
        query = select(InvestigationTimelineEvent).where(
            InvestigationTimelineEvent.investigation_id == investigation_id
        ).order_by(desc(InvestigationTimelineEvent.sequence_number)).limit(1)
        result = await self.db.execute(query)
        last_evt = result.scalar_one_or_none()
        
        seq = (last_evt.sequence_number + 1) if last_evt else 0
        
        db_evt = InvestigationTimelineEvent(
            id=f"itev_{uuid.uuid4().hex[:12]}",
            investigation_id=investigation_id,
            sequence_number=seq,
            **event_in.model_dump(exclude={"sequence_number", "metadata"}, by_alias=False)
        )
        db_evt.metadata_ = event_in.metadata
        self.db.add(db_evt)
        await self.db.commit()
        await self.db.refresh(db_evt)
        return db_evt

    async def get_timeline(self, investigation_id: str, workspace_id: str) -> List[InvestigationTimelineEvent]:
        await self.get_investigation(investigation_id, workspace_id)
        query = select(InvestigationTimelineEvent).where(
            InvestigationTimelineEvent.investigation_id == investigation_id
        ).order_by(InvestigationTimelineEvent.timestamp, InvestigationTimelineEvent.sequence_number)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def add_note(self, investigation_id: str, workspace_id: str, note_in: InvestigationNoteCreate, author_id: str) -> InvestigationNote:
        await self.get_investigation(investigation_id, workspace_id)
        
        db_note = InvestigationNote(
            id=f"not_{uuid.uuid4().hex[:12]}",
            investigation_id=investigation_id,
            author_id=author_id,
            **note_in.model_dump()
        )
        self.db.add(db_note)
        await self.db.commit()
        await self.db.refresh(db_note)
        
        await self.add_timeline_event(
            investigation_id=investigation_id,
            workspace_id=workspace_id,
            event_in=InvestigationTimelineEventCreate(
                timestamp=datetime.now(timezone.utc),
                event_type="NOTE_ADDED",
                entity_type="NOTE",
                entity_id=db_note.id,
                actor_type="USER",
                actor_id=author_id,
                title="Analyst Note Added"
            )
        )
        return db_note

    async def get_notes(self, investigation_id: str, workspace_id: str) -> List[InvestigationNote]:
        await self.get_investigation(investigation_id, workspace_id)
        query = select(InvestigationNote).where(
            InvestigationNote.investigation_id == investigation_id
        ).order_by(InvestigationNote.created_at)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_investigation_by_run(self, workspace_id: str, run_id: str) -> Optional[Investigation]:
        stmt = (
            select(Investigation)
            .where(
                Investigation.workspace_id == workspace_id,
                Investigation.agent_run_id == run_id
            )
            .order_by(desc(Investigation.created_at))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def ensure_investigation_for_blocked_action(
        self,
        workspace_id: str,
        agent_id: str,
        agent_run_id: Optional[str],
        agent_action_id: Optional[str],
        gate_decision_id: str,
        action_type: str,
        explanation: str,
        reasons: List[str],
        snapshot: dict,
        intent_id: Optional[str] = None,
        authority_id: Optional[str] = None,
        risk_assessment_id: Optional[str] = None,
    ) -> Investigation:
        """
        Idempotently create or update an Investigation case for a blocked agent action.
        Prevents duplicate cases when repeated events occur for the same agent run.
        """
        # Prevent duplicate investigations for repeated actions in the same run
        if agent_run_id:
            existing = await self.get_investigation_by_run(workspace_id, agent_run_id)
            if existing:
                await self.add_timeline_event(
                    investigation_id=existing.id,
                    workspace_id=workspace_id,
                    event_in=InvestigationTimelineEventCreate(
                        timestamp=datetime.now(timezone.utc),
                        event_type="ACTION_BLOCKED_REPEAT",
                        entity_type="ACTION_GATE",
                        entity_id=gate_decision_id,
                        actor_type="SYSTEM",
                        severity=existing.priority.value,
                        title=f"Blocked Action: {action_type}",
                        description=explanation
                    )
                )
                return existing

        # Determine type
        inv_type = InvestigationType.SECURITY_EVENT
        if any("INTENT" in r for r in reasons):
            inv_type = InvestigationType.INTENT_DRIFT
        elif any("POLICY" in r or "CAPABILITY" in r for r in reasons):
            inv_type = InvestigationType.POLICY_VIOLATION
        elif any("AUTHORITY" in r for r in reasons):
            inv_type = InvestigationType.AUTHORITY_VIOLATION

        inv_id = f"inv_{uuid.uuid4().hex[:12]}"
        db_inv = Investigation(
            id=inv_id,
            workspace_id=workspace_id,
            title=f"Action Gate Blocked: {action_type} by Agent {agent_id}",
            description=explanation,
            type=inv_type,
            status=InvestigationStatus.OPEN,
            priority=InvestigationPriority.CRITICAL,
            source_type="ACTION_GATE",
            source_id=gate_decision_id,
            agent_id=agent_id,
            agent_run_id=agent_run_id,
            agent_action_id=agent_action_id,
            intent_id=intent_id,
            authority_id=authority_id,
            gate_decision_id=gate_decision_id,
            risk_assessment_id=risk_assessment_id
        )
        self.db.add(db_inv)
        await self.db.commit()
        await self.db.refresh(db_inv)

        # Initial timeline event
        await self.add_timeline_event(
            investigation_id=db_inv.id,
            workspace_id=workspace_id,
            event_in=InvestigationTimelineEventCreate(
                timestamp=datetime.now(timezone.utc),
                sequence_number=0,
                event_type="ACTION_BLOCKED",
                entity_type="INVESTIGATION",
                entity_id=db_inv.id,
                actor_type="SYSTEM",
                severity=db_inv.priority.value,
                title=f"Action Blocked: {action_type}",
                description=explanation
            )
        )

        # Attach snapshot evidence if present
        if snapshot:
            await self.add_evidence(
                investigation_id=db_inv.id,
                workspace_id=workspace_id,
                evidence_in=InvestigationEvidenceCreate(
                    evidence_type="GATE_DECISION",
                    entity_type="GATE_DECISION",
                    entity_id=gate_decision_id,
                    snapshot=snapshot,
                    title="Action Gate Decision Snapshot",
                    description=explanation,
                    source_timestamp=datetime.now(timezone.utc)
                )
            )

        # Audit event
        audit_service = AuditService(self.db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type="INVESTIGATION_CREATED",
            event_category=EventCategory.INVESTIGATION,
            severity=EventSeverity.WARNING,
            actor_type=ActorType.SYSTEM,
            entity_type="INVESTIGATION",
            entity_id=db_inv.id,
            payload={"title": db_inv.title, "priority": db_inv.priority.value, "run_id": agent_run_id}
        )
        await self.db.commit()
        return db_inv
