#!/bin/bash

# Exit on any error
set -e

# AWS ECR Registry
REGISTRY="715841361707.dkr.ecr.eu-north-1.amazonaws.com"
REGION="eu-north-1"

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY

# Build and push AI Detector Service
echo "Building and pushing ai-detector..."

# Build the Docker image
cd microservices/ai-detector
docker build --platform linux/amd64 -t $REGISTRY/ai-detector:latest .

# Push to ECR
docker push $REGISTRY/ai-detector:latest

# Go back to parent directory
cd ../..

echo "ai-detector build and push completed"

# Update Kubernetes deployment
echo "Updating Kubernetes deployment for ai-detector..."

# Create namespace if it doesn't exist
kubectl create namespace microservices --dry-run=client -o yaml | kubectl apply -f -

# Apply deployment
kubectl apply -f microservices/ai-detector/k8s/deployment.yaml

# Delete pods to force pull of new images
kubectl delete pods -n microservices -l app=ai-detector --force

echo "AI Detector deployment completed successfully!"

# Watch pods status
echo "Watching pods status..."
kubectl get pods -n microservices -l app=ai-detector 