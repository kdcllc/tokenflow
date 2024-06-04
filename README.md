# TokenFlow

TenantTokenFlow optimizes token generation and directory management across multiple tenants using Azure device flow. This repository empowers applications to capture user tokens seamlessly and utilize them for creating app registrations, users, and groups within accessible directories. Unlock the potential of multi-tenant applications with TenantTokenFlow.

## Running Locally

To run the application locally, follow these steps:

1. **Create a virtual environment:**

    ```bash
    python -m venv .venv
    ```

2. **Activate the virtual environment:**

    ```bash
    source .venv/bin/activate
    ```

3. **Install the dependencies management tool:**

    ```bash
    pip install pip-tools
    ```

4. **Compile the requirements:**

    ```bash
    pip-compile requirements.in
    ```

5. **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

6. **Run the application:**

    ```bash
    uvicorn main:app --reload
    ```

## Deploy the Container

To deploy the application using Docker, use the following steps:

1. **Pull the Docker container:**

    ```bash
    docker pull kdcllc/tokenflow
    ```

2. **Run the Docker container:**

    ```bash
    docker run -e LOGGING_LEVEL=INFO -e X_AUTH_TOKEN=<your_auth_token> -p 6700:6700 kdcllc/tokenflow
    ```

## API Documentation

Swagger documentation is available at [http://localhost:6700/docs](http://localhost:6700/docs).

## Environment Variables

- `LOGGING_LEVEL`: Sets the logging level (default is `INFO`).
- `X_AUTH_TOKEN`: Your authentication token for accessing the application.
