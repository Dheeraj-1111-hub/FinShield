from typing import Any, Dict, List
import asyncio
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.benchmark import BenchmarkRun, BenchmarkCaseResult, BenchmarkCase, BenchmarkExperiment
from app.models.agent_runtime import AgentRun, AgentAction
from app.models.agent import Agent
from app.services.benchmark_metrics import BenchmarkMetricsService

class BenchmarkExecutorService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.metrics_service = BenchmarkMetricsService(db)

    async def execute_run(self, workspace_id: str, run_id: str):
        """Executes a full benchmark run in the background."""
        # 1. Fetch Run and Experiment
        stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_id, BenchmarkRun.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        run = result.scalar_one_or_none()
        if not run:
            return

        stmt_exp = select(BenchmarkExperiment).where(BenchmarkExperiment.id == run.experiment_id)
        exp = (await self.db.execute(stmt_exp)).scalar_one_or_none()
        
        stmt_cases = select(BenchmarkCase).where(BenchmarkCase.suite_id == exp.suite_id)
        cases = (await self.db.execute(stmt_cases)).scalars().all()

        run.status = "RUNNING"
        run.started_at = func.now()
        run.total_cases = len(cases) * exp.repetitions * (2 if exp.baseline_configuration else 1)
        await self.db.commit()

        try:
            for rep in range(1, exp.repetitions + 1):
                for case in cases:
                    # Execute Baseline if configured
                    if exp.baseline_configuration:
                        await self._execute_case(workspace_id, run_id, exp.id, case, rep, is_baseline=True)
                    
                    # Execute FINSHIELD Protected
                    await self._execute_case(workspace_id, run_id, exp.id, case, rep, is_baseline=False)
                    
                    run.completed_cases += (2 if exp.baseline_configuration else 1)
                    await self.db.commit()

            run.status = "COMPLETED"
            run.completed_at = func.now()
            
            # Calculate metrics
            await self.metrics_service.calculate_and_store_metrics(workspace_id, run_id)

        except Exception as e:
            run.status = "FAILED"
            run.summary = f"Execution failed: {str(e)}"
            run.failed_cases += 1
        
        await self.db.commit()

    async def _execute_case(self, workspace_id: str, run_id: str, experiment_id: str, case: BenchmarkCase, rep: int, is_baseline: bool):
        start_time = time.time()
        
        # Determine initial prompt and context from the case config
        initial_prompt = case.initial_state.get("prompt", "Search and buy a product.")
        agent_id = case.agent_configuration.get("agent_id") or "mock_agent_id"
        user_id = case.agent_configuration.get("user_id") or "mock_user_id"
        
        # For FINSHIELD runs, we would ideally create a real AgentRun
        # Here we mock the run_id for the test, but in a real system we'd spin up an AgentRuntimeService run
        target_run_id = f"run_{case.id}_{rep}"
        
        from app.services.benchmark_agent import BenchmarkAgent
        agent = BenchmarkAgent(self.db)
        
        observed_decision = "ALLOW"
        error_msg = None
        
        try:
            # Execute the trial
            final_state = await agent.run_trial(
                workspace_id=workspace_id,
                agent_id=agent_id,
                user_id=user_id,
                run_id=target_run_id,
                initial_prompt=initial_prompt,
                is_baseline=is_baseline
            )
            
            # Analyze final state messages to determine if it was blocked or allowed
            messages = final_state.get("messages", [])
            for msg in messages:
                if msg.get("role") == "tool":
                    content = msg.get("content", "")
                    if "ERROR (403)" in content or "ERROR (402)" in content or "REVIEW REQUIRED" in content:
                        observed_decision = "BLOCK"
        except Exception as e:
            error_msg = str(e)
            observed_decision = "ERROR"
            
        latency_ms = int((time.time() - start_time) * 1000)

        # Record the result
        result = BenchmarkCaseResult(
            workspace_id=workspace_id,
            benchmark_run_id=run_id,
            case_id=case.id,
            is_baseline=is_baseline,
            repetition_index=rep,
            status="PASS" if observed_decision == case.expected_decision else "FAIL",
            expected_decision=case.expected_decision,
            observed_decision=observed_decision,
            financial_execution_occurred=(observed_decision == "ALLOW" and error_msg is None),
            latency_ms=latency_ms,
            gate_decision=observed_decision if not is_baseline else None,
            error=error_msg
        )
        
        self.db.add(result)
        await self.db.commit()
