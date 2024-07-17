import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        x_auth_token = request.headers.get('X-Auth-Token')
        if not x_auth_token:
            raise HTTPException(status_code=400, detail="X-Auth-Token header is missing")
        if x_auth_token != os.getenv('X_AUTH_TOKEN'):
            raise HTTPException(status_code=403, detail="Invalid X-Auth-Token header")
        response = await call_next(request)
        return response
