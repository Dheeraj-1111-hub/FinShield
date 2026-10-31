from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

def get_api_key_or_ip(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # Rate limit by credential prefix/hash if available
        return auth_header
    return get_remote_address(request)

limiter = Limiter(key_func=get_api_key_or_ip)
