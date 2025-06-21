#!/bin/bash
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd "$SCRIPT_DIR"

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Complete Events System${NC}"
echo "=========================================="

# Deploy in order: RabbitMQ → events-consumer → events-logger
echo -e "${YELLOW}1. Deploying RabbitMQ (infrastructure)...${NC}"
./deploy-rabbitmq.sh

echo -e "${YELLOW}2. Deploying Events Consumer (3 replicas)...${NC}"
./deploy-events-consumer.sh

echo -e "${YELLOW}3. Deploying Events Logger (2 replicas)...${NC}"
./deploy-events-logger.sh

echo ""
echo -e "${GREEN}🎉 Complete Events System Deployed!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}📊 Current Deployment Status:${NC}"
echo "   • RabbitMQ: 1 broker (infrastructure)"
echo "   • Events Consumer: 3 consumers (scalable)"
echo "   • Events Logger: 2 API pods (scalable)"
echo ""
echo -e "${BLUE}🔧 Scaling Commands:${NC}"
echo "   • Scale consumers: kubectl scale deployment events-consumer -n microservices --replicas=5"
echo "   • Scale API: kubectl scale deployment events-logger -n microservices --replicas=3"
echo "   • Scale RabbitMQ: kubectl scale deployment rabbitmq -n microservices --replicas=3"
echo ""
echo -e "${BLUE}📈 Monitoring:${NC}"
echo "   • RabbitMQ UI: kubectl port-forward svc/rabbitmq 15672:15672 -n microservices"
echo "   • Pod status: kubectl get pods -n microservices | grep -E '(rabbitmq|events)'"
echo "   • Logs: kubectl logs -f deployment/events-consumer -n microservices" 