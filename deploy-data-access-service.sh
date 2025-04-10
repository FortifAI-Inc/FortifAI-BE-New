#!/bin/bash

# Exit on error
set -e

# Configuration
SERVICE_NAME="data-access-service"
SERVICE_DIR="microservices/${SERVICE_NAME}"
ECR_REPO="715841361707.dkr.ecr.eu-north-1.amazonaws.com"
DOCKER_IMAGE="${SERVICE_NAME}:latest"
K8S_NAMESPACE="microservices"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Deploying ${SERVICE_NAME}...${NC}"

# Login to Docker
echo -e "${YELLOW}Logging in to Docker...${NC}"
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin ${ECR_REPO}

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
cd ${SERVICE_DIR}
docker build --platform linux/amd64 -t ${DOCKER_IMAGE} .

# Tag and push to ECR
echo -e "${YELLOW}Pushing to ECR...${NC}"
docker tag ${DOCKER_IMAGE} ${ECR_REPO}/${DOCKER_IMAGE}
docker push ${ECR_REPO}/${DOCKER_IMAGE}

# Update Kubernetes deployment
echo -e "${YELLOW}Updating Kubernetes deployment...${NC}"
kubectl rollout restart deployment ${SERVICE_NAME} -n ${K8S_NAMESPACE}

# Wait for rollout to complete
echo -e "${YELLOW}Waiting for rollout to complete...${NC}"
kubectl rollout status deployment ${SERVICE_NAME} -n ${K8S_NAMESPACE}

echo -e "${GREEN}Deployment completed successfully!${NC}" 