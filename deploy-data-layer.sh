#!/bin/bash
set -e
REGISTRY="715841361707.dkr.ecr.eu-north-1.amazonaws.com"
REGION="eu-north-1"
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY
echo "Building and pushing data-layer..."
cd data-layer
docker build --platform linux/amd64 -t $REGISTRY/data-layer:latest .
docker push $REGISTRY/data-layer:latest
cd ..
echo "Updating Kubernetes deployment for data-layer..."
kubectl create namespace data-layer --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f data-layer/k8s/deployment.yaml
kubectl delete pods -n data-layer -l app=data-layer --force
echo "Data Layer deployment completed successfully!"
echo "Watching pods status..."
kubectl get pods -n data-layer -l app=data-layer
