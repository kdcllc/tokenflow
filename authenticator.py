import json
import os
import re
import subprocess
import threading
import asyncio
import time
import logging

from fastapi import HTTPException
import pexpect
import functools


class AzureAuthenticator:
    def __init__(self):
        self.users_data = {}
        self.lock = threading.Lock()

    async def get_device_code(self, user_id: str):
        # Set the environment variable
        env = self.set_env(user_id)
        # run az logout to clear any existing sessions
        logging.info("Logging out of Azure CLI...")
        result = subprocess.run(['az', 'logout'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        # make sure the user is logged out
        time.sleep(5)
        if result.returncode != 0:
            logging.error(f"Failed to logout: {result.stderr.decode('utf-8')}")
        else:
            logging.info("Logged out of Azure CLI.")

        # Execute the command
        child = pexpect.spawn('az login --use-device-code', env=env, timeout=120)

        logging.debug("Launching a device code process...")

        index = child.expect(['To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code .* to authenticate.', pexpect.EOF])
        logging.debug(str(child.before))

        if index == 0:
            # Extract the device code from the output
            match = re.search('enter the code (.*?) to authenticate', child.after.decode())
            if match:
                device_code = match.group(1)
                logging.debug(f"Device code: {device_code}")
            else:
                logging.error("Could not extract device code")
                raise HTTPException(status_code=500, detail="Could not extract device code")
        elif index == 1:
            logging.error("Command exited before device code was provided")
            raise HTTPException(status_code=500, detail="Command exited before device code was provided")

        with self.lock:
            self.users_data[user_id] = {'child': child}

        logging.info("Device code process completed successfully.")

        url = 'https://microsoft.com/devicelogin'
        return url, device_code

    def set_env(self, user_id):
        # to utilize the multiple user login experience, we need to set the environment variable AZURE_CONFIG_DIR
        # https://github.com/microsoft/azure-pipelines-tasks/issues/8314

        temp_dir = self.get_temp_dir(user_id)
        env = os.environ.copy()
        env['AZURE_CONFIG_DIR'] = temp_dir

        # Ensure the directory exists
        os.makedirs(env['AZURE_CONFIG_DIR'], exist_ok=True)

        # execute az config set core.login_experience_v2=off
        command = ['az', 'config', 'set', 'core.login_experience_v2=off']
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

        if result.returncode != 0:
            logging.error(f"Failed to set login_experience_v2: {
                          result.stderr.decode('utf-8')}")
        else:
            logging.info("az config set login_experience_v2 successfully")

        # New command to only show errors
        error_command = ['az', 'config', 'set', 'core.only_show_errors=yes']
        error_result = subprocess.run(
            error_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

        if error_result.returncode != 0:
            logging.error(f"Failed to set only_show_errors: {
                        error_result.stderr.decode('utf-8')}")
        else:
            logging.info("az config set only_show_errors set successfully")

        return env
    
    def get_temp_dir(self, user_id: str):
        if os.path.exists('/.dockerenv'):
            # We are running inside a Docker container
            # /root/.temp/user_id
            temp_dir = os.path.join('/app/.temp', user_id)
            logging.info(f"Running inside a Docker container. Temp directory: {temp_dir}")
        else:
            # We are not running inside a Docker container
            temp_dir = os.path.join(os.path.expanduser('~'), '.temp', user_id)
            logging.info(f"Running outside a Docker container. Temp directory: {temp_dir}")
        
        # Ensure the directory exists
        os.makedirs(temp_dir, exist_ok=True)

        return temp_dir

    async def get_token(self, user_id: str, resource: str):
        try:
            # Wait for the command to finish
            child = self.users_data[user_id]['child']
            child.close(True)
            logging.debug(f'{child.exitstatus}-{child.signalstatus}')

            output = child.before.decode() + child.after.decode()
            logging.debug(output)
        except KeyError:
            logging.warning(f"No child process found for user {user_id}. Continuing execution.")

        env = self.set_env(user_id)

        # Execute the command
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, functools.partial(subprocess.run, ['az', 'account', 'get-access-token', '--resource', resource], capture_output=True, text=True, env=env))

        # Check if the command was successful
        if result.returncode != 0:
            raise Exception(f'Command failed with exit code {result.returncode}: {result.stderr}')

        # Parse the output as JSON
        token_info = json.loads(result.stdout)
        return token_info 

    async def check_az_login(self):
        # Execute the command
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, functools.partial(subprocess.run, ['az', 'account', 'get-access-token'], capture_output=True, text=True))

        # Check if the output equals the specified string
        if result.stdout.strip() == 'Please run "az login" to access your accounts.':
            return False
        else:
            return True
    
    async def authenticate(self, user_id: str, resource: str):
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                token = await self.get_token(user_id, resource)

                logging.info("Authentication successful.")
                return token
            except Exception as e:
                error_message = str(e)
                if 'az login' in error_message:
                    logging.error("'az login' found in the error message. Returning None.")
                    return None

            logging.error("Waiting for user to authenticate..." + error_message)
            await asyncio.sleep(10)
            retry_count += 1

        if retry_count == max_retries:
            logging.error("Authentication failed after 3 attempts.")
        
        return None
