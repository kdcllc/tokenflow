import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Set the X_AUTH_TOKEN environment variable for testing
os.environ['X_AUTH_TOKEN'] = 'test_token'

# Add the directory containing main.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')

from main import app, TokenRequest

client = TestClient(app)

def test_health_check():
    response = client.get("/health", headers={"X-Auth-Token": os.getenv('X_AUTH_TOKEN')})
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}

def test_get_device_code():
    user_id = "test_user"
    response = client.post(f"/device-code/{user_id}", headers={"X-Auth-Token": os.getenv('X_AUTH_TOKEN')})
    assert response.status_code == 200
    assert "url" in response.json()
    assert "device_code" in response.json()

def test_get_token():
    user_id = "test_user"
    token_request = TokenRequest(resource="test_resource")
    
    with patch('authenticator.AzureAuthenticator.authenticate') as mock_authenticate:
        mock_authenticate.return_value = None
        with patch('authenticator.AzureAuthenticator.get_token_thread_safe') as mock_get_token_thread_safe:
            mock_get_token_thread_safe.return_value = {
                "accessToken": "test_token",
                "expiresOn": "2023-12-31T23:59:59.000Z",
                "expires_on": 1672531199,
                "subscription": "test_subscription",
                "tenant": "test_tenant",
                "tokenType": "Bearer"
            }
            response = client.post(f"/token/{user_id}", json=token_request.dict(), headers={"X-Auth-Token": os.getenv('X_AUTH_TOKEN')})
            assert response.status_code == 200
            assert "accessToken" in response.json()
            assert "expiresOn" in response.json()
            assert "expires_on" in response.json()
            assert "subscription" in response.json()
            assert "tenant" in response.json()
            assert "tokenType" in response.json()
