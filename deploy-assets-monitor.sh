#!/bin/bash

# Exit on error
set -e

# Login to Amazon ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 715841361707.dkr.ecr.eu-north-1.amazonaws.com

# Build and push the Docker image
echo "Building and pushing assets-monitor image..."
docker build --platform linux/amd64 -t assets-monitor:latest ./microservices/assets-monitor
docker tag assets-monitor:latest 715841361707.dkr.ecr.eu-north-1.amazonaws.com/assets-monitor:latest
docker push 715841361707.dkr.ecr.eu-north-1.amazonaws.com/assets-monitor:latest

# Update the Kubernetes deployment
echo "Updating Kubernetes deployment..."
kubectl rollout restart deployment assets-monitor -n microservices

# Wait for the rollout to complete
echo "Waiting for rollout to complete..."
kubectl rollout status deployment assets-monitor -n microservices

echo "Deployment completed successfully!" 