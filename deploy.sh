#!/bin/bash

# Exit on any error
set -e

# AWS ECR Registry
REGISTRY="715841361707.dkr.ecr.eu-north-1.amazonaws.com"
REGION="eu-north-1"

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY

# Function to build and push a service
build_and_push() {
    local SERVICE=$1
    echo "Building and pushing $SERVICE..."
    
    # Build the Docker image
    cd $SERVICE
    docker build -t $REGISTRY/fortifai/$SERVICE:latest .
    
    # Push to ECR
    docker push $REGISTRY/fortifai/$SERVICE:latest
    
    # Go back to parent directory
    cd ..
    
    echo "$SERVICE build and push completed"
}

# Build and push each service
echo "Starting deployment process..."

# Data Access Service
build_and_push "data-access-service"

# Analytics Service
build_and_push "analytics-service"

# IAM Service (if it has a Dockerfile)
if [ -f "iam/Dockerfile" ]; then
    build_and_push "iam"
fi

# Update Kubernetes deployments
echo "Updating Kubernetes deployments..."

# Function to apply k8s configurations
apply_k8s() {
    local SERVICE=$1
    local NAMESPACE=$2
    
    echo "Applying Kubernetes configurations for $SERVICE in namespace $NAMESPACE..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply deployment
    kubectl apply -f $SERVICE/k8s/deployment.yaml
    
    # Delete pods to force pull of new images
    kubectl delete pods -n $NAMESPACE -l app=$SERVICE --force
}

# Apply Kubernetes configurations for each service
apply_k8s "data-access-service" "data-access"
apply_k8s "analytics-service" "analytics"

if [ -f "iam/k8s/deployment.yaml" ]; then
    apply_k8s "iam" "iam"
fi

echo "Deployment completed successfully!"

# Watch pods status
echo "Watching pods status..."
kubectl get pods -A -w | grep -E 'data-access|analytics|iam' 