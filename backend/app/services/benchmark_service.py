from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.benchmark import BenchmarkSuite, BenchmarkCase, BenchmarkExperiment, BenchmarkRun
from app.schemas.benchmark import BenchmarkSuiteCreate, BenchmarkCaseCreate, BenchmarkExperimentCreate

class BenchmarkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Suites
    async def get_suites(self, workspace_id: str) -> List[BenchmarkSuite]:
        stmt = select(BenchmarkSuite).where(BenchmarkSuite.workspace_id == workspace_id)
        return (await self.db.execute(stmt)).scalars().all()
        
    async def create_suite(self, workspace_id: str, data: BenchmarkSuiteCreate) -> BenchmarkSuite:
        suite = BenchmarkSuite(
            workspace_id=workspace_id,
            name=data.name,
            slug=data.name.lower().replace(" ", "-"),
            description=data.description,
            version=data.version
        )
        self.db.add(suite)
        await self.db.commit()
        await self.db.refresh(suite)
        return suite

    # Cases
    async def get_cases(self, workspace_id: str, suite_id: str) -> List[BenchmarkCase]:
        stmt = select(BenchmarkCase).where(
            BenchmarkCase.workspace_id == workspace_id,
            BenchmarkCase.suite_id == suite_id
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def create_case(self, workspace_id: str, data: BenchmarkCaseCreate) -> BenchmarkCase:
        case = BenchmarkCase(
            workspace_id=workspace_id,
            **data.model_dump()
        )
        self.db.add(case)
        await self.db.commit()
        await self.db.refresh(case)
        return case

    # Experiments
    async def get_experiments(self, workspace_id: str) -> List[BenchmarkExperiment]:
        stmt = select(BenchmarkExperiment).where(BenchmarkExperiment.workspace_id == workspace_id)
        return (await self.db.execute(stmt)).scalars().all()
        
    async def create_experiment(self, workspace_id: str, data: BenchmarkExperimentCreate) -> BenchmarkExperiment:
        exp = BenchmarkExperiment(
            workspace_id=workspace_id,
            **data.model_dump()
        )
        self.db.add(exp)
        await self.db.commit()
        await self.db.refresh(exp)
        return exp

    # Runs
    async def get_runs(self, workspace_id: str, experiment_id: Optional[str] = None) -> List[BenchmarkRun]:
        stmt = select(BenchmarkRun).where(BenchmarkRun.workspace_id == workspace_id)
        if experiment_id:
            stmt = stmt.where(BenchmarkRun.experiment_id == experiment_id)
        return (await self.db.execute(stmt)).scalars().all()
        
    async def create_run(self, workspace_id: str, experiment_id: str, configuration: dict) -> BenchmarkRun:
        run = BenchmarkRun(
            workspace_id=workspace_id,
            experiment_id=experiment_id,
            configuration_snapshot=configuration
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run
