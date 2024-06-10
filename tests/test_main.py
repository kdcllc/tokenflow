import sys
import os
import pytest
from fastapi.testclient import TestClient

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
    response = client.post(f"/token/{user_id}", json=token_request.dict(), headers={"X-Auth-Token": os.getenv('X_AUTH_TOKEN')})
    assert response.status_code == 200
    assert "accessToken" in response.json()
