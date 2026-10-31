import uuid
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.audit import AuditEvent, EventCategory, EventSeverity, ActorType
from app.core.canonical_json import compute_hash
from app.core.middleware import get_current_request_id

class AuditSanitizer:
    SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "client_secret", "access_token"}

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: ("[REDACTED]" if k.lower() in cls.SENSITIVE_KEYS else cls.sanitize(v)) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.sanitize(item) for item in data]
        return data

class AuditService:
    _workspace_locks: Dict[str, asyncio.Lock] = {}

    @classmethod
    def _get_workspace_lock(cls, workspace_id: str) -> asyncio.Lock:
        if workspace_id not in cls._workspace_locks:
            cls._workspace_locks[workspace_id] = asyncio.Lock()
        return cls._workspace_locks[workspace_id]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_next_sequence_and_hash(self, workspace_id: str) -> tuple[int, Optional[str]]:
        from sqlalchemy import text
        from app.models.audit import WorkspaceAuditSequence
        
        # Try to atomically increment and return
        stmt = text("""
            UPDATE workspace_audit_sequences 
            SET current_sequence = current_sequence + 1 
            WHERE workspace_id = :ws_id 
            RETURNING current_sequence, latest_event_hash
        """)
        result = await self.db.execute(stmt, {"ws_id": workspace_id})
        row = result.fetchone()
        
        if row:
            next_seq = row[0]
            prev_hash = row[1]
        else:
            # Workspace sequence doesn't exist, create it
            seq_row = WorkspaceAuditSequence(
                workspace_id=workspace_id,
                current_sequence=1,
                latest_event_hash=None
            )
            self.db.add(seq_row)
            await self.db.flush()
            next_seq = 1
            prev_hash = None
            
        return next_seq, prev_hash

    async def record_event(
        self,
        workspace_id: str,
        event_type: str,
        event_category: EventCategory,
        severity: EventSeverity,
        actor_type: ActorType,
        actor_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_run_id: Optional[str] = None,
        agent_action_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        before_snapshot: Optional[Dict[str, Any]] = None,
        after_snapshot: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        
        from app.core.middleware import get_current_request_id, get_current_correlation_id
        
        request_id = get_current_request_id()
        if not correlation_id:
            correlation_id = get_current_correlation_id()
        
        sanitized_payload = AuditSanitizer.sanitize(payload) if payload else None
        sanitized_before = AuditSanitizer.sanitize(before_snapshot) if before_snapshot else None
        sanitized_after = AuditSanitizer.sanitize(after_snapshot) if after_snapshot else None
        sanitized_metadata = AuditSanitizer.sanitize(metadata) if metadata else None

        async with self._get_workspace_lock(workspace_id):
            seq, prev_hash = await self._get_next_sequence_and_hash(workspace_id)
            
            # Prepare canonical data for hashing
            canonical_data = {
                "workspace_id": workspace_id,
                "event_type": event_type,
                "event_category": event_category.value,
                "severity": severity.value,
                "actor_type": actor_type.value,
                "actor_id": actor_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "workspace_sequence": seq,
                "payload": sanitized_payload,
                "before_snapshot": sanitized_before,
                "after_snapshot": sanitized_after,
            }
            
            event_hash = compute_hash(canonical_data, prev_hash)

            event = AuditEvent(
                id=f"evt_{uuid.uuid4().hex}",
                workspace_id=workspace_id,
                event_type=event_type,
                event_category=event_category,
                severity=severity,
                actor_type=actor_type,
                actor_id=actor_id,
                agent_id=agent_id,
                agent_run_id=agent_run_id,
                agent_action_id=agent_action_id,
                entity_type=entity_type,
                entity_id=entity_id,
                request_id=request_id,
                correlation_id=correlation_id,
                payload=sanitized_payload,
                before_snapshot=sanitized_before,
                after_snapshot=sanitized_after,
                metadata_=sanitized_metadata,
                workspace_sequence=seq,
                previous_event_hash=prev_hash,
                event_hash=event_hash,
                created_at=datetime.now(timezone.utc)
            )
            
            self.db.add(event)
            
            # Update the latest_event_hash
            from sqlalchemy import text
            stmt = text("""
                UPDATE workspace_audit_sequences 
                SET latest_event_hash = :hash 
                WHERE workspace_id = :ws_id
            """)
            await self.db.execute(stmt, {"hash": event_hash, "ws_id": workspace_id})
            await self.db.flush()
            
            return event

    async def verify_integrity(self, workspace_id: str) -> dict:
        from sqlalchemy import func
        from app.models.payment import Payment
        from app.models.commerce import Order
        from app.models.investigation import Investigation

        stmt = select(AuditEvent).where(AuditEvent.workspace_id == workspace_id).order_by(AuditEvent.workspace_sequence)
        result = await self.db.execute(stmt)
        events = result.scalars().all()
        
        if not events:
            # Check if domain activity exists in this workspace
            p_res = await self.db.execute(select(func.count(Payment.id)).where(Payment.workspace_id == workspace_id))
            p_count = p_res.scalar() or 0

            o_res = await self.db.execute(select(func.count(Order.id)).where(Order.workspace_id == workspace_id))
            o_count = o_res.scalar() or 0

            i_res = await self.db.execute(select(func.count(Investigation.id)).where(Investigation.workspace_id == workspace_id))
            i_count = i_res.scalar() or 0

            has_activity = (p_count > 0 or o_count > 0 or i_count > 0)
            if has_activity:
                return {
                    "valid": False,
                    "checked_events": 0,
                    "first_event": None,
                    "last_event": None,
                    "broken_links": [],
                    "chain_status": "EMPTY",
                    "completeness_status": "INCOMPLETE_INGESTION",
                    "completeness_note": f"Workspace has active records ({p_count} payments, {o_count} orders, {i_count} investigations) but 0 audit events. Event ingestion missing or broken."
                }
            return {
                "valid": True,
                "checked_events": 0,
                "first_event": None,
                "last_event": None,
                "broken_links": [],
                "chain_status": "EMPTY",
                "completeness_status": "NO_EVENTS",
                "completeness_note": "No audit events recorded for this workspace. No hash chain exists to verify."
            }
            
        broken_links = []
        expected_prev_hash = None
        expected_seq = 1
        
        for event in events:
            if event.workspace_sequence != expected_seq:
                broken_links.append({"event_id": event.id, "reason": "SEQUENCE_GAP", "expected": expected_seq, "actual": event.workspace_sequence})
            
            if event.previous_event_hash != expected_prev_hash:
                broken_links.append({"event_id": event.id, "reason": "PREVIOUS_HASH_MISMATCH"})
                
            canonical_data = {
                "workspace_id": event.workspace_id,
                "event_type": event.event_type,
                "event_category": event.event_category.value,
                "severity": event.severity.value,
                "actor_type": event.actor_type.value,
                "actor_id": event.actor_id,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "workspace_sequence": event.workspace_sequence,
                "payload": event.payload,
                "before_snapshot": event.before_snapshot,
                "after_snapshot": event.after_snapshot,
            }
            computed_hash = compute_hash(canonical_data, event.previous_event_hash)
            
            if computed_hash != event.event_hash:
                broken_links.append({"event_id": event.id, "reason": "HASH_MISMATCH"})
                
            expected_prev_hash = event.event_hash
            expected_seq = event.workspace_sequence + 1
            
        is_valid = len(broken_links) == 0
        chain_status = "VALID" if is_valid else "TAMPERED"
        completeness_status = "CHAIN_VALID_ONLY" if is_valid else "TAMPERED"
        completeness_note = (
            "Available cryptographic hash chain is valid and untampered across recorded events. Note: A valid hash chain confirms ledger immutability of existing events, but does not guarantee completeness of external operations."
            if is_valid
            else f"Cryptographic integrity violation: {len(broken_links)} broken link(s) or sequence gap(s) detected in audit ledger."
        )

        return {
            "valid": is_valid,
            "checked_events": len(events),
            "first_event": events[0].id,
            "last_event": events[-1].id,
            "broken_links": broken_links,
            "chain_status": chain_status,
            "completeness_status": completeness_status,
            "completeness_note": completeness_note
        }

