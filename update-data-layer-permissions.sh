#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Updating network policies to allow access to data-layer...${NC}"

# Create a NetworkPolicy allowing access from microservices namespace to data-layer namespace
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-microservices
  namespace: data-layer
spec:
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: microservices
  podSelector: {}
  policyTypes:
  - Ingress
EOF

# Label the microservices namespace
kubectl label namespace microservices name=microservices --overwrite

echo -e "${YELLOW}Granting service account permissions...${NC}"

# Create a ClusterRole with necessary permissions
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: data-layer-access
rules:
- apiGroups: [""]
  resources: ["services"]
  verbs: ["get", "list"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
EOF

# Create a ClusterRoleBinding for the service account
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: data-access-service-data-layer-access
subjects:
- kind: ServiceAccount
  name: data-access-service
  namespace: microservices
roleRef:
  kind: ClusterRole
  name: data-layer-access
  apiGroup: rbac.authorization.k8s.io
EOF

echo -e "${GREEN}Network policies and permissions updated successfully!${NC}"
echo -e "${YELLOW}Note: You may need to restart your deployments for changes to take effect.${NC}" 