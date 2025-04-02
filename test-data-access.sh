#!/bin/bash

# Base URL
BASE_URL="http://localhost:8080"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Function to print test results
print_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
    fi
}

echo "Testing Data Access Service..."

# Test health endpoint
echo -e "\nTesting health endpoint..."
curl -s "$BASE_URL/health" | grep -q "healthy"
print_result "Health check"

# Test listing EC2 assets
echo -e "\nTesting list EC2 assets..."
curl -s "$BASE_URL/assets/EC2" > /dev/null
print_result "List EC2 assets"

# Test creating an EC2 asset
echo -e "\nTesting create EC2 asset..."
curl -s -X POST "$BASE_URL/assets/EC2" \
    -H "Content-Type: application/json" \
    -d '{
        "UniqueId": "test-ec2-1",
        "IsStale": false,
        "Tags": {"Name": "test-instance"},
        "InstanceId": "i-1234567890abcdef0",
        "InstanceType": "t2.micro",
        "State": "running",
        "VpcId": "vpc-12345678",
        "SubnetId": "subnet-12345678"
    }' > /dev/null
print_result "Create EC2 asset"

# Test getting the created asset
echo -e "\nTesting get EC2 asset..."
curl -s "$BASE_URL/assets/EC2/test-ec2-1" > /dev/null
print_result "Get EC2 asset"

# Test updating the asset
echo -e "\nTesting update EC2 asset..."
curl -s -X PUT "$BASE_URL/assets/EC2/test-ec2-1" \
    -H "Content-Type: application/json" \
    -d '{
        "State": "stopped",
        "Tags": {"Name": "test-instance-updated"}
    }' > /dev/null
print_result "Update EC2 asset"

# Test marking asset as stale
echo -e "\nTesting mark asset as stale..."
curl -s -X POST "$BASE_URL/assets/EC2/stale" \
    -H "Content-Type: application/json" \
    -d '["test-ec2-1"]' > /dev/null
print_result "Mark asset as stale"

# Test deleting the asset
echo -e "\nTesting delete EC2 asset..."
curl -s -X DELETE "$BASE_URL/assets/EC2/test-ec2-1" > /dev/null
print_result "Delete EC2 asset"

echo -e "\nTesting complete!" 