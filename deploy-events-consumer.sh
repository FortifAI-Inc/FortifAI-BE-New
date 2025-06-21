#!/bin/bash
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd "$SCRIPT_DIR"

# Exit on error
set -e

# Configuration
SERVICE_NAME="events-consumer"
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
docker build --no-cache --platform linux/amd64 -t ${DOCKER_IMAGE} .

# Tag and push to ECR
echo -e "${YELLOW}Pushing to ECR...${NC}"
docker tag ${DOCKER_IMAGE} ${ECR_REPO}/${DOCKER_IMAGE}
docker push ${ECR_REPO}/${DOCKER_IMAGE}

# Go back to parent directory
cd ../..

# Create namespace if it doesn't exist
kubectl create namespace ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Deploy events-consumer
echo -e "${YELLOW}Deploying events-consumer...${NC}"
kubectl apply -f ${SERVICE_DIR}/k8s/deployment.yaml

# Delete pods to force pull of new images
kubectl delete pods -n ${K8S_NAMESPACE} -l app=${SERVICE_NAME} --force

echo -e "${GREEN}Events Consumer deployment completed successfully!${NC}"

# Watch pods status
echo -e "${YELLOW}Watching pods status...${NC}"
kubectl get pods -n ${K8S_NAMESPACE} -l app=${SERVICE_NAME} 