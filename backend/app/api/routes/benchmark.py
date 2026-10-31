from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any
from app.db.database import get_db
from app.schemas.benchmark import (
    BenchmarkSuite, BenchmarkSuiteCreate, BenchmarkSuiteDetail,
    BenchmarkCase, BenchmarkCaseCreate,
    BenchmarkExperiment, BenchmarkExperimentCreate, BenchmarkExperimentDetail,
    BenchmarkRun, BenchmarkRunCreate, BenchmarkRunDetail,
    BenchmarkMetric, BenchmarkCaseResult
)
from app.services.benchmark_service import BenchmarkService
from app.services.benchmark_executor import BenchmarkExecutorService
from app.models.benchmark import BenchmarkRun as BenchmarkRunModel
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

router = APIRouter()

@router.get("/suites", response_model=List[BenchmarkSuite])
async def list_suites(workspace_id: str, db: AsyncSession = Depends(get_db)):
    svc = BenchmarkService(db)
    return await svc.get_suites(workspace_id)

@router.post("/suites", response_model=BenchmarkSuite)
async def create_suite(workspace_id: str, data: BenchmarkSuiteCreate, db: AsyncSession = Depends(get_db)):
    svc = BenchmarkService(db)
    return await svc.create_suite(workspace_id, data)

@router.get("/suites/{suite_id}/cases", response_model=List[BenchmarkCase])
async def list_cases(workspace_id: str, suite_id: str, db: AsyncSession = Depends(get_db)):
    svc = BenchmarkService(db)
    return await svc.get_cases(workspace_id, suite_id)

@router.post("/cases", response_model=BenchmarkCase)
async def create_case(workspace_id: str, data: BenchmarkCaseCreate, db: AsyncSession = Depends(get_db)):
    svc = BenchmarkService(db)
    return await svc.create_case(workspace_id, data)

@router.get("/experiments", response_model=List[BenchmarkExperiment])
async def list_experiments(workspace_id: str, db: AsyncSession = Depends(get_db)):
    svc = BenchmarkService(db)
    return await svc.get_experiments(workspace_id)

@router.post("/experiments", response_model=BenchmarkExperiment)
async def create_experiment(workspace_id: str, data: BenchmarkExperimentCreate, db: AsyncSession = Depends(get_db)):
    svc = BenchmarkService(db)
    return await svc.create_experiment(workspace_id, data)

@router.get("/experiments/{experiment_id}/runs", response_model=List[BenchmarkRun])
async def list_runs(workspace_id: str, experiment_id: str, db: AsyncSession = Depends(get_db)):
    svc = BenchmarkService(db)
    return await svc.get_runs(workspace_id, experiment_id)

@router.post("/experiments/{experiment_id}/runs", response_model=BenchmarkRun)
async def run_experiment(
    workspace_id: str, 
    experiment_id: str, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    svc = BenchmarkService(db)
    run = await svc.create_run(workspace_id, experiment_id, configuration={})
    
    executor = BenchmarkExecutorService(db)
    background_tasks.add_task(executor.execute_run, workspace_id, run.id)
    
    return run

@router.get("/runs/{run_id}", response_model=BenchmarkRunDetail)
async def get_run_detail(workspace_id: str, run_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(BenchmarkRunModel).options(
        selectinload(BenchmarkRunModel.results),
        selectinload(BenchmarkRunModel.experiment)
    ).where(
        BenchmarkRunModel.id == run_id, 
        BenchmarkRunModel.workspace_id == workspace_id
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    from app.models.benchmark import BenchmarkMetric as BenchmarkMetricModel
    stmt_metrics = select(BenchmarkMetricModel).where(BenchmarkMetricModel.benchmark_run_id == run_id)
    metrics_res = await db.execute(stmt_metrics)
    metrics = metrics_res.scalars().all()
    
    # Constructing manually as Pydantic may have issues with relationships if not configured right
    run_dict = BenchmarkRunDetail.model_validate(run)
    run_dict.metrics = [BenchmarkMetric.model_validate(m) for m in metrics]
    run_dict.results = [BenchmarkCaseResult.model_validate(r) for r in run.results]
    
    return run_dict
