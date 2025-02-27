# CI/CD Pipeline Setup for LCA-Cost-NHMzh

This document provides instructions for setting up the CI/CD pipeline for the LCA-Cost-NHMzh project.

## Overview

The CI/CD pipeline automates the following processes:

1. Building the Docker image
2. Running unit tests
3. Deploying the image to production (if tests pass)
4. Sending notifications about build/deployment status

## Required GitHub Secrets

To use the CI/CD pipeline, you need to set up the following secrets in your GitHub repository:

### Docker Hub Credentials

- `DOCKER_HUB_USERNAME`: Your Docker Hub username
- `DOCKER_HUB_TOKEN`: Your Docker Hub access token (not your password)

### Deployment Credentials

- `DEPLOY_HOST`: The hostname or IP address of your deployment server
- `DEPLOY_USERNAME`: The SSH username for your deployment server
- `DEPLOY_SSH_KEY`: The private SSH key for authentication
- `DEPLOY_PATH`: The path on the deployment server where the project is located

### Notification Settings

- `SLACK_WEBHOOK`: The webhook URL for Slack notifications

## Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Click on "Settings" > "Secrets and variables" > "Actions"
3. Click on "New repository secret"
4. Add each of the secrets listed above

## Generating a Docker Hub Access Token

1. Log in to [Docker Hub](https://hub.docker.com/)
2. Go to "Account Settings" > "Security"
3. Click on "New Access Token"
4. Give it a name (e.g., "GitHub Actions")
5. Copy the token and save it as `DOCKER_HUB_TOKEN` in GitHub Secrets

## Setting Up SSH Keys for Deployment

1. Generate an SSH key pair if you don't have one:

   ```bash
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com" -f ~/.ssh/deploy_key
   ```

2. Add the public key to the authorized_keys file on your deployment server:

   ```bash
   ssh-copy-id -i ~/.ssh/deploy_key.pub user@your-server
   ```

3. Add the private key content as `DEPLOY_SSH_KEY` in GitHub Secrets:
   ```bash
   cat ~/.ssh/deploy_key
   ```

## Setting Up Slack Notifications

1. Create a Slack app in your workspace
2. Enable Incoming Webhooks
3. Create a new webhook for your channel
4. Copy the webhook URL and save it as `SLACK_WEBHOOK` in GitHub Secrets

## Testing the Pipeline

After setting up all the secrets, you can test the pipeline by:

1. Making a small change to your codebase
2. Committing and pushing the change to your repository
3. Going to the "Actions" tab in your GitHub repository to monitor the workflow

## Troubleshooting

If you encounter issues with the CI/CD pipeline:

1. Check the workflow logs in the GitHub Actions tab
2. Verify that all secrets are correctly set up
3. Ensure your deployment server is accessible and has Docker and Docker Compose installed
4. Check that the Docker Hub credentials have permission to push to the repository
