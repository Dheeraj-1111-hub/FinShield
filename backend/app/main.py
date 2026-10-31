from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import _rate_limit_exceeded_handler
from app.core.rate_limit import limiter
from slowapi.errors import RateLimitExceeded

from app.api.routes import (
    auth, users, workspaces, agents, policies, 
    payments, commerce, agent_runtime, intents,
    authorities, risk, approvals, investigations,
    audit, security_lab, benchmark, developers, overview
)

app = FastAPI(
    title="FINSHIELD API",
    description="Runtime Trust & Risk Infrastructure for Autonomous Financial Agents",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global Exception Handlers for Standardized JSON Errors
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code = "UNAUTHORIZED" if exc.status_code == 401 else "ERROR"
    if exc.status_code == 403: code = "FORBIDDEN"
    if exc.status_code == 404: code = "NOT_FOUND"
    if exc.status_code == 429: code = "RATE_LIMITED"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}}
    )

from fastapi.encoders import jsonable_encoder

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "VALIDATION_ERROR", "message": "Invalid request parameters.", "details": jsonable_encoder(exc.errors())}}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    # In production, log the actual exception but do not expose it
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}}
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8082", "http://localhost:8081"], # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["Workspaces"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(policies.router, prefix="/api/v1/policies", tags=["Policies"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(commerce.router, prefix="/api/v1/commerce", tags=["Commerce"])
app.include_router(agent_runtime.router, prefix="/api/v1/agent-runtime", tags=["Agent Runtime"])
app.include_router(intents.router, prefix="/api/v1/intents", tags=["Intents"])
app.include_router(authorities.router, prefix="/api/v1/authorities", tags=["Authorities"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk & Governance"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["Approvals"])
app.include_router(approvals.gate_decisions_router, prefix="/api/v1/gate-decisions", tags=["Gate Decisions"])
app.include_router(investigations.router, prefix="/api/v1/investigations", tags=["Investigations"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit & Forensics"])
app.include_router(audit.router, prefix="/api/v1/workspaces/{workspace_id}/audit", tags=["Audit & Forensics"])
app.include_router(security_lab.router, prefix="/api/v1/workspaces/{workspace_id}/security-lab", tags=["Security Lab"])
app.include_router(benchmark.router, prefix="/api/v1/workspaces/{workspace_id}/benchmark", tags=["Benchmark Lab"])
app.include_router(developers.router, prefix="/api/v1/developers", tags=["Developers"])
app.include_router(overview.router, prefix="/api/v1/overview", tags=["Overview"])

@app.get("/")
async def root():
    return {"message": "FINSHIELD API Gateway is running."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
