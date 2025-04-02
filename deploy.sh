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
    local DIR=$2
    echo "Building and pushing $SERVICE from directory $DIR..."
    
    # Build the Docker image for linux/amd64 platform
    cd $DIR
    docker build --platform linux/amd64 -t $REGISTRY/$SERVICE:latest .
    
    # Push to ECR
    docker push $REGISTRY/$SERVICE:latest
    
    # Go back to parent directory
    cd ..
    if [ "$DIR" = "microservices/data-access-service" ]; then
        cd ..
    fi
    
    echo "$SERVICE build and push completed"
}

# Build and push each service
echo "Starting deployment process..."

# API Gateway Service
build_and_push "api-gateway" "api-gateway"

# Data Access Service
build_and_push "data-access-service" "microservices/data-access-service"

# Data Layer Service
build_and_push "data-layer" "data-layer"

# Update Kubernetes deployments
echo "Updating Kubernetes deployments..."

# Function to apply k8s configurations
apply_k8s() {
    local SERVICE=$1
    local NAMESPACE=$2
    local DIR=$3
    
    echo "Applying Kubernetes configurations for $SERVICE in namespace $NAMESPACE..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply deployment
    kubectl apply -f $DIR/k8s/deployment.yaml
    
    # Delete pods to force pull of new images
    kubectl delete pods -n $NAMESPACE -l app=$SERVICE --force
}

# Apply Kubernetes configurations for each service
apply_k8s "api-gateway" "api-gateway" "api-gateway"
apply_k8s "data-access-service" "microservice" "microservices/data-access-service"
apply_k8s "data-layer" "data-layer" "data-layer"

echo "Deployment completed successfully!"

# Watch pods status
echo "Watching pods status..."
kubectl get pods -A -w | grep -E 'api-gateway|microservice|data-layer' 