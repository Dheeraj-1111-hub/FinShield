import asyncio
import logging
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole, WorkspaceMember
from app.core.dependencies import get_current_user, get_current_workspace, RequireWorkspaceRole
from app.services.security_scenarios import ScenarioRegistry
from app.services.security_lab_service import SecurityLabService
from app.schemas.security_lab import (
    SecurityScenarioResponse,
    SecurityTestRunCreate,
    SecurityTestRunResponse,
    SecurityFindingResponse,
    SecurityBenchmarkSummary
)
from app.models.security_lab import SecurityScenario, SecurityTestRun, TestStatus

logger = logging.getLogger(__name__)
router = APIRouter()

_running_test_runs: set[str] = set()

async def _execute_test_run_background(run_id: str, actor_id: str):
    """Executes the security test run in an isolated async database session with error capture."""
    if run_id in _running_test_runs:
        return
    _running_test_runs.add(run_id)
    try:
        async with AsyncSessionLocal() as session:
            svc = SecurityLabService(session)
            await svc.execute_test(run_id=run_id, actor_id=actor_id)
    except Exception as e:
        logger.exception("Background execution error for security test run %s: %s", run_id, e)
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(SecurityTestRun).where(SecurityTestRun.id == run_id)
                res = await session.execute(stmt)
                run = res.scalar_one_or_none()
                if run and run.status in [TestStatus.QUEUED, TestStatus.RUNNING]:
                    run.status = TestStatus.ERROR
                    run.summary = f"Execution failed: {str(e)}"
                    run.completed_at = datetime.now(timezone.utc)
                    await session.commit()
        except Exception as inner_e:
            logger.exception("Failed to mark test run %s as ERROR: %s", run_id, inner_e)
    finally:
        _running_test_runs.discard(run_id)

@router.get("/scenarios", response_model=List[SecurityScenarioResponse])
async def list_scenarios(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """Get all security scenarios available for testing in the workspace."""
    await ScenarioRegistry.initialize_scenarios(db, current_workspace.id, current_user.id)
    stmt = select(SecurityScenario).order_by(SecurityScenario.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.post("/runs", response_model=SecurityTestRunResponse)
async def run_scenario(
    workspace_id: str,
    request: SecurityTestRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
    membership: WorkspaceMember = Depends(RequireWorkspaceRole([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]))
):
    """Trigger a new security test run."""
    svc = SecurityLabService(db)
    
    test_run = await svc.start_test(
        workspace_id=current_workspace.id,
        scenario_id=request.scenario_id,
        actor_id=current_user.id,
        configuration=request.configuration,
        target_agent_id=request.target_agent_id
    )
    
    # Execute immediately in background task
    asyncio.create_task(_execute_test_run_background(test_run.id, current_user.id))
    
    return test_run

@router.get("/runs", response_model=List[SecurityTestRunResponse])
async def list_test_runs(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """Get all test runs for the workspace."""
    svc = SecurityLabService(db)
    runs = await svc.get_runs(current_workspace.id)

    # Auto-dispatch any queued runs that have not yet executed
    for run in runs:
        if run.status == TestStatus.QUEUED and run.id not in _running_test_runs:
            asyncio.create_task(_execute_test_run_background(run.id, run.initiated_by))

    return runs

@router.get("/runs/{run_id}", response_model=SecurityTestRunResponse)
async def get_test_run(
    workspace_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """Get details for a specific test run including its steps and findings."""
    svc = SecurityLabService(db)
    run = await svc.get_run_details(current_workspace.id, run_id)
    if run.status == TestStatus.QUEUED and run.id not in _running_test_runs:
        asyncio.create_task(_execute_test_run_background(run.id, run.initiated_by))
    return run

@router.get("/findings", response_model=List[SecurityFindingResponse])
async def get_findings(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """Get all security findings for the workspace."""
    svc = SecurityLabService(db)
    return await svc.get_findings(current_workspace.id)

@router.get("/benchmark", response_model=SecurityBenchmarkSummary)
async def get_benchmark_summary(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace)
):
    """Get the verified Security Benchmark summary and per-scenario evaluation breakdown."""
    svc = SecurityLabService(db)
    return await svc.get_benchmark_summary(current_workspace.id, current_user.id)
