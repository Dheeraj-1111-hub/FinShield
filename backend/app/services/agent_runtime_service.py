import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.agent_runtime import AgentRun, AgentAction, RunStatus, ActionStatus
from app.models.agent import Agent, AgentStatus
from app.models.audit import EventCategory, EventSeverity, ActorType
from app.services.audit_service import AuditService
from app.models.authority import DelegatedAuthority, AuthorityStatus
from app.models.intent import Intent, IntentStatus, IntentType
from app.services.tool_registry import registry, ToolDefinition
from app.services.commerce_service import CommerceService
from app.schemas.commerce import CartCreate, CartItemCreate, OrderCreate
from app.services.alignment_engine import evaluate_alignment
from app.services.authority_evaluator import evaluate_authority
from app.services.risk_orchestrator import evaluate_risk
from app.models.risk import RiskLevel, RiskAssessment
from app.schemas.risk import RiskEvaluateRequest, TransactionContext
from app.services.action_gate_service import ActionGateService
from app.models.gate import DecisionResult, ApprovalRequest, ApprovalStatus
from app.schemas.execution_context import ExecutionContext

class AgentRuntimeService:

    @staticmethod
    async def _log_agent_activity(db: AsyncSession, agent_id: str, workspace_id: str, action: str, actor_id: Optional[str] = None, details: dict = None):
        audit_service = AuditService(db)
        await audit_service.record_event(
            workspace_id=workspace_id,
            event_type=action,
            event_category=EventCategory.AGENT,
            severity=EventSeverity.INFO,
            actor_type=ActorType.USER if actor_id else ActorType.SYSTEM,
            actor_id=actor_id,
            agent_id=agent_id,
            entity_type="AGENT",
            entity_id=agent_id,
            payload=details or {}
        )

    @staticmethod
    async def create_run(
        db: AsyncSession,
        workspace_id: str,
        agent_id: str,
        input_text: str,
        trigger_type: str = "API",
        authority_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AgentRun:
        # Verify agent exists and is ACTIVE
        stmt = select(Agent).where(Agent.id == agent_id, Agent.workspace_id == workspace_id)
        result = await db.execute(stmt)
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if agent.status != AgentStatus.ACTIVE:
            raise HTTPException(status_code=403, detail=f"Cannot execute runs for agent in {agent.status} state")

        # Resolve active authority for this agent in workspace if not explicitly provided
        authority = None
        if authority_id:
            stmt_a = select(DelegatedAuthority).where(
                DelegatedAuthority.id == authority_id,
                DelegatedAuthority.workspace_id == workspace_id,
                DelegatedAuthority.agent_id == agent_id,
            )
            res_a = await db.execute(stmt_a)
            authority = res_a.scalar_one_or_none()
            if not authority:
                raise HTTPException(status_code=404, detail="Authority not found or not bound to this agent")
        else:
            # Query for an active delegated authority bound to this agent
            from app.services.authority_service import get_active_authority_for_agent
            authority = await get_active_authority_for_agent(db, workspace_id, agent_id)
            if authority:
                authority_id = authority.id

        # Determine run intent from user prompt (or fallback to authority intent)
        from app.services.intent_extractor import extract_intent
        from app.models.intent import Intent, IntentStatus

        run_intent_id = None
        is_search_only_request = False
        if input_text and input_text.strip():
            from app.services.intent_extractor import _is_search_only_or_prohibits_purchase
            is_search_only_request = _is_search_only_or_prohibits_purchase(input_text.strip())

        if is_search_only_request:
            # A read/search-only intent or explicit negative purchase constraint in the prompt
            # must strictly override any broad authority intent for this run.
            proposal = extract_intent(input_text.strip())
            run_intent = Intent(
                workspace_id=workspace_id,
                agent_id=agent_id,
                status=IntentStatus.ACTIVE,
                intent_type=proposal.proposed_type,
                title=proposal.proposed_title,
                natural_language_request=input_text.strip(),
                structured_constraints=proposal.proposed_constraints.model_dump(),
                version=1,
            )
            db.add(run_intent)
            await db.flush()
            run_intent_id = run_intent.id
        elif authority and authority.intent_id:
            # Use the explicitly delegated authority's configured intent
            run_intent_id = authority.intent_id
        else:
            # Check if agent has an active intent bound in the workspace
            stmt_active_intent = (
                select(Intent)
                .where(
                    Intent.workspace_id == workspace_id,
                    Intent.agent_id == agent_id,
                    Intent.status == IntentStatus.ACTIVE,
                )
                .order_by(Intent.created_at.desc())
            )
            res_intent = await db.execute(stmt_active_intent)
            active_intent = res_intent.scalars().first()
            if active_intent and not is_search_only_request:
                run_intent_id = active_intent.id
            elif input_text and input_text.strip():
                # If no authority intent exists, extract intent from prompt
                proposal = extract_intent(input_text.strip())
                run_intent = Intent(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    status=IntentStatus.ACTIVE,
                    intent_type=proposal.proposed_type,
                    title=proposal.proposed_title,
                    natural_language_request=input_text.strip(),
                    structured_constraints=proposal.proposed_constraints.model_dump(),
                    version=1,
                )
                db.add(run_intent)
                await db.flush()
                run_intent_id = run_intent.id

        run = AgentRun(
            workspace_id=workspace_id,
            agent_id=agent_id,
            input=input_text,
            trigger_type=trigger_type,
            status=RunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            intent_id=run_intent_id,
            authority_id=authority_id,
            session_id=session_id,
        )
        db.add(run)
        await db.flush()
        
        await AgentRuntimeService._log_agent_activity(db, agent_id, workspace_id, "AGENT_RUN_CREATED", details={"run_id": run.id})
        await AgentRuntimeService._log_agent_activity(db, agent_id, workspace_id, "AGENT_RUN_STARTED", details={"run_id": run.id})
        
        agent.last_active_at = datetime.now(timezone.utc)
        agent.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        return await AgentRuntimeService.get_run(db, workspace_id, run.id)

    @staticmethod
    async def get_run(db: AsyncSession, workspace_id: str, run_id: str) -> AgentRun:
        stmt = select(AgentRun).options(selectinload(AgentRun.actions)).where(AgentRun.id == run_id, AgentRun.workspace_id == workspace_id)
        result = await db.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    @staticmethod
    async def list_runs(db: AsyncSession, workspace_id: str, agent_id: str, skip: int = 0, limit: int = 100) -> List[AgentRun]:
        stmt = select(AgentRun).options(selectinload(AgentRun.actions)).where(AgentRun.agent_id == agent_id, AgentRun.workspace_id == workspace_id).order_by(AgentRun.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def cancel_run(db: AsyncSession, workspace_id: str, run_id: str) -> AgentRun:
        run = await AgentRuntimeService.get_run(db, workspace_id, run_id)
        if run.status in [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail="Run already finished")
            
        run.status = RunStatus.CANCELLED
        run.completed_at = datetime.now(timezone.utc)
        
        await AgentRuntimeService._log_agent_activity(db, run.agent_id, workspace_id, "AGENT_RUN_CANCELLED", details={"run_id": run.id})
        await db.commit()
        await db.refresh(run)
        return run

    @staticmethod
    async def execute_action(db: AsyncSession, workspace_id: str, run_id: str, tool_name: str, tool_input: dict) -> AgentAction:
        run = await AgentRuntimeService.get_run(db, workspace_id, run_id)
        if run.status == RunStatus.WAITING_FOR_APPROVAL:
            stmt_active_appr = select(ApprovalRequest).where(
                ApprovalRequest.agent_run_id == run_id,
                ApprovalRequest.status == ApprovalStatus.PENDING
            )
            res_active_appr = await db.execute(stmt_active_appr)
            if not res_active_appr.scalars().first():
                run.status = RunStatus.RUNNING
                await db.commit()
            else:
                raise HTTPException(status_code=400, detail="Cannot execute new action while a previous action is pending approval")

        if run.status != RunStatus.RUNNING:
            raise HTTPException(status_code=400, detail=f"Cannot execute action. Run is in {run.status} state")

        # Guard against executing new actions while an existing action in this run awaits approval
        stmt_active_appr = select(ApprovalRequest).where(
            ApprovalRequest.agent_run_id == run_id,
            ApprovalRequest.status == ApprovalStatus.PENDING
        )
        res_active_appr = await db.execute(stmt_active_appr)
        if res_active_appr.scalars().first():
            run.status = RunStatus.WAITING_FOR_APPROVAL
            await db.commit()
            raise HTTPException(status_code=400, detail="Cannot execute new action while a previous action is pending approval")

        agent = await db.get(Agent, run.agent_id)
        
        # Get next sequence number
        stmt_seq = select(AgentAction).where(AgentAction.run_id == run_id).order_by(AgentAction.sequence_number.desc())
        result_seq = await db.execute(stmt_seq)
        last_action = result_seq.scalars().first()
        next_seq = (last_action.sequence_number + 1) if last_action else 1
        
        if next_seq > 50:
            # Hard limit to prevent infinite loops
            run.status = RunStatus.FAILED
            run.error_code = "MAX_ACTIONS_EXCEEDED"
            run.error_message = "Agent run exceeded maximum number of actions (50)"
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise HTTPException(status_code=400, detail="Max actions exceeded")

        action = AgentAction(
            run_id=run.id,
            sequence_number=next_seq,
            tool_name=tool_name,
            input=tool_input,
            status=ActionStatus.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        db.add(action)
        await db.flush()
        
        await AgentRuntimeService._log_agent_activity(db, agent.id, workspace_id, "AGENT_ACTION_STARTED", details={"run_id": run.id, "action_id": action.id, "tool_name": tool_name})
        
        try:
            tool_def = registry.get_tool(tool_name)
        except ValueError:
            action.status = ActionStatus.FAILED
            action.error_code = "UNKNOWN_TOOL"
            action.error_message = f"Tool {tool_name} is not registered"
            action.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise HTTPException(status_code=400, detail="Unknown tool")

        # ── PHASE 10: Action Gate ──────────────────────────────
        gate = ActionGateService(db)
        
        # We run authority & alignment for state collection (and backwards compatibility)
        run_authority_id = run.authority_id
        active_authority = None
        active_intent = None

        if run_authority_id:
            stmt_auth = select(DelegatedAuthority).where(
                DelegatedAuthority.id == run_authority_id,
                DelegatedAuthority.workspace_id == workspace_id,
            )
            res_auth = await db.execute(stmt_auth)
            active_authority = res_auth.scalar_one_or_none()
        else:
            # Fallback to look up active authority for this agent
            from app.services.authority_service import get_active_authority_for_agent
            active_authority = await get_active_authority_for_agent(db, workspace_id, agent.id)
            if active_authority:
                run.authority_id = active_authority.id

        # Intent resolution: Run-level intent takes absolute precedence over authority template intent
        if run.intent_id:
            active_intent = await db.get(Intent, run.intent_id)
        elif active_authority and active_authority.intent_id:
            active_intent = await db.get(Intent, active_authority.intent_id)
            run.intent_id = active_authority.intent_id

        # Fail closed: If run specified an intent_id but the Intent record does not exist
        if run.intent_id and not active_intent:
            action.status = ActionStatus.DENIED
            action.error_code = "INTENT_NOT_FOUND"
            action.error_message = f"Intent {run.intent_id} could not be resolved. Failing closed."
            action.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise HTTPException(status_code=403, detail="Intent not found. Failing closed.")

        if active_authority:
            # Stamp action with authority context BEFORE checking authorized
            action.authority_id = active_authority.id
            action.authority_version = active_authority.version

        if active_intent:
            action.intent_id = active_intent.id
            action.intent_version = active_intent.version
                
        # Enforce that actions beyond safe tools require delegated authority
        from app.services.capabilities import TOOL_CAPABILITY_REQUIREMENTS, check_missing_capabilities
        
        req_cap_sets = TOOL_CAPABILITY_REQUIREMENTS.get(tool_name, [{cap} for cap in tool_def.required_capabilities])

        if not active_authority:
            # Define safe tools that do not require purchase authority
            safe_tools = {"search_products", "list_products", "get_product"}
            if tool_name not in safe_tools:
                missing_capabilities = ["DELEGATED_AUTHORITY_REQUIRED"]
            else:
                missing_capabilities = []
        else:
            # Check agent capability (must have delegated capability in its own configuration)
            agent_caps = set(agent.capabilities or [])
            missing_capabilities = check_missing_capabilities(req_cap_sets, agent_caps)
            
            # Also check authority capability if agent has it
            if not missing_capabilities:
                auth_caps = set(active_authority.allowed_capabilities or [])
                missing_capabilities = check_missing_capabilities(req_cap_sets, auth_caps)
            
        if missing_capabilities:
            action.status = ActionStatus.DENIED
            action.error_code = "CAPABILITY_DENIED"
            action.error_message = f"Authority denied. Agent or Authority lacks required capabilities: {', '.join(missing_capabilities)}"
            action.completed_at = datetime.now(timezone.utc)
            run.status = RunStatus.BLOCKED
            run.error_code = "CAPABILITY_DENIED"
            run.error_message = action.error_message
            run.completed_at = datetime.now(timezone.utc)
            await AgentRuntimeService._log_agent_activity(db, agent.id, workspace_id, "AGENT_TOOL_DENIED", details={"run_id": run.id, "action_id": action.id, "tool_name": tool_name})
            await db.commit()
            raise HTTPException(status_code=403, detail="Authority denied: Agent or Authority lacks capability to execute this tool")

        # Authoritative Intent Evaluation
        SIDE_EFFECTING_COMMERCE_ACTIONS = {
            "create_cart", "add_to_cart", "checkout", "pay_order",
            "CREATE_CART", "ADD_TO_CART", "ADD_CART_ITEM", "MANAGE_CART",
            "CHECKOUT", "CREATE_ORDER", "PAY_ORDER", "EXECUTE_PAYMENT"
        }

        is_search_only_intent = False
        is_prohibited_before_hydration = False

        from app.services.intent_extractor import _is_search_only_or_prohibits_purchase
        if run.input and _is_search_only_or_prohibits_purchase(run.input.strip()):
            is_search_only_intent = True

        if active_intent:
            if not is_search_only_intent:
                if active_intent.natural_language_request and _is_search_only_or_prohibits_purchase(active_intent.natural_language_request):
                    is_search_only_intent = True
                elif active_intent.structured_constraints:
                    is_search_only_intent = bool(
                        active_intent.structured_constraints.get("search_only") or
                        active_intent.structured_constraints.get("read_only") or
                        ("create_cart" in (active_intent.structured_constraints.get("prohibited_actions") or []))
                    )
            if is_search_only_intent and tool_name in SIDE_EFFECTING_COMMERCE_ACTIONS:
                is_prohibited_before_hydration = True
                action.alignment_result = "MISALIGNED"
                action.alignment_signals = [{
                    "type": "ACTION",
                    "status": "MISALIGNED",
                    "reason": f"Tool '{tool_name}' is prohibited: Intent is strictly read/search-only and forbids all cart, checkout, order, and payment actions."
                }]
            elif tool_name in SIDE_EFFECTING_COMMERCE_ACTIONS:
                from app.services.capabilities import get_equivalent_action_names, normalize_action_name
                constraints = active_intent.structured_constraints or {}
                prohibited_actions = constraints.get("prohibited_actions", [])
                allowed_actions = constraints.get("allowed_actions", [])
                action_equivs = get_equivalent_action_names(tool_name)
                action_norm = normalize_action_name(tool_name)

                if prohibited_actions:
                    prohibited_equivs = set()
                    for a in prohibited_actions:
                        prohibited_equivs.update(get_equivalent_action_names(a))
                    prohibited_norm = {normalize_action_name(a) for a in prohibited_actions}
                    if bool(action_equivs & prohibited_equivs) or (action_norm in prohibited_norm):
                        is_prohibited_before_hydration = True
                        action.alignment_result = "MISALIGNED"
                        action.alignment_signals = [{
                            "type": "ACTION",
                            "status": "MISALIGNED",
                            "reason": f"Tool '{tool_name}' is explicitly prohibited by intent."
                        }]
                if not is_prohibited_before_hydration and allowed_actions:
                    allowed_equivs = set()
                    for a in allowed_actions:
                        allowed_equivs.update(get_equivalent_action_names(a))
                    allowed_norm = {normalize_action_name(a) for a in allowed_actions}
                    if not (bool(action_equivs & allowed_equivs) or (action_norm in allowed_norm)):
                        is_prohibited_before_hydration = True
                        action.alignment_result = "MISALIGNED"
                        action.alignment_signals = [{
                            "type": "ACTION",
                            "status": "MISALIGNED",
                            "reason": f"Tool '{tool_name}' is not in allowed actions: {allowed_actions}."
                        }]
        elif tool_name in SIDE_EFFECTING_COMMERCE_ACTIONS:
            # Missing intent for side-effecting tools fails closed
            is_prohibited_before_hydration = True
            action.alignment_result = "MISALIGNED"
            action.alignment_signals = [{
                "type": "ACTION",
                "status": "MISALIGNED",
                "reason": f"Side-effecting tool '{tool_name}' requires an active intent, but none was bound. Failing closed."
            }]

        # HARD GATING: Prohibit side-effecting tools immediately before hydration if search-only, missing intent, or prohibited
        if is_prohibited_before_hydration:
            gate_decision = await gate.evaluate(
                workspace_id=workspace_id,
                agent_id=agent.id,
                agent_run_id=run.id,
                agent_action_id=action.id,
                intent_id=active_intent.id if active_intent else None,
                authority_id=active_authority.id if active_authority else None,
                risk_assessment_id=None,
                transaction=None,
                is_revalidation=False,
                approval_id=None,
                alignment_result=action.alignment_result,
                alignment_signals=action.alignment_signals,
                action_type=tool_name
            )
            if not action.metadata_:
                action.metadata_ = {}
            action.metadata_["gate_decision_id"] = gate_decision.id
            action.metadata_["gate_decision"] = gate_decision.decision.value if hasattr(gate_decision.decision, "value") else str(gate_decision.decision)
            action.status = ActionStatus.DENIED
            action.error_code = gate_decision.reason_codes[0] if gate_decision.reason_codes else "INTENT_MISALIGNED_SEARCH_ONLY"
            action.error_message = gate_decision.explanation
            action.completed_at = datetime.now(timezone.utc)
            run.status = RunStatus.BLOCKED
            run.error_code = action.error_code
            run.error_message = f"Run stopped: Action '{tool_name}' violated intent constraints ({gate_decision.explanation})"
            run.completed_at = datetime.now(timezone.utc)
            await AgentRuntimeService._log_agent_activity(
                db, agent.id, workspace_id, "AGENT_TOOL_DENIED",
                details={"run_id": run.id, "action_id": action.id, "tool_name": tool_name, "reason": gate_decision.explanation}
            )
            await db.commit()
            raise HTTPException(status_code=403, detail=f"Action blocked by Action Gate: {gate_decision.explanation}")

        # Read-only operations (search_products, list_products, get_product) do not execute financial mutations
        # and are not evaluated by the financial Action Gate. They execute directly with NOT EVALUATED gate decision.
        is_read_only = tool_name in ["search_products", "list_products", "get_product"]
        if is_read_only:
            if not action.metadata_:
                action.metadata_ = {}
            action.metadata_["gate_decision"] = "NOT EVALUATED"
            action.metadata_["is_read_only"] = True

            try:
                validated_input = tool_def.input_schema(**tool_input)
            except ValidationError as e:
                action.status = ActionStatus.FAILED
                action.error_code = "INVALID_INPUT"
                action.error_message = str(e)
                action.completed_at = datetime.now(timezone.utc)
                await db.commit()
                raise HTTPException(status_code=400, detail=f"Invalid tool input: {str(e)}")

            try:
                output_data = await AgentRuntimeService._execute_tool_logic(
                    db, workspace_id, agent.id, tool_name, validated_input, tool_input, 
                    run_id=run.id, action_id=action.id, signed_decision_token=None
                )
                action.status = ActionStatus.SUCCESS
                action.output = output_data
                action.completed_at = datetime.now(timezone.utc)
                await AgentRuntimeService._log_agent_activity(db, agent.id, workspace_id, "AGENT_TOOL_EXECUTED", details={"run_id": run.id, "action_id": action.id, "tool_name": tool_name})
                await db.commit()
                return action
            except Exception as e:
                action.status = ActionStatus.FAILED
                action.error_message = str(e)
                action.completed_at = datetime.now(timezone.utc)
                await db.commit()
                raise HTTPException(status_code=500, detail=str(e))

        # Risk evaluation
        tx_context = None
        transaction = None
        
        # Hydrate transaction info for add_to_cart from authoritative Product in catalog
        if tool_name == "add_to_cart" and "product_id" in tool_input:
            from app.services.commerce_service import CommerceService
            product = await CommerceService.get_product(db, workspace_id, tool_input["product_id"])
            if product:
                qty = tool_input.get("quantity", 1) or 1
                tool_input["amount"] = product.price * qty
                tool_input["currency"] = product.currency
                # Authoritative hydration - overwrite agent values
                tool_input["merchant_id"] = product.merchant_id
                tool_input["category"] = product.category

        # Hydrate transaction info and duplicate prevention for checkout
        if tool_name == "checkout":
            from app.services.commerce_service import CommerceService
            from app.models.commerce import OrderStatus, CartStatus, Order, Cart, CartItem
            from sqlalchemy.orm import joinedload

            # Idempotency / Duplicate Checkout Prevention:
            # 1. Check if this run already has a successfully checked-out order
            if run_id:
                stmt_prev_co = (
                    select(AgentAction)
                    .where(
                        AgentAction.run_id == run_id,
                        AgentAction.tool_name == "checkout",
                        AgentAction.status == ActionStatus.SUCCESS
                    )
                    .order_by(AgentAction.sequence_number.desc())
                )
                res_prev_co = await db.execute(stmt_prev_co)
                prev_co_act = res_prev_co.scalars().first()
                if prev_co_act and prev_co_act.output and "order_id" in prev_co_act.output:
                    existing_order_id = prev_co_act.output["order_id"]
                    existing_order = await CommerceService.get_order(db, workspace_id, existing_order_id)
                    if existing_order and existing_order.status in [OrderStatus.PENDING_PAYMENT, OrderStatus.PAID]:
                        action.status = ActionStatus.SUCCESS
                        action.output = {
                            "order_id": existing_order.id,
                            "status": existing_order.status.value,
                            "total": existing_order.total,
                            "currency": existing_order.currency,
                            "reused": True
                        }
                        action.completed_at = datetime.now(timezone.utc)
                        await db.commit()
                        return action

            # 2. Check if the specific cart is already checked out
            if "cart_id" in tool_input:
                try:
                    cart = await CommerceService.get_cart(db, workspace_id, tool_input["cart_id"])
                except Exception:
                    cart = None
                if cart:
                    if cart.status == CartStatus.CHECKED_OUT:
                        stmt_existing_order = select(Order).where(Order.cart_id == cart.id, Order.workspace_id == workspace_id)
                        res_order = await db.execute(stmt_existing_order)
                        existing_order = res_order.scalars().first()
                        if existing_order and existing_order.status in [OrderStatus.PENDING_PAYMENT, OrderStatus.PAID]:
                            action.status = ActionStatus.SUCCESS
                            action.output = {
                                "order_id": existing_order.id,
                                "status": existing_order.status.value,
                                "total": existing_order.total,
                                "currency": existing_order.currency,
                                "reused": True
                            }
                            action.completed_at = datetime.now(timezone.utc)
                            await db.commit()
                            return action
                    elif cart.items:
                        tool_input["amount"] = sum((item.quantity * item.product.price) for item in cart.items)
                        tool_input["currency"] = cart.currency
                        tool_input["merchant_id"] = cart.items[0].product.merchant_id
                        tool_input["category"] = cart.items[0].product.category
                    
        # Hydrate transaction info for pay_order if missing
        if tool_name == "pay_order" and "order_id" in tool_input:
            from app.services.commerce_service import CommerceService
            from app.models.commerce import OrderStatus
            order = await CommerceService.get_order(db, workspace_id, tool_input["order_id"])
            if not order:
                action.status = ActionStatus.FAILED
                action.error_code = "ORDER_NOT_FOUND"
                action.error_message = f"Order {tool_input['order_id']} not found."
                action.completed_at = datetime.now(timezone.utc)
                await db.commit()
                raise HTTPException(status_code=404, detail=f"Order {tool_input['order_id']} not found.")

            # Idempotency / Duplicate Payment Prevention:
            if order.status == OrderStatus.PAID:
                is_paid_by_current_run = False
                if run_id:
                    stmt_prev_pay = (
                        select(AgentAction)
                        .where(
                            AgentAction.run_id == run_id,
                            AgentAction.tool_name == "pay_order",
                            AgentAction.status == ActionStatus.SUCCESS
                        )
                        .order_by(AgentAction.sequence_number.desc())
                    )
                    res_prev_pay = await db.execute(stmt_prev_pay)
                    prev_pay_act = res_prev_pay.scalars().first()
                    if prev_pay_act and prev_pay_act.output and prev_pay_act.output.get("transaction_id") == order.payment_id:
                        is_paid_by_current_run = True
                        action.status = ActionStatus.SUCCESS
                        action.output = {
                            "status": "PAID",
                            "transaction_id": order.payment_id,
                            "reused": True
                        }
                        action.completed_at = datetime.now(timezone.utc)
                        await db.commit()
                        return action

                if not is_paid_by_current_run:
                    # An order paid by a different run or external transaction CANNOT be re-paid or reused to bypass the Action Gate!
                    action.status = ActionStatus.FAILED
                    action.error_code = "ORDER_ALREADY_PAID"
                    action.error_message = f"Cannot pay order {order.id}: Order is already paid."
                    action.completed_at = datetime.now(timezone.utc)
                    await db.commit()
                    raise HTTPException(status_code=400, detail=f"Cannot pay order {order.id}: Order is already paid.")

            # Authoritative hydration - always overwrite agent values with canonical order metadata
            tool_input["amount"] = order.total
            tool_input["currency"] = order.currency
            tool_input["merchant_id"] = order.merchant_id
            if order.items:
                tool_input["category"] = order.items[0].product.category
                    
        if tool_input.get("amount"):
            fallback_curr = tool_input.get("currency") or agent.currency or "INR"
            tx_context = TransactionContext(
                amount=float(tool_input.get("amount")),
                currency=fallback_curr
            )
            transaction = {
                "amount": float(tool_input.get("amount")), 
                "currency": fallback_curr,
                "merchant_id": tool_input.get("merchant_id")
            }
            if "order_id" in tool_input:
                transaction["order_id"] = tool_input["order_id"]
            if "cart_id" in tool_input:
                transaction["cart_id"] = tool_input["cart_id"]
            if "product_id" in tool_input:
                transaction["product_id"] = tool_input["product_id"]
            
        # Evaluate authoritative intent alignment with hydrated parameters
        if active_intent:
            alignment = evaluate_alignment(
                constraints=active_intent.structured_constraints,
                action=tool_name,
                amount=tool_input.get("amount"),
                currency=tool_input.get("currency"),
                product_category=tool_input.get("category"),
                merchant_id=tool_input.get("merchant_id"),
            )
            action.alignment_result = alignment.alignment
            action.alignment_signals = [s.model_dump() for s in alignment.signals]

        risk_req = RiskEvaluateRequest(
            agent_id=agent.id,
            agent_action_id=action.id,
            agent_run_id=run.id,
            intent_id=active_intent.id if active_intent else None,
            authority_id=active_authority.id if active_authority else None,
            merchant_id=tool_input.get("merchant_id"),
            product_category=tool_input.get("category"),
            transaction=tx_context
        )
        
        assessment = await evaluate_risk(db, workspace_id, risk_req, persist=True)

        # ── Check for an existing APPROVED approval on this run for same amount ──
        # If the human already approved an identical action on this run, treat this
        # as a revalidation so the approval-threshold REVIEW is not re-triggered.
        prior_approval = None
        prior_approval_id: Optional[str] = None
        is_revalidation = False
        if transaction and transaction.get("amount"):
            stmt_appr = (
                select(ApprovalRequest)
                .where(
                    ApprovalRequest.agent_run_id == run.id,
                    ApprovalRequest.status == ApprovalStatus.APPROVED,
                )
                .order_by(ApprovalRequest.id.desc())
            )
            res_appr = await db.execute(stmt_appr)
            for appr in res_appr.scalars().all():
                if appr.transaction_data == transaction:
                    prior_approval = appr
                    prior_approval_id = prior_approval.id
                    is_revalidation = True
                    break

        gate_decision = await gate.evaluate(
            workspace_id=workspace_id,
            agent_id=agent.id,
            agent_run_id=run.id,
            agent_action_id=action.id,
            intent_id=active_intent.id if active_intent else None,
            authority_id=active_authority.id if active_authority else None,
            risk_assessment_id=assessment.id if assessment else None,
            transaction=transaction,
            is_revalidation=is_revalidation,
            approval_id=prior_approval_id,
            alignment_result=action.alignment_result,
            alignment_signals=action.alignment_signals,
            action_type=tool_name
        )
        
        if not action.metadata_:
            action.metadata_ = {}
        action.metadata_["gate_decision_id"] = gate_decision.id
        action.metadata_["gate_decision"] = gate_decision.decision.value if hasattr(gate_decision.decision, "value") else str(gate_decision.decision)

        if gate_decision.decision == DecisionResult.BLOCK:
            action.status = ActionStatus.DENIED
            action.error_code = gate_decision.reason_codes[0] if gate_decision.reason_codes else "GATE_BLOCKED"
            action.error_message = gate_decision.explanation
            action.completed_at = datetime.now(timezone.utc)
            run.status = RunStatus.BLOCKED
            run.error_code = action.error_code
            run.error_message = f"Run stopped: Action '{tool_name}' blocked by Action Gate ({gate_decision.explanation})"
            run.completed_at = datetime.now(timezone.utc)
            await AgentRuntimeService._log_agent_activity(
                db, agent.id, workspace_id, "AGENT_TOOL_DENIED",
                details={"run_id": run.id, "action_id": action.id, "tool_name": tool_name, "reason": gate_decision.explanation}
            )
            await db.commit()
            raise HTTPException(status_code=403, detail=f"Action blocked by Action Gate: {gate_decision.explanation}")
            
        elif gate_decision.decision == DecisionResult.REVIEW:
            action.status = ActionStatus.PENDING_APPROVAL
            action.error_code = "APPROVAL_REQUIRED"
            action.error_message = f"Action requires human approval. Approval ID: {gate_decision.approval_id}"
            run.status = RunStatus.WAITING_FOR_APPROVAL
            await db.commit()
            raise HTTPException(status_code=402, detail=f"Action requires human approval. Approval ID: {gate_decision.approval_id}")
            
        # ── END Action Gate ───────────────────────────────────

        # Validate input schema
        try:
            validated_input = tool_def.input_schema(**tool_input)
        except ValidationError as e:
            action.status = ActionStatus.FAILED
            action.error_code = "INVALID_INPUT"
            action.error_message = str(e)
            action.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise HTTPException(status_code=400, detail=f"Invalid tool input: {str(e)}")

        signed_token = gate.issue_token(gate_decision, tool_name, transaction)

        # CONSUME the approval so it cannot be replayed
        if prior_approval:
            prior_approval.status = ApprovalStatus.CONSUMED
            await db.commit()

        # Execute Tool (We map handlers directly here for simplicity and to ensure db/workspace_id injection)
        try:
            output_data = await AgentRuntimeService._execute_tool_logic(db, workspace_id, agent.id, tool_name, validated_input, tool_input, run_id=run.id, action_id=action.id, signed_decision_token=signed_token)
            
            action.status = ActionStatus.SUCCESS
            action.output = output_data
            action.completed_at = datetime.now(timezone.utc)
            await AgentRuntimeService._log_agent_activity(db, agent.id, workspace_id, "AGENT_ACTION_COMPLETED", details={"run_id": run.id, "action_id": action.id})
            await db.commit()
            await db.refresh(action)
            return action
            
        except Exception as e:
            action.status = ActionStatus.FAILED
            action.error_code = "TOOL_EXECUTION_FAILED"
            action.error_message = str(e)
            action.completed_at = datetime.now(timezone.utc)
            await AgentRuntimeService._log_agent_activity(db, agent.id, workspace_id, "AGENT_ACTION_FAILED", details={"run_id": run.id, "action_id": action.id, "error": str(e)})
            await db.commit()
            return action

    @staticmethod
    async def _execute_tool_logic(db: AsyncSession, workspace_id: str, agent_id: str, tool_name: str, input_data: Any, raw_input: dict, run_id: Optional[str] = None, action_id: Optional[str] = None, signed_decision_token: Optional[str] = None) -> dict:
        ctx = ExecutionContext(
            is_human=False,
            is_agent=True,
            agent_id=agent_id,
            is_agent_runtime=True,
            agent_run_id=run_id,
            agent_action_id=action_id,
            signed_decision_token=signed_decision_token
        )
        
        if tool_name == "search_products":
            products = await CommerceService.list_products(
                db, 
                workspace_id, 
                category=input_data.category
            )
            # If category filter yielded zero results, fallback to all workspace products so query matching is not thwarted
            if not products and input_data.category:
                products = await CommerceService.list_products(
                    db,
                    workspace_id,
                    category=None
                )

            # Filter in python for query and price
            results = []
            clean_query = (input_data.query or "").strip().lower()
            query_terms = clean_query.split() if clean_query else []
            
            for p in products:
                prod_name = (p.name or "").strip().lower()
                name_desc = (prod_name + " " + (p.description or "")).lower()

                # Check exact product name match first
                is_exact_name = clean_query and prod_name == clean_query
                
                if query_terms and not is_exact_name:
                    # Check if query terms match name/description/category
                    searchable_text = name_desc + " " + (p.category or "").lower()
                    if not any(term in searchable_text for term in query_terms):
                        continue

                if input_data.min_price is not None and p.price < input_data.min_price:
                    continue
                if input_data.max_price is not None and p.price > input_data.max_price:
                    continue

                # Canonical persisted product metadata - NEVER trust model supplied prices
                item_dict = {
                    "product_id": p.id, 
                    "name": p.name, 
                    "category": p.category,
                    "price": p.price, 
                    "currency": p.currency, 
                    "merchant_id": p.merchant_id,
                    "inventory": p.inventory
                }
                if is_exact_name:
                    results.insert(0, item_dict)
                else:
                    results.append(item_dict)

            # Enforce intent category and brand constraints against authoritative product metadata
            if run_id:
                from app.models.agent_runtime import AgentRun
                from app.models.intent import Intent
                from app.services.taxonomy import are_categories_compatible
                run_obj = await db.get(AgentRun, run_id)
                if run_obj and run_obj.intent_id:
                    intent_obj = await db.get(Intent, run_obj.intent_id)
                    if intent_obj and intent_obj.structured_constraints:
                        intent_prod = intent_obj.structured_constraints.get("product") or {}
                        intent_cat = intent_prod.get("category")
                        if intent_cat:
                            # Filter results so that returned products match canonical catalog taxonomy
                            results = [r for r in results if are_categories_compatible(intent_cat, r.get("category"))]

            return {"results": results}
            
        elif tool_name == "create_cart":
            # Duplicate Cart Prevention: If this run already created an active cart, reuse it!
            if run_id:
                stmt_prev_cart = (
                    select(AgentAction)
                    .where(
                        AgentAction.run_id == run_id,
                        AgentAction.tool_name == "create_cart",
                        AgentAction.status == ActionStatus.SUCCESS
                    )
                    .order_by(AgentAction.sequence_number.desc())
                )
                res_prev_cart = await db.execute(stmt_prev_cart)
                prev_action = res_prev_cart.scalars().first()
                if prev_action and prev_action.output and "cart_id" in prev_action.output:
                    existing_cart_id = prev_action.output["cart_id"]
                    existing_cart = await CommerceService.get_cart(db, workspace_id, existing_cart_id)
                    if existing_cart and existing_cart.status.value == "ACTIVE":
                        return {
                            "cart_id": existing_cart.id,
                            "currency": existing_cart.currency,
                            "reused": True,
                            "message": f"Reused existing cart {existing_cart.id} for this run"
                        }

            # Determine currency:
            # 1. Active authority currency
            # 2. Agent configured currency
            # 3. Default from sandbox catalog products if available in workspace, otherwise INR
            agent = await db.get(Agent, agent_id)
            currency = None
            if run_id:
                from app.models.agent_runtime import AgentRun
                from app.models.authority import DelegatedAuthority
                run = await db.get(AgentRun, run_id)
                if run and run.authority_id:
                    auth = await db.get(DelegatedAuthority, run.authority_id)
                    if auth and auth.currency:
                        currency = auth.currency
            if not currency and agent and agent.currency:
                currency = agent.currency
            if not currency:
                # Check products in workspace
                from app.models.commerce import Product, Merchant
                prod_stmt = select(Product.currency).join(Merchant).where(Merchant.workspace_id == workspace_id).limit(1)
                res_prod = await db.execute(prod_stmt)
                cat_curr = res_prod.scalar_one_or_none()
                currency = cat_curr or "INR"
                
            cart_create = CartCreate(agent_id=agent_id, currency=currency)
            cart = await CommerceService.create_cart(db, workspace_id, cart_create, ctx)
            return {"cart_id": cart.id, "currency": cart.currency}
            
        elif tool_name == "add_to_cart":
            # Resolve product from authoritative workspace catalog records
            authoritative_product = await CommerceService.get_product(db, workspace_id, input_data.product_id)
            cart = await CommerceService.get_cart(db, workspace_id, input_data.cart_id)
            # Idempotency check: if product is already in cart with at least requested quantity, reuse it
            existing_item = next((it for it in (cart.items or []) if it.product_id == authoritative_product.id), None)
            if existing_item and existing_item.quantity >= input_data.quantity:
                return {
                    "cart_id": input_data.cart_id,
                    "item_id": existing_item.id,
                    "product_id": authoritative_product.id,
                    "product_name": authoritative_product.name,
                    "price": authoritative_product.price,
                    "currency": authoritative_product.currency,
                    "quantity": existing_item.quantity,
                    "total": authoritative_product.price * existing_item.quantity,
                    "reused": True
                }
            cart_item_create = CartItemCreate(product_id=authoritative_product.id, quantity=input_data.quantity)
            item = await CommerceService.add_cart_item(db, workspace_id, input_data.cart_id, cart_item_create, ctx)
            return {
                "cart_id": input_data.cart_id,
                "item_id": item.id,
                "product_id": authoritative_product.id,
                "product_name": authoritative_product.name,
                "price": authoritative_product.price,
                "currency": authoritative_product.currency,
                "quantity": item.quantity,
                "total": item.total
            }
            
        elif tool_name == "checkout":
            from app.models.commerce import Order, CartStatus
            # Check if this run already checked out an order successfully (duplicate prevention across distinct carts)
            if run_id:
                stmt_prev_co = (
                    select(AgentAction)
                    .where(
                        AgentAction.run_id == run_id,
                        AgentAction.tool_name == "checkout",
                        AgentAction.status == ActionStatus.SUCCESS
                    )
                    .order_by(AgentAction.sequence_number.desc())
                )
                res_prev_co = await db.execute(stmt_prev_co)
                prev_co_act = res_prev_co.scalars().first()
                if prev_co_act and prev_co_act.output and "order_id" in prev_co_act.output:
                    existing_order_id = prev_co_act.output["order_id"]
                    existing_order = await CommerceService.get_order(db, workspace_id, existing_order_id)
                    if existing_order and existing_order.status.value in ["PENDING_PAYMENT", "PAID"]:
                        return {
                            "order_id": existing_order.id,
                            "status": existing_order.status.value,
                            "total": existing_order.total,
                            "currency": existing_order.currency,
                            "reused": True
                        }

            cart = await CommerceService.get_cart(db, workspace_id, input_data.cart_id)
            if not cart:
                raise ValueError("Cart not found")
            # Idempotency check: if cart is already checked out, reuse existing order
            if cart.status == CartStatus.CHECKED_OUT:
                stmt_existing_order = select(Order).where(Order.cart_id == cart.id, Order.workspace_id == workspace_id)
                res_order = await db.execute(stmt_existing_order)
                existing_order = res_order.scalars().first()
                if existing_order:
                    order_status_val = existing_order.status.value if hasattr(existing_order.status, "value") else str(existing_order.status)
                    return {
                        "order_id": existing_order.id,
                        "status": order_status_val,
                        "total": existing_order.total,
                        "currency": existing_order.currency,
                        "reused": True
                    }
            if not cart.items:
                raise ValueError("Cart is empty")
            merchant_id = cart.items[0].product.merchant_id
            order_create = OrderCreate(cart_id=input_data.cart_id, agent_id=agent_id, merchant_id=merchant_id)
            order = await CommerceService.create_order(db, workspace_id, order_create, ctx)
            order_status_val = order.status.value if hasattr(order.status, "value") else str(order.status)
            return {"order_id": order.id, "status": order_status_val, "total": order.total, "currency": order.currency}
            
        elif tool_name == "pay_order":
            from app.models.commerce import Order, OrderStatus
            from app.services.payment_service import create_payment_intent, authorize_payment, capture_payment
            from app.schemas.payment import PaymentCreate
            import uuid
            
            # Duplicate Payment Prevention: If this run already captured payment, reuse it
            if run_id:
                stmt_prev_pay = (
                    select(AgentAction)
                    .where(
                        AgentAction.run_id == run_id,
                        AgentAction.tool_name == "pay_order",
                        AgentAction.status == ActionStatus.SUCCESS
                    )
                    .order_by(AgentAction.sequence_number.desc())
                )
                res_prev_pay = await db.execute(stmt_prev_pay)
                prev_pay_act = res_prev_pay.scalars().first()
                if prev_pay_act and prev_pay_act.output and "transaction_id" in prev_pay_act.output:
                    return {
                        "status": "PAID",
                        "transaction_id": prev_pay_act.output["transaction_id"],
                        "reused": True
                    }

            order = await CommerceService.get_order(db, workspace_id, input_data.order_id)
            if not order:
                raise ValueError("Order not found")
            # Idempotency check: if order is already paid, ensure it was paid by this run
            if order.status == OrderStatus.PAID:
                is_paid_by_current_run = False
                if run_id:
                    stmt_prev_pay = (
                        select(AgentAction)
                        .where(
                            AgentAction.run_id == run_id,
                            AgentAction.tool_name == "pay_order",
                            AgentAction.status == ActionStatus.SUCCESS
                        )
                        .order_by(AgentAction.sequence_number.desc())
                    )
                    res_prev_pay = await db.execute(stmt_prev_pay)
                    prev_pay_act = res_prev_pay.scalars().first()
                    if prev_pay_act and prev_pay_act.output and prev_pay_act.output.get("transaction_id") == order.payment_id:
                        is_paid_by_current_run = True
                        return {"status": "PAID", "transaction_id": order.payment_id, "reused": True}
                if not is_paid_by_current_run:
                    raise ValueError(f"Cannot pay order {order.id}: Order is already paid.")
                
            amount = int(raw_input.get("amount", 0))
            if amount <= 0:
                amount = order.total
                
            currency = raw_input.get("currency")
            if not currency:
                if run_id:
                    from app.models.agent_runtime import AgentRun
                    from app.models.authority import DelegatedAuthority
                    run = await db.get(AgentRun, run_id)
                    if run and run.authority_id:
                        auth = await db.get(DelegatedAuthority, run.authority_id)
                        if auth and auth.currency:
                            currency = auth.currency
                if not currency:
                    currency = order.currency or "USD"
            
            payment_create = PaymentCreate(
                payment_intent_id=f"pi_{uuid.uuid4().hex[:8]}",
                idempotency_key=f"idk_{agent_id}_{input_data.order_id}",
                agent_id=agent_id,
                order_id=input_data.order_id,
                amount=amount,
                currency=currency,
                payment_method_type="card"
            )
            
            payment = await create_payment_intent(db, workspace_id, payment_create, ctx)
            
            # Authorize
            payment = await authorize_payment(db, workspace_id, payment.id, ctx)
            if payment.status.value == "FAILED":
                raise ValueError(f"Payment failed: {payment.failure_reason}")
                
            # Capture
            payment = await capture_payment(db, workspace_id, payment.id, ctx)
            if payment.status.value == "FAILED":
                raise ValueError(f"Payment capture failed: {payment.failure_reason}")
                
            return {"status": "PAID", "transaction_id": payment.id}
            
        else:
            raise ValueError(f"No execution logic for tool {tool_name}")

    @staticmethod
    async def finish_run(
        db: AsyncSession,
        workspace_id: str,
        run_id: str,
        output: str,
        status: RunStatus = RunStatus.COMPLETED,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> AgentRun:
        run = await AgentRuntimeService.get_run(db, workspace_id, run_id)
        if run.status != RunStatus.RUNNING:
            raise HTTPException(status_code=400, detail="Cannot finish a run that is not RUNNING")
            
        run.status = status
        run.output = output
        if error_code is not None:
            run.error_code = error_code
        if error_message is not None:
            run.error_message = error_message
        run.completed_at = datetime.now(timezone.utc)
        
        event_name = "AGENT_RUN_COMPLETED" if status == RunStatus.COMPLETED else "AGENT_RUN_FAILED"
        await AgentRuntimeService._log_agent_activity(db, run.agent_id, workspace_id, event_name, details={"run_id": run.id, "status": status.value if hasattr(status, "value") else str(status)})
        await db.commit()
        await db.refresh(run)
        return run
