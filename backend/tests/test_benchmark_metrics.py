import pytest
import statistics
from unittest.mock import MagicMock
from app.services.benchmark_metrics import BenchmarkMetricsService
from app.models.benchmark import BenchmarkCaseResult, BenchmarkCase, BenchmarkRun

# A quick class to mock the row returned by SQLAlchemy
class MockRow:
    def __init__(self, result, case):
        self.BenchmarkCaseResult = result
        self.BenchmarkCase = case

def test_metrics_empty():
    service = BenchmarkMetricsService(db=None)
    metrics = service._calculate_metrics_dict([])
    assert metrics == {}

def test_metrics_latency():
    service = BenchmarkMetricsService(db=None)
    case = BenchmarkCase(category="LEGITIMATE_COMMERCE")
    results = [
        MockRow(BenchmarkCaseResult(latency_ms=100, expected_decision="ALLOW", observed_decision="ALLOW"), case),
        MockRow(BenchmarkCaseResult(latency_ms=200, expected_decision="ALLOW", observed_decision="ALLOW"), case),
        MockRow(BenchmarkCaseResult(latency_ms=300, expected_decision="ALLOW", observed_decision="ALLOW"), case),
    ]
    metrics = service._calculate_metrics_dict(results)
    assert metrics["mean_latency_ms"] == 200.0
    assert metrics["median_latency_ms"] == 200.0
    assert metrics["task_completion_rate"] == 1.0
    assert metrics["correct_decision_rate"] == 1.0

def test_metrics_false_allow_rate():
    service = BenchmarkMetricsService(db=None)
    case = BenchmarkCase(category="PROMPT_INJECTION")
    
    # 3 expected BLOCK cases. 1 successfully blocked, 2 falsely allowed.
    results = [
        MockRow(BenchmarkCaseResult(expected_decision="BLOCK", observed_decision="BLOCK", financial_execution_occurred=False), case),
        MockRow(BenchmarkCaseResult(expected_decision="BLOCK", observed_decision="ALLOW", financial_execution_occurred=True), case),
        MockRow(BenchmarkCaseResult(expected_decision="BLOCK", observed_decision="ALLOW", financial_execution_occurred=True), case),
    ]
    
    metrics = service._calculate_metrics_dict(results)
    assert metrics["false_allow_rate"] == 2 / 3
    assert metrics["correct_decision_rate"] == 1 / 3
    assert metrics["attack_prevention_rate"] == 1 / 3

def test_metrics_false_block_rate():
    service = BenchmarkMetricsService(db=None)
    case = BenchmarkCase(category="LEGITIMATE_COMMERCE")
    
    # 4 expected ALLOW cases. 3 allowed, 1 falsely blocked.
    results = [
        MockRow(BenchmarkCaseResult(expected_decision="ALLOW", observed_decision="ALLOW", financial_execution_occurred=True), case),
        MockRow(BenchmarkCaseResult(expected_decision="ALLOW", observed_decision="ALLOW", financial_execution_occurred=True), case),
        MockRow(BenchmarkCaseResult(expected_decision="ALLOW", observed_decision="ALLOW", financial_execution_occurred=True), case),
        MockRow(BenchmarkCaseResult(expected_decision="ALLOW", observed_decision="BLOCK", financial_execution_occurred=False), case),
    ]
    
    metrics = service._calculate_metrics_dict(results)
    assert metrics["false_block_rate"] == 1 / 4
    assert metrics["task_completion_rate"] == 3 / 4

def test_metrics_div_by_zero_prevention():
    service = BenchmarkMetricsService(db=None)
    
    # If no expected_not_allow exists, false_allow_rate should not exist in dict
    case = BenchmarkCase(category="LEGITIMATE_COMMERCE")
    results = [MockRow(BenchmarkCaseResult(expected_decision="ALLOW", observed_decision="ALLOW"), case)]
    
    metrics = service._calculate_metrics_dict(results)
    assert "false_allow_rate" not in metrics
    assert "false_block_rate" in metrics
    assert metrics["false_block_rate"] == 0.0
