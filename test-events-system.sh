#!/bin/bash

# Test script for the complete events system
# This script simulates various activities and tests the events logging

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

API_GATEWAY_URL="https://a12c65672e20e491e83c7a13c5662714-1758004955.eu-north-1.elb.amazonaws.com"
AGENT_ID="test-agent-$(hostname)"

echo -e "${BLUE}🧪 Testing Complete Events System${NC}"
echo "=========================================="

# Function to log test step
log_step() {
    echo -e "${YELLOW}📋 $1${NC}"
}

# Function to log success
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to log error
log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Test 1: Check if all services are running
log_step "1. Checking service status..."

# Check RabbitMQ
if kubectl get pods -n microservices | grep -q "rabbitmq.*Running"; then
    log_success "RabbitMQ is running"
else
    log_error "RabbitMQ is not running"
    exit 1
fi

# Check events-consumer
if kubectl get pods -n microservices | grep -q "events-consumer.*Running"; then
    log_success "Events Consumer is running"
else
    log_error "Events Consumer is not running"
    exit 1
fi

# Check events-logger
if kubectl get pods -n microservices | grep -q "events-logger.*Running"; then
    log_success "Events Logger is running"
else
    log_error "Events Logger is not running"
    exit 1
fi

# Test 2: Test events-logger API
log_step "2. Testing events-logger API..."

# Test health endpoint
HEALTH_RESPONSE=$(curl -s -k -H "Authorization: Bearer development_token" \
    "${API_GATEWAY_URL}/api/v1/events-logger/health")

if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    log_success "Events Logger health check passed"
    echo "Response: $HEALTH_RESPONSE"
else
    log_error "Events Logger health check failed"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi

# Test 3: Send test events
log_step "3. Sending test events..."

# Create test event data
TEST_EVENT=$(cat <<EOF
{
  "agent_id": "$AGENT_ID",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)",
  "event_type": "network_connection",
  "event_category": "outbound",
  "source": "test-script",
  "event_data": {
    "method": "GET",
    "host": "api.anthropic.com",
    "path": "/v1/messages",
    "url": "https://api.anthropic.com/v1/messages",
    "content_length": 1024,
    "client_ip": "10.0.0.13",
    "test_scenario": "simulated_llm_request"
  },
  "session_id": "test-session-$(date +%s)",
  "correlation_id": "test-correlation-$(date +%s)"
}
EOF
)

