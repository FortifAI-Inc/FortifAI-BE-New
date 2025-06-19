#!/bin/bash

# Deploy Dynamic Certificate Manager
# This script builds and deploys the dynamic certificate manager service

set -e

echo "🚀 Deploying Dynamic Certificate Manager"
echo "========================================"

# Configuration
ECR_REGISTRY="715841361707.dkr.ecr.eu-north-1.amazonaws.com"
SERVICE_NAME="dynamic-cert-manager"
REGION="eu-north-1"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Create ECR repository if it doesn't exist
echo "📦 Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $SERVICE_NAME --region $REGION 2>/dev/null || \
aws ecr create-repository --repository-name $SERVICE_NAME --region $REGION

# Build Docker image
echo "🔨 Building Docker image..."
cd microservices/dynamic-cert-manager
docker build --platform linux/amd64 -t $SERVICE_NAME .

# Tag and push image
echo "📤 Pushing image to ECR..."
docker tag $SERVICE_NAME:latest $ECR_REGISTRY/$SERVICE_NAME:latest
docker push $ECR_REGISTRY/$SERVICE_NAME:latest

# Go back to root directory
cd ../..

# Create namespace if it doesn't exist
echo "🏗️ Creating namespace..."
kubectl create namespace microservices --dry-run=client -o yaml | kubectl apply -f -

# Create CA secret if it doesn't exist
echo "🔐 Creating CA secret..."
if ! kubectl get secret glassbox-ca-secret -n microservices >/dev/null 2>&1; then
    # Create temporary CA files if they don't exist
    if [ ! -f /tmp/ca.crt ] || [ ! -f /tmp/ca.key ]; then
        echo "⚠️  CA files not found. Creating temporary CA..."
        openssl genrsa -out /tmp/ca.key 4096
        openssl req -new -x509 -days 365 -key /tmp/ca.key -out /tmp/ca.crt \
            -subj "/C=US/ST=State/L=City/O=GlassBox/CN=GlassBox CA"
    fi
    
    kubectl create secret generic glassbox-ca-secret \
        --from-file=ca.crt=/tmp/ca.crt \
        --from-file=ca.key=/tmp/ca.key \
        -n microservices
fi

# Deploy the service
echo "🚀 Deploying to Kubernetes..."
kubectl apply -f microservices/dynamic-cert-manager/k8s/deployment.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl rollout status deployment/dynamic-cert-manager -n microservices --timeout=300s

# Get service information
echo "✅ Deployment completed!"
echo ""
echo "📊 Service Status:"
kubectl get pods -n microservices -l app=dynamic-cert-manager
echo ""
echo "🌐 Service Info:"
kubectl get svc dynamic-cert-manager -n microservices
echo ""
echo "🔍 Service Endpoints:"
kubectl get endpoints dynamic-cert-manager -n microservices

# Test the service
echo ""
echo "🧪 Testing service health..."
CLUSTER_IP=$(kubectl get svc dynamic-cert-manager -n microservices -o jsonpath='{.spec.clusterIP}')
echo "Cluster IP: $CLUSTER_IP"

# Test from within cluster (using a temporary pod)
echo "Testing health endpoint..."
kubectl run test-pod --rm -i --tty --restart=Never --image=curlimages/curl -- \
    curl -s http://$CLUSTER_IP:8443/health || echo "Health check failed"

echo ""
echo "🎉 Dynamic Certificate Manager deployed successfully!"
echo "📋 Service accessible at: $CLUSTER_IP:8443"
echo "🔐 SDS endpoint: http://$CLUSTER_IP:8443/v3/discovery:secrets"
echo "🌐 API Gateway endpoint: /api/v1/dynamic-cert-manager/*" 