#!/bin/bash

# Exit on any error
set -e

# AWS ECR Registry
AWS_ACCOUNT_ID="715841361707"
AWS_REGION="eu-north-1"
REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REGISTRY

# Build and push API Gateway Service
echo "Building and pushing api-gateway..."

# Build the Docker image
cd api-gateway
docker build --platform linux/amd64 -t $REGISTRY/api-gateway:latest .

# Push to ECR
docker push $REGISTRY/api-gateway:latest

# Go back to parent directory
cd ..

echo "api-gateway build and push completed"

# Update Kubernetes deployment
echo "Updating Kubernetes deployment for api-gateway..."

# Create namespace if it doesn't exist
kubectl create namespace api-gateway --dry-run=client -o yaml | kubectl apply -f -

# Apply deployment with environment variables substituted
envsubst < api-gateway/k8s/deployment.yaml | kubectl apply -f -

# Delete pods to force pull of new images
kubectl delete pods -n api-gateway -l app=api-gateway --force

echo "API Gateway deployment completed successfully!"

# Watch pods status
echo "Watching pods status..."
kubectl get pods -n api-gateway 