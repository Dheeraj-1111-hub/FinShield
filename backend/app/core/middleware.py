import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_var: ContextVar[str] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default=None)

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get request id from header or generate new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = f"req_{uuid.uuid4().hex}"
            
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = f"corr_{uuid.uuid4().hex}"
        
        # Store in contextvar
        req_token = request_id_var.set(request_id)
        corr_token = correlation_id_var.set(correlation_id)
        
        try:
            response = await call_next(request)
            # Ensure header is returned
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            request_id_var.reset(req_token)
            correlation_id_var.reset(corr_token)

def get_current_request_id() -> str:
    return request_id_var.get()

def get_current_correlation_id() -> str:
    return correlation_id_var.get()