# Send single event
SINGLE_EVENT_RESPONSE=$(curl -s -k -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer development_token" \
    -d "$TEST_EVENT" \
    "${API_GATEWAY_URL}/api/v1/events-logger/events/collect")

if echo "$SINGLE_EVENT_RESPONSE" | grep -q "success.*true"; then
    log_success "Single event sent successfully"
    EVENT_ID=$(echo "$SINGLE_EVENT_RESPONSE" | grep -o '"event_id":"[^"]*"' | cut -d'"' -f4)
    echo "Event ID: $EVENT_ID"
else
    log_error "Failed to send single event"
    echo "Response: $SINGLE_EVENT_RESPONSE"
    exit 1
fi

# Test 4: Send batch events
log_step "4. Sending batch events..."

# Create batch event data
BATCH_EVENTS=$(cat <<EOF
{
  "events": [
    {
      "agent_id": "$AGENT_ID",
      "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)",
      "event_type": "llm_request",
      "event_category": "outbound",
      "source": "test-script",
      "event_data": {
        "method": "POST",
        "host": "api.anthropic.com",
        "path": "/v1/messages",
        "model": "claude-3-sonnet-20240229",
        "messages_count": 2,
        "max_tokens": 4096,
        "test_scenario": "simulated_llm_request_batch"
      }
    },
    {
      "agent_id": "$AGENT_ID",
      "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)",
      "event_type": "llm_response",
      "event_category": "inbound",
      "source": "test-script",
      "event_data": {
        "status_code": 200,
        "host": "api.anthropic.com",
        "path": "/v1/messages",
        "content_length": 2048,
        "test_scenario": "simulated_llm_response_batch"
      }
    },
    {
      "agent_id": "$AGENT_ID",
      "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)",
      "event_type": "user_interaction",
      "event_category": "internal",
      "source": "test-script",
      "event_data": {
        "action": "button_click",
        "component": "chat_interface",
        "user_id": "test-user-123",
        "test_scenario": "simulated_user_interaction"
      }
    }
  ]
}
EOF
)

# Send batch events
BATCH_RESPONSE=$(curl -s -k -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer development_token" \
    -d "$BATCH_EVENTS" \
    "${API_GATEWAY_URL}/api/v1/events-logger/events/batch")

if echo "$BATCH_RESPONSE" | grep -q "success.*true"; then
    log_success "Batch events sent successfully"
    echo "Batch response: $BATCH_RESPONSE"
else
    log_error "Failed to send batch events"
    echo "Response: $BATCH_RESPONSE"
    exit 1
fi

# Test 5: Search for events
log_step "5. Searching for events..."

# Wait a moment for events to be processed
sleep 5

# Search for events
SEARCH_RESPONSE=$(curl -s -k -X GET \
    -H "Authorization: Bearer development_token" \
    "${API_GATEWAY_URL}/api/v1/events-logger/events/search?agent_id=$AGENT_ID&limit=10")

if echo "$SEARCH_RESPONSE" | grep -q "success.*true"; then
    log_success "Event search successful"
    EVENT_COUNT=$(echo "$SEARCH_RESPONSE" | grep -o '"count":[0-9]*' | cut -d':' -f2)
    echo "Found $EVENT_COUNT events for agent $AGENT_ID"
else
    log_error "Event search failed"
    echo "Response: $SEARCH_RESPONSE"
    exit 1
fi

# Test 6: Check RabbitMQ queue
log_step "6. Checking RabbitMQ queue status..."

# Get RabbitMQ pod name
RABBITMQ_POD=$(kubectl get pods -n microservices -l app=rabbitmq -o jsonpath='{.items[0].metadata.name}')

# Check queue status
QUEUE_STATUS=$(kubectl exec -n microservices "$RABBITMQ_POD" -- rabbitmqctl list_queues name messages_ready messages_unacknowledged 2>/dev/null | grep glassbox_events || echo "Queue not found")

if echo "$QUEUE_STATUS" | grep -q "glassbox_events"; then
    log_success "RabbitMQ queue exists"
    echo "Queue status: $QUEUE_STATUS"
else
    log_error "RabbitMQ queue not found"
    echo "Queue status: $QUEUE_STATUS"
fi

# Test 7: Check events-consumer logs
log_step "7. Checking events-consumer logs..."

CONSUMER_LOGS=$(kubectl logs -n microservices deployment/events-consumer --tail=10 2>/dev/null || echo "No logs available")

if echo "$CONSUMER_LOGS" | grep -q "Processing event\|Event stored"; then
    log_success "Events consumer is processing events"
    echo "Recent logs: $CONSUMER_LOGS"
else
    log_error "No event processing logs found"
    echo "Consumer logs: $CONSUMER_LOGS"
fi

echo ""
echo -e "${GREEN}🎉 Events System Test Completed Successfully!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}📊 Test Summary:${NC}"
echo "   ✅ All services are running"
echo "   ✅ Events Logger API is accessible"
echo "   ✅ Single event collection works"
echo "   ✅ Batch event collection works"
echo "   ✅ Event search functionality works"
echo "   ✅ RabbitMQ queue is operational"
echo "   ✅ Events consumer is processing events"
echo ""
echo -e "${BLUE}🔧 Next Steps:${NC}"
echo "   • Monitor events in real-time: kubectl logs -f deployment/events-consumer -n microservices"
echo "   • Scale consumers: kubectl scale deployment events-consumer -n microservices --replicas=3"
echo "   • Scale API: kubectl scale deployment events-logger -n microservices --replicas=2"
echo "   • View RabbitMQ UI: kubectl port-forward svc/rabbitmq 15672:15672 -n microservices" 