#!/bin/bash
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd "$SCRIPT_DIR"

# Exit on error
set -e

# Configuration
SERVICE_NAME="rabbitmq"
SERVICE_DIR="microservices/${SERVICE_NAME}"
K8S_NAMESPACE="microservices"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Deploying ${SERVICE_NAME}...${NC}"

# Deploy RabbitMQ
echo -e "${YELLOW}Deploying RabbitMQ...${NC}"
kubectl apply -f ${SERVICE_DIR}/rabbitmq.yaml

# Wait for RabbitMQ to be ready
echo -e "${YELLOW}Waiting for RabbitMQ to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app=rabbitmq -n ${K8S_NAMESPACE} --timeout=300s

echo -e "${GREEN}RabbitMQ deployment completed successfully!${NC}"
echo -e "${YELLOW}RabbitMQ Management UI available at: kubectl port-forward svc/rabbitmq 15672:15672 -n microservices${NC}"
echo -e "${YELLOW}Default credentials: glassbox / glassbox123${NC}" 