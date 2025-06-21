#!/bin/bash
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd "$SCRIPT_DIR"

# Exit on error
set -e

# Configuration
SERVICE_NAME="events-logger"
SERVICE_DIR="microservices/${SERVICE_NAME}"
ECR_REPO="715841361707.dkr.ecr.eu-north-1.amazonaws.com"
DOCKER_IMAGE="${SERVICE_NAME}:latest"
K8S_NAMESPACE="microservices"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${RED}🚀 NON-GRACEFUL DEPLOYMENT: ${SERVICE_NAME}${NC}"
echo -e "${RED}⚠️  WARNING: This will forcefully terminate existing pods!${NC}"

# Login to Docker
echo -e "${YELLOW}Logging in to Docker...${NC}"
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin ${ECR_REPO}

# Build Docker image with no cache
echo -e "${YELLOW}Building Docker image (no cache)...${NC}"
cd ${SERVICE_DIR}
docker build --no-cache --platform linux/amd64 -t ${DOCKER_IMAGE} .

# Tag and push to ECR
echo -e "${YELLOW}Pushing to ECR...${NC}"
docker tag ${DOCKER_IMAGE} ${ECR_REPO}/${DOCKER_IMAGE}
docker push ${ECR_REPO}/${DOCKER_IMAGE}

# Go back to parent directory
cd ../..

# Force delete existing pods immediately
echo -e "${RED}Force deleting existing ${SERVICE_NAME} pods...${NC}"
kubectl delete pods -n ${K8S_NAMESPACE} -l app=${SERVICE_NAME} --force --grace-period=0 --ignore-not-found=true

# Force delete existing deployment
echo -e "${RED}Force deleting existing deployment...${NC}"
kubectl delete deployment ${SERVICE_NAME} -n ${K8S_NAMESPACE} --force --grace-period=0 --ignore-not-found=true

# Wait a moment for cleanup
sleep 2

# Create namespace if it doesn't exist
kubectl create namespace ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Deploy events-logger (fresh deployment)
echo -e "${YELLOW}Deploying events-logger (fresh deployment)...${NC}"
kubectl apply -f ${SERVICE_DIR}/k8s/deployment.yaml
kubectl apply -f ${SERVICE_DIR}/k8s/service.yaml

# Force restart any existing deployment
echo -e "${RED}Force restarting deployment...${NC}"
kubectl rollout restart deployment ${SERVICE_NAME} -n ${K8S_NAMESPACE} || true

# Force delete pods again to ensure new image is pulled
echo -e "${RED}Final force deletion to ensure new image pull...${NC}"
kubectl delete pods -n ${K8S_NAMESPACE} -l app=${SERVICE_NAME} --force --grace-period=0 --ignore-not-found=true

echo -e "${GREEN}✅ NON-GRACEFUL Events Logger deployment completed!${NC}"
echo -e "${YELLOW}📊 Checking pod status...${NC}"
kubectl get pods -n ${K8S_NAMESPACE} -l app=${SERVICE_NAME} 