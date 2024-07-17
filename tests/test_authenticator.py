import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add the directory containing authenticator.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')

from token_authenticator import AzureAuthenticator

@pytest.fixture
def authenticator():
    return AzureAuthenticator()

def test_set_env(authenticator):
    user_id = "test_user"
    with patch('os.makedirs') as mock_makedirs, \
         patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        env = authenticator.set_env(user_id)
        assert 'AZURE_CONFIG_DIR' in env
        assert mock_makedirs.call_count >= 1
        mock_run.assert_called_once()

def test_get_temp_dir(authenticator):
    user_id = "test_user"
    with patch('os.makedirs') as mock_makedirs:
        temp_dir = authenticator.get_temp_dir(user_id)
        assert user_id in temp_dir
        mock_makedirs.assert_called_once()

def test_get_device_code(authenticator):
    user_id = "test_user"
    with patch('pexpect.spawn') as mock_spawn, \
         patch('re.search') as mock_search, \
         patch('os.makedirs'), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_child = MagicMock()
        mock_child.expect.return_value = 0
        mock_child.after.decode.return_value = "enter the code ABC123 to authenticate"
        mock_spawn.return_value = mock_child
        mock_search.return_value.group.return_value = "ABC123"
        
        url, device_code = authenticator.get_device_code(user_id)
        assert url == 'https://microsoft.com/devicelogin'
        assert device_code == "ABC123"

def test_get_token(authenticator):
    user_id = "test_user"
    resource = "test_resource"
    with patch('subprocess.run') as mock_run, \
         patch('os.makedirs'), \
         patch('authenticator.AzureAuthenticator.set_env') as mock_set_env:
        mock_set_env.return_value = os.environ.copy()
        mock_child = MagicMock()
        mock_child.before.decode.return_value = ""
        mock_child.after.decode.return_value = ""
        authenticator.users_data[user_id] = {'child': mock_child}
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"accessToken": "test_token"}'
        
        token_info = authenticator.get_token(user_id, resource)
        assert token_info['accessToken'] == "test_token"

def test_authenticate(authenticator):
    user_id = "test_user"
    resource = "test_resource"
    with patch('authenticator.AzureAuthenticator.get_token') as mock_get_token, \
         patch('time.sleep'):
        mock_get_token.side_effect = [{"accessToken": "test_token"}, Exception("error")]
        authenticator.users_data[user_id] = {'token': None}
        
        authenticator.authenticate(user_id, resource)
        assert authenticator.users_data[user_id]['token']['accessToken'] == "test_token"

def test_get_token_thread_safe(authenticator):
    user_id = "test_user"
    authenticator.users_data[user_id] = {'token': "test_token"}
    token = authenticator.get_token_thread_safe(user_id)
    assert token == "test_token"
