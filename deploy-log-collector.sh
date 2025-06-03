#!/bin/bash
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd "$SCRIPT_DIR"

# Exit on error
set -e

# Configuration
ECR_REGISTRY="715841361707.dkr.ecr.eu-north-1.amazonaws.com"
IMAGE_NAME="logs-collector"
IMAGE_TAG="latest"
FULL_IMAGE_NAME="${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building and deploying log-collector service..."

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin ${ECR_REGISTRY}

# Build the Docker image
echo "Building Docker image..."
cd microservices/logs-collector
docker build --platform linux/amd64 -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Tag and push to ECR
echo "Tagging and pushing to ECR..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${FULL_IMAGE_NAME}
docker push ${FULL_IMAGE_NAME}

# Create namespace if it doesn't exist
echo "Ensuring microservices namespace exists..."
kubectl create namespace microservices --dry-run=client -o yaml | kubectl apply -f -

# Force delete existing pods
echo "Forcefully deleting existing pods..."
kubectl delete pod -n microservices -l app=logs-collector --force --grace-period=0

# Apply Kubernetes configurations
echo "Applying Kubernetes configurations..."
kubectl apply -f k8s/

# Force pod recreation to ensure new image is pulled
echo "Forcing pod recreation..."
kubectl rollout restart deployment logs-collector -n microservices

# Wait for pods to be ready
echo "Waiting for pods to be ready..."
kubectl rollout status deployment logs-collector -n microservices

echo "Deployment completed successfully!" 