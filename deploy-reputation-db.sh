#!/bin/bash
set -e

# Check if the ECR repository exists, create it if not
REPO_NAME="reputation-db"
REGION="eu-north-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}"

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Check if repository exists
if ! aws ecr describe-repositories --repository-names ${REPO_NAME} --region ${REGION} > /dev/null 2>&1; then
    echo "Creating ECR repository: ${REPO_NAME}"
    aws ecr create-repository --repository-name ${REPO_NAME} --region ${REGION}
fi

# Build and push the Docker image
echo "Building Docker image for ${REPO_NAME} in $(pwd)/microservices/${REPO_NAME}..."
cd microservices/${REPO_NAME}
docker build --platform=linux/amd64 -t ${ECR_REPOSITORY}:latest .
echo "Pushing ${REPO_NAME} to ECR..."
docker push ${ECR_REPOSITORY}:latest

cd ../..

# Create ECR pull secret if it doesn't exist
echo "Checking for ECR pull secret..."
if ! kubectl get secret ecr-registry-secret -n microservices > /dev/null 2>&1; then
    echo "Creating ECR pull secret..."
    kubectl create secret docker-registry ecr-registry-secret \
        --docker-server=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com \
        --docker-username=AWS \
        --docker-password=$(aws ecr get-login-password --region ${REGION}) \
        -n microservices
fi

# Apply Kubernetes deployments
echo "Applying Kubernetes deployments..."
kubectl apply -f microservices/${REPO_NAME}/service.yaml
kubectl apply -f microservices/${REPO_NAME}/deployment.yaml

# Force a rollout restart to ensure the new image is used
echo "Forcing deployment rollout..."
kubectl rollout restart deployment/${REPO_NAME} -n microservices

# Wait for rollout to complete
echo "Waiting for rollout to complete..."
kubectl rollout status deployment/${REPO_NAME} -n microservices --timeout=180s

echo "Deployment complete for ${REPO_NAME}!"
echo "You can check the service status with: kubectl get svc ${REPO_NAME}-svc -n microservices"
echo "And check the pod status with: kubectl get pods -l app=${REPO_NAME} -n microservices"

echo "Applying updated ingress configuration..."
kubectl apply -f ingress.yaml

echo "Deployment completed successfully!" 