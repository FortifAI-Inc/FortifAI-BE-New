#!/bin/bash

# Exit on any error
set -e

# AWS ECR Registry
REGISTRY="715841361707.dkr.ecr.eu-north-1.amazonaws.com"
REGION="eu-north-1"

# Function to build and push a service
build_and_push() {
    local SERVICE=$1
    local SERVICE_PATH=$2
    echo "Building and pushing $SERVICE..."
    
    # Check if directory exists
    if [ ! -d "$SERVICE_PATH" ]; then
        echo "Error: Directory $SERVICE_PATH does not exist"
        return 1
    fi
    
    # Build the Docker image
    cd "$SERVICE_PATH" || exit 1
    echo "Building Docker image for $SERVICE in $(pwd)..."
    docker build --platform linux/amd64 -t "$REGISTRY/$SERVICE" .
    
    # Push to ECR
    echo "Pushing $SERVICE to ECR..."
    docker push "$REGISTRY/$SERVICE"
    
    # Go back to parent directory
    cd - > /dev/null
    
    echo "$SERVICE build and push completed"
    return 0
}

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY

echo "Starting rebuild and deployment process..."

# Build and push each service
services=(
    "data-access-service:microservices/data-access-service"
    "ai-detector:microservices/ai-detector"
    "assets-monitor:microservices/assets-monitor"
    "data-layer:data-layer"
    "api-gateway:api-gateway"
)

for service_info in "${services[@]}"; do
    IFS=':' read -r service_name service_path <<< "$service_info"
    if ! build_and_push "$service_name" "$service_path"; then
        echo "Failed to build and push $service_name"
        exit 1
    fi
done

echo "All services built and pushed successfully!"

# Delete existing pods to force pull of new images
echo "Deleting existing pods..."
for namespace in data-layer api-gateway microservices; do
    echo "Deleting pods in $namespace namespace..."
    kubectl delete pods -n "$namespace" --all || echo "No pods found in $namespace namespace"
done

echo "Watching pods status..."
kubectl get pods -A -w | grep -E 'data-access|api-gateway|ai-detector|assets-monitor|analytics-service|data-layer' 