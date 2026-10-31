from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from app.core.dependencies import get_db, get_current_workspace
from app.models.risk import RiskAssessment, RiskLevel
from app.schemas.risk import RiskEvaluateRequest, RiskAssessmentResponse, RiskSummaryResponse
from app.models.workspace import Workspace
from app.services.risk_orchestrator import evaluate_risk

router = APIRouter()

@router.post("/evaluate", response_model=RiskAssessmentResponse)
async def evaluate_risk_endpoint(
    request: RiskEvaluateRequest,
    persist: bool = Query(True, description="Whether to save the assessment to DB"),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Evaluate an action through the Risk Engine"""
    assessment = await evaluate_risk(db, workspace.id, request, persist=persist)
    return assessment


@router.get("/assessments", response_model=List[RiskAssessmentResponse])
async def list_assessments(
    agent_id: Optional[str] = Query(None),
    level: Optional[RiskLevel] = Query(None),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """List risk assessments"""
    stmt = select(RiskAssessment).where(RiskAssessment.workspace_id == workspace.id)
    if agent_id:
        stmt = stmt.where(RiskAssessment.agent_id == agent_id)
    if level:
        stmt = stmt.where(RiskAssessment.risk_level == level)
        
    stmt = stmt.order_by(desc(RiskAssessment.created_at)).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/assessments/{assessment_id}", response_model=RiskAssessmentResponse)
async def get_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get a specific risk assessment"""
    stmt = select(RiskAssessment).where(
        RiskAssessment.id == assessment_id, 
        RiskAssessment.workspace_id == workspace.id
    )
    result = await db.execute(stmt)
    assessment = result.scalar_one_or_none()
    
    if not assessment:
        raise HTTPException(status_code=404, detail="Risk Assessment not found")
        
    return assessment


@router.get("/summary", response_model=RiskSummaryResponse)
async def get_risk_summary(
    days: int = Query(7),
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get aggregated risk statistics"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    stmt = select(RiskAssessment).where(
        RiskAssessment.workspace_id == workspace.id,
        RiskAssessment.created_at >= since
    )
    result = await db.execute(stmt)
    assessments = result.scalars().all()
    
    total = len(assessments)
    if total == 0:
        return RiskSummaryResponse(
            total_assessments=0,
            low=0, medium=0, high=0, critical=0,
            average_score=0.0, high_risk_rate=0.0
        )
        
    low = sum(1 for a in assessments if a.risk_level == RiskLevel.LOW)
    medium = sum(1 for a in assessments if a.risk_level == RiskLevel.MEDIUM)
    high = sum(1 for a in assessments if a.risk_level == RiskLevel.HIGH)
    critical = sum(1 for a in assessments if a.risk_level == RiskLevel.CRITICAL)
    
    avg_score = sum(a.risk_score for a in assessments) / total
    high_risk_rate = ((high + critical) / total) * 100.0
    
    return RiskSummaryResponse(
        total_assessments=total,
        low=low,
        medium=medium,
        high=high,
        critical=critical,
        average_score=round(avg_score, 1),
        high_risk_rate=round(high_risk_rate, 1)
    )
