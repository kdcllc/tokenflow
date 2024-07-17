import logging
import os
from fastapi import Body, FastAPI, HTTPException, Path
from pydantic import BaseModel
from typing import Optional

from src.auth_middleware import AuthMiddleware
from src.token_authenticator import AzureAuthenticator


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
    accessToken: Optional[str]
    expiresOn: Optional[str]
    expires_on: Optional[int]
    subscription: Optional[str]
    tenant: Optional[str]
    tokenType: Optional[str]

class DeviceCodeResponse(BaseModel):
    url: str
    device_code: str

class TokenRequest(BaseModel):
    resource: str

@app.post("/device-code/{user_id}", response_model=DeviceCodeResponse)
async def get_device_code(user_id: str = Path(..., description="The unique ID of the user")):
    url, device_code = await authenticator.get_device_code(user_id)
    return {"url": url, "device_code": device_code}

@app.post("/token/{user_id}", response_model=TokenResponse)
async def get_token(token_request: TokenRequest = Body(...), user_id: str = Path(..., description="The unique ID of the user")):
    
    if not await authenticator.check_az_login():
        raise HTTPException(status_code=400, detail="Device code not requested")

    token_info = await authenticator.authenticate(user_id, token_request.resource)

    if token_info is None:
        raise HTTPException(status_code=400, detail="Token not found")
    
    token = {
            "accessToken": token_info["accessToken"], 
            "expiresOn": token_info["expiresOn"], 
            "expires_on": token_info["expires_on"], 
            "subscription": token_info["subscription"], 
            "tenant": token_info["tenant"], 
            "tokenType": token_info["tokenType"]
            }
    return token

@app.get("/health")
async def health_check():
    return {"status": "UP"}
