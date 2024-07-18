import json
import os
import re
import subprocess
import threading
import asyncio
import time
import logging

import pexpect
import functools

logger = logging.getLogger(__name__)


class AzureAuthenticator:
    def __init__(self):
        self.users_data = {}
        self.lock = threading.Lock()

    async def get_device_code_async(self, user_id: str):
        """
        Retrieves the device code for Azure CLI authentication.

        Args:
            user_id (str): The user ID.

        Returns:
            tuple: A tuple containing the URL for device login and the device code.

        Raises:
            Exception: If there is an error retrieving the device code.
        """

        # Set the environment variable
        env = self.__set_env(user_id)

        # run az logout to clear any existing sessions
        logger.info(f"User: {user_id} logging out of Azure CLI...")

        result = subprocess.run(
            ['az', 'logout'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

        # make sure the user is logged out
        time.sleep(5)

        if result.returncode != 0:
            logger.error(f"User: {user_id} failed to logout: {
                         result.stderr.decode('utf-8')}")
        else:
            logger.info(f"User: {user_id} logged out of Azure CLI.")

        # Execute the command
        child = pexpect.spawn(
            'az login --use-device-code', env=env, timeout=120)

        logger.debug(f"User: {user_id} launching a device code process...")

        index = child.expect(
            ['To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code .* to authenticate.', pexpect.EOF])
        logger.debug(str(child.before))

        if index == 0:
            # Extract the device code from the output
            match = re.search(
                'enter the code (.*?) to authenticate', child.after.decode())
            if match:
                device_code = match.group(1)
                logger.debug(f"User: {user_id} device code: {
                             device_code} was created successfully.")
            else:
                ex = f"User: {
                    user_id} could not extract device code successfully."
                logger.error(ex)
                raise Exception(ex)
        elif index == 1:
            ex = f"User: {
                user_id} command exited before device code was provided."
            logger.error(ex)
            raise Exception(ex)

        with self.lock:
            self.users_data[user_id] = {'child': child}

        logger.info(
            f"User: {user_id} device code process completed successfully.")

        url = 'https://microsoft.com/devicelogin'
        return url, device_code

    async def check_az_login_async(self, user_id: str):
        """
        Checks if the user is logged in to Azure CLI.

        Returns:
            bool: True if the user is logged in, False otherwise.
        """
        env = self.__set_env(user_id=user_id)

        # Execute the command
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, functools.partial(subprocess.run, ['az', 'account', 'get-access-token'], capture_output=True, text=True, env=env))

        if re.search(r"Please run 'az login'.*to setup account", result.stderr):
            # Your code here
            logger.warning(f"{result.stderr}")
            return False
        else:
            return True

    def __set_env(self, user_id):
        # to utilize the multiple user login experience, we need to set the environment variable AZURE_CONFIG_DIR
        # https://github.com/microsoft/azure-pipelines-tasks/issues/8314

        temp_dir = self.__get_temp_dir(user_id)
        env = os.environ.copy()
        env['AZURE_CONFIG_DIR'] = temp_dir

        # Ensure the directory exists
        os.makedirs(env['AZURE_CONFIG_DIR'], exist_ok=True)

        # execute az config set core.login_experience_v2=off
        command = ['az', 'config', 'set', 'core.login_experience_v2=off']
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

        if result.returncode != 0:
            logger.error(f"Failed to set login_experience_v2: {
                         result.stderr.decode('utf-8')}")
        else:
            logger.debug("az config set login_experience_v2 successfully")

        # New command to only show errors
        error_command = ['az', 'config', 'set', 'core.only_show_errors=yes']
        error_result = subprocess.run(
            error_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

        if error_result.returncode != 0:
            logger.error(f"Failed to set only_show_errors: {
                         error_result.stderr.decode('utf-8')}")
        else:
            logger.debug("az config set only_show_errors set successfully")

        return env

    def __get_temp_dir(self, user_id: str):

        temp_dir = os.path.join(os.path.expanduser('~'), '.temp', user_id)
        logger.info(
            f"User: {user_id} - temp directory: {temp_dir}")

        # Ensure the directory exists
        os.makedirs(temp_dir, exist_ok=True)

        return temp_dir

    async def __get_token_async(self,
                                user_id: str,
                                resource: str,
                                subscription_id: str = None,
                                tenant_id: str = None):
        try:
            # Wait for the command to finish
            child = self.users_data[user_id]['child']
            child.close(True)
            logger.debug(f'{child.exitstatus}-{child.signalstatus}')

            output = child.before.decode() + child.after.decode()
            logger.debug(output)
        except KeyError:
            logger.warning(f"No child process found for user {
                           user_id}. Continuing execution.")

        env = self.__set_env(user_id)

        command = ['az', 'account', 'get-access-token', '--resource', resource]
        if subscription_id and not tenant_id:
            command.extend(['--subscription', subscription_id])

        if tenant_id:
            command.extend(['--tenant', tenant_id])

        # Execute the command
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, functools.partial(subprocess.run, command, capture_output=True, text=True, env=env))

        # Check if the command was successful
        if result.returncode != 0:
            raise Exception(f'az account get-access-token --resource {
                            resource} command failed with exit code {result.returncode}: {result.stderr}')

        # Parse the output as JSON
        token_info = json.loads(result.stdout)
        return token_info

    async def get_list_of_subscriptions_async(self, user_id: str):
        """
        Retrieves a list of azure subscriptions for the specified azure user.

        Args:
            user_id (str): The ID of the user.

        Returns:
            list: A list of subscriptions.

        Raises:
            Exception: If the command fails with a non-zero exit code.
        """

        # Set the environment variable
        env = self.__set_env(user_id)

        # Execute the command
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, functools.partial(subprocess.run, ['az', 'account', 'list'], capture_output=True, text=True, env=env))

        # Check if the command was successful
        if result.returncode != 0:
            raise Exception(f'az account list command failed with exit code {
                            result.returncode}: {result.stderr}')

        # Parse the output as JSON
        subscriptions = json.loads(result.stdout)
        return subscriptions

    async def authenticate_async(self, user_id: str, resource: str):
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                token = await self.__get_token_async(user_id, resource)

                logger.info("Authentication successful.")
                return token
            except Exception as e:
                error_message = str(e)
                if 'az login' in error_message:
                    logger.error(
                        "'az login' found in the error message. Returning None.")
                    return None

            logger.error("Waiting for user to authenticate..." + error_message)
            await asyncio.sleep(10)
            retry_count += 1

        if retry_count == max_retries:
            logger.error("Authentication failed after 3 attempts.")

        return None

    async def get_version_async(self):
        """
        Retrieves the version of the Azure CLI.

        Returns:
            str: The version of the Azure CLI.
        """
        # Execute the command
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, functools.partial(subprocess.run, ['az', '--version'], capture_output=True, text=True))

        if result.returncode != 0:
            raise Exception(f'az --version command failed with exit code {result.returncode}: {result.stderr}')

        # Extract the version from the output
        version_match = re.search(r'azure-cli\s+(\S+)', result.stdout)
        if version_match:
            return version_match.group(1)
        else:
            raise Exception('Failed to parse Azure CLI version from output')
