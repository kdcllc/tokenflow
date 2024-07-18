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

logger = logging.getLogger(__name__)

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


class TokenSubRequest(BaseModel):
    resource: str
    subscription_id: str


@app.post("/device-code/{user_id}", response_model=DeviceCodeResponse)
async def get_device_code(user_id: str = Path(..., description="The unique ID of the user")):
    """
    Retrieves the device code for the specified user ID.

    Args:
        user_id (str): The unique ID of the user.

    Returns:
        dict: A dictionary containing the URL and device code.

    Raises:
        HTTPException: If an error occurs while retrieving the device code.
    """
    try:
        url, device_code = await authenticator.get_device_code_async(user_id)
        return {"url": url, "device_code": device_code}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/token/{user_id}", response_model=TokenResponse)
async def get_token(token_request: TokenRequest = Body(...), user_id: str = Path(..., description="The unique ID of the user")):

    try:
        await check_az_login_async(user_id=user_id)

        token_info = await authenticator.authenticate_async(user_id, token_request.resource)

        if token_info is None:
            raise HTTPException(status_code=400, detail="Token was not found")

        token = {
            "accessToken": token_info["accessToken"],
            "expiresOn": token_info["expiresOn"],
            "expires_on": token_info["expires_on"],
            "subscription": token_info["subscription"],
            "tenant": token_info["tenant"],
            "tokenType": token_info["tokenType"]
        }
        return token
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/subscriptions/{user_id}")
async def get_list_of_subscriptions_async(user_id: str = Path(..., description="The unique ID of the user")):
    """
    Retrieve a list of subscriptions for a given azure user.

    Args:
        user_id (str): The unique ID of the user.

    Returns:
        list: A list of subscriptions.

    """
    try:
        await check_az_login_async(user_id=user_id)

        subscriptions = await authenticator.get_list_of_subscriptions_async(user_id)
        return subscriptions
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


async def check_az_login_async(user_id: str):

    logger.info(f"Checking if user: {user_id} has requested device code")

    if not await authenticator.check_az_login_async(user_id=user_id):
        raise HTTPException(
            status_code=400, detail="Device code was not requested")


async def health_check():
    """
    Performs a health check and returns the status.

    Returns:
        dict: A dictionary containing the status of the health check.
    """
    try:
        version = await authenticator.get_version_async()
        return {"status": "UP", "version": version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
