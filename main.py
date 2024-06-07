import logging
import os
import threading
from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel
from typing import Optional

from authenticator import AzureAuthenticator
from authmiddleware import AuthMiddleware

# Get logging level from environment variable
logging_level = os.getenv('LOGGING_LEVEL', 'INFO')

# Set logging level
logging.basicConfig(level=getattr(logging, logging_level.upper()))

app = FastAPI()

app.add_middleware(AuthMiddleware)

x_auth_token = os.getenv('X_AUTH_TOKEN')
if not x_auth_token:
    raise ValueError("X_AUTH_TOKEN environment variable is not set")

authenticator = AzureAuthenticator()

class TokenResponse(BaseModel):
    token: Optional[str]

class DeviceCodeResponse(BaseModel):
    url: str
    device_code: str

class TokenRequest(BaseModel):
    resource: str

@app.post("/device-code/{user_id}", response_model=DeviceCodeResponse)
def get_device_code(user_id: str = Path(..., description="The unique ID of the user")):
    url, device_code = authenticator.get_device_code(user_id)
    return {"url": url, "device_code": device_code}

@app.post("/token/{user_id}", response_model=TokenResponse)
def get_token(token_request: TokenRequest, user_id: str = Path(..., description="The unique ID of the user")):
    if user_id not in authenticator.users_data  or not authenticator.users_data[user_id].get('device_code'):
        raise HTTPException(status_code=400, detail="Device code not requested")

    # ensure the user has authenticated
    auth_thread = threading.Thread(target=authenticator.authenticate, args=(user_id, token_request.resource))
    auth_thread.start()
    auth_thread.join()

    token = authenticator.get_token_thread_safe(user_id)
    return {"token": token}

@app.get("/health")
def health_check():
    return {"status": "UP"}
