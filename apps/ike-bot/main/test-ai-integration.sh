#!/bin/bash
# Test script for IkeBot AI Integration

echo "======================================================================"
echo "IkeBot AI Integration Test Script"
echo "======================================================================"
echo ""

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY not set"
    echo "   Set it with: export OPENAI_API_KEY=your_key_here"
    echo ""
fi

# Check if server is running
echo "1. Checking if IkeBot server is running..."
if curl -s http://localhost:3000/api/ai/status > /dev/null 2>&1; then
    echo "✅ Server is running"
else
    echo "❌ Server is not running"
    echo "   Start it with: npm run dev"
    exit 1
fi

echo ""
echo "2. Testing AI status endpoint..."
curl -s http://localhost:3000/api/ai/status | jq '.'

echo ""
echo "3. Testing beneficiary analysis..."
curl -s -X POST http://localhost:3000/api/ai/analyze-beneficiary \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-123",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "relationship": "Primary",
    "created_at": "2024-01-01T00:00:00Z",
    "credit_disputes": [],
    "billing_events": []
  }' | jq '.'

echo ""
echo "4. Testing dispute letter generation..."
curl -s -X POST http://localhost:3000/api/ai/generate-dispute-letter \
  -H "Content-Type: application/json" \
  -d '{
    "dispute": {
      "id": "dispute-123",
      "beneficiary_id": "test-123",
      "creditor_name": "Example Credit Corp",
      "dispute_reason": "This account does not belong to me",
      "dispute_type": "not_mine",
      "status": "pending"
    },
    "beneficiary": {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "phone": "555-0100"
    }
  }' | jq '.'

echo ""
echo "5. Testing personalized message generation..."
curl -s -X POST http://localhost:3000/api/ai/generate-message \
  -H "Content-Type: application/json" \
  -d '{
    "beneficiary": {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com"
    },
    "message_type": "welcome",
    "context": "New account setup"
  }' | jq '.'

echo ""
echo "======================================================================"
echo "Test completed!"
echo "======================================================================"
