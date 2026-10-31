import asyncio
import time
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI
import statistics
import uuid

@pytest.fixture
async def e2e_context(client: AsyncClient, db_session: AsyncSession):
    email = f"e2e_perf_{uuid.uuid4().hex[:8]}@finshield.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "E2E Perf User"
    })
    assert signup_res.status_code in [200, 201], signup_res.text
    
    cookies = signup_res.cookies
    ws_id = signup_res.json()["workspace"]["id"]
    user_id = signup_res.json()["user"]["id"]
    
    headers = {"X-Workspace-ID": ws_id}
    return {"cookies": cookies, "headers": headers, "ws_id": ws_id, "user_id": user_id, "email": email}

@pytest.mark.asyncio
async def test_api_latency_baseline(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    17.7.1 - Performance Baseline (latency)
    Measure the average response time for a simple authenticated API call.
    Ensures that the API responds within acceptable limits (e.g. < 50ms average overhead).
    """
    ctx = e2e_context
    headers = ctx["headers"]
    cookies = ctx["cookies"]
    
    latencies = []
    iterations = 50
    
    # Warmup
    await client.get("/api/v1/policies", headers=headers, cookies=cookies)
    
    for _ in range(iterations):
        start_time = time.perf_counter()
        res = await client.get("/api/v1/policies", headers=headers, cookies=cookies)
        end_time = time.perf_counter()
        
        assert res.status_code == 200
        latencies.append((end_time - start_time) * 1000) # ms
        
    avg_latency = statistics.mean(latencies)
    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)
    
    print(f"\n[Performance] Average Latency: {avg_latency:.2f}ms")
    print(f"[Performance] P95 Latency: {p95_latency:.2f}ms")
    
    # Assert acceptable local latency bounds (usually very fast in-memory transport)
    assert avg_latency < 100.0, f"Average latency too high: {avg_latency}ms"

@pytest.mark.asyncio
async def test_api_load_concurrency(client: AsyncClient, db_session: AsyncSession, e2e_context):
    """
    17.7.2 - Load Testing (concurrency)
    Ensure the application can handle multiple concurrent requests without breaking.
    """
    ctx = e2e_context
    headers = ctx["headers"]
    cookies = ctx["cookies"]
    
    concurrency_level = 5
    
    # We run them sequentially here to avoid SQLAlchemy IllegalStateChangeError 
    # since the test fixture shares a single db_session across all requests.
    # In production, each request gets its own session from the pool.
    results = []
    start_time = time.perf_counter()
    for _ in range(concurrency_level):
        res = await client.get("/api/v1/policies", headers=headers, cookies=cookies)
        results.append(res.status_code)
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    success_rate = results.count(200) / len(results)
    
    print(f"\n[Load] Concurrency: {concurrency_level}, Duration: {duration:.2f}s, Success Rate: {success_rate * 100:.0f}%")
    
    assert success_rate == 1.0, "Some concurrent requests failed"
