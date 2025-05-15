#!/bin/bash

# Get the node role name
NODE_ROLE=$(aws iam list-roles --query 'Roles[?contains(RoleName, `eksctl-fortifai-cluster-nodegroup`)].RoleName' --output text)

if [ -z "$NODE_ROLE" ]; then
    echo "Could not find node role"
    exit 1
fi

# Create the policy
aws iam create-policy \
    --policy-name FortifAICloudTrailAccess \
    --policy-document file://cloudtrail-policy.json

# Attach the policy to the node role
aws iam attach-role-policy \
    --role-name $NODE_ROLE \
    --policy-arn arn:aws:iam::715841361707:policy/FortifAICloudTrailAccess

echo "Policy attached successfully to role: $NODE_ROLE" 