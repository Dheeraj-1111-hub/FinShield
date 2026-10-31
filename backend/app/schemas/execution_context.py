import datetime
from pydantic import BaseModel
from typing import Optional, Any, Dict

class SignedGateDecision(BaseModel):
    decision_id: str
    workspace_id: str
    agent_id: str
    agent_run_id: str
    agent_action_id: str
    
    action_type: str
    target_resource: Optional[str] = None
    
    intent_id: Optional[str] = None
    intent_version: Optional[int] = None
    authority_id: Optional[str] = None
    authority_version: Optional[int] = None
    policy_version: Optional[str] = None
    risk_assessment_id: Optional[str] = None
    
    amount: Optional[int] = None
    currency: Optional[str] = None
    target_identity: Optional[str] = None # product/cart/order ID
    action_parameters: Optional[Dict[str, Any]] = None
    
    decision: str
    issued_at: datetime.datetime
    expires_at: datetime.datetime
    nonce: str

class ExecutionContext(BaseModel):
    """
    Cryptographic/programmatic provenance of an execution action.
    This guarantees that service layer actions (like creating an order)
    know definitively if the action is human-driven or agent-driven,
    and if agent-driven, whether it actually passed through the Action Gate.
    """
    is_human: bool
    user_id: Optional[str] = None
    
    is_agent: bool
    agent_id: Optional[str] = None
    
    # Internal runtime context
    is_agent_runtime: bool = False
    agent_run_id: Optional[str] = None
    agent_action_id: Optional[str] = None
    signed_decision_token: Optional[str] = None
