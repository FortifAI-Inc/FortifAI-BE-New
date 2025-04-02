#!/bin/bash

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-eu-north-1}

# Replace environment variables in deployment.yaml
sed -i '' "s/\${AWS_ACCOUNT_ID}/$AWS_ACCOUNT_ID/g" deployment.yaml
sed -i '' "s/\${AWS_REGION}/$AWS_REGION/g" deployment.yaml

# Apply the deployment
kubectl apply -f deployment.yaml

# Restore the original deployment.yaml
sed -i '' "s/$AWS_ACCOUNT_ID/\${AWS_ACCOUNT_ID}/g" deployment.yaml
sed -i '' "s/$AWS_REGION/\${AWS_REGION}/g" deployment.yaml 