#
# docker build -t kdcllc/tokenflow .
#
# docker run -p 6700:8080 -e X_AUTH_TOKEN=169ddeb1-502a-42cf-a222-9dbb8ec2cbf6 -e LOGGING_LEVEL=DEBUG kdcllc/tokenflow
#
# docker push kdcllc/tokenflow

# Use the official Python 3.12 image from Docker Hub
FROM python:3.12

# Install necessary packages including lsb-release, then obtain the currently installed distribution and store an Azure CLI version of choice
RUN apt-get update && \
    apt-get install -y ca-certificates curl apt-transport-https lsb-release gnupg && \
    AZ_DIST=$(lsb_release -cs) && \
    AZ_VER=2.61.0 && \
    echo $AZ_DIST && echo $AZ_VER && \
    curl -sL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | tee /etc/apt/trusted.gpg.d/microsoft.asc.gpg > /dev/null && \
    echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $AZ_DIST main" | tee /etc/apt/sources.list.d/azure-cli.list && \
    apt-get update && \
    apt-get install -y azure-cli=${AZ_VER}-1~$AZ_DIST

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run the command to start Uvicorn
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8080"]