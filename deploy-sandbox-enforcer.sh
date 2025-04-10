#!/bin/bash

# Exit on any error
set -e

# AWS ECR Registry
REGISTRY="715841361707.dkr.ecr.eu-north-1.amazonaws.com"
REGION="eu-north-1"

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY

# Build and push Sandbox Enforcer Service
echo "Building and pushing sandbox-enforcer..."

# Build the Docker image
cd microservices/sandbox-enforcer
docker build --platform linux/amd64 -t $REGISTRY/sandbox-enforcer:latest .

# Push to ECR
docker push $REGISTRY/sandbox-enforcer:latest

# Go back to parent directory
cd ../..

echo "sandbox-enforcer build and push completed"

# Update Kubernetes deployment
echo "Updating Kubernetes deployment for sandbox-enforcer..."

# Create namespace if it doesn't exist
kubectl create namespace microservices --dry-run=client -o yaml | kubectl apply -f -

# Apply deployment
kubectl apply -f microservices/sandbox-enforcer/k8s/deployment.yaml

# Delete pods to force pull of new images
kubectl delete pods -n microservices -l app=sandbox-enforcer --force

echo "Sandbox Enforcer deployment completed successfully!"

# Watch pods status
echo "Watching pods status..."
kubectl get pods -n microservices -l app=sandbox-enforcer 