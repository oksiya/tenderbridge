#!/bin/bash
# deploy_and_start.sh - Automated deployment script for TenderBridge

set -e  # Exit on error

echo "🚀 TenderBridge Deployment Script"
echo "=================================="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded environment variables from .env"
else
    echo "❌ .env file not found! Copy .env.example to .env first."
    exit 1
fi

# Start services
echo "📦 Starting containers..."
podman-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if Ganache is running
echo "🔍 Checking Ganache..."
if podman exec tenderbridge_ganache_1 echo "OK" &>/dev/null; then
    echo "✅ Ganache is running"
else
    echo "❌ Ganache is not running"
    exit 1
fi

# Deploy smart contract
echo "📝 Deploying Stamp contract..."
podman exec tenderbridge_api_1 python3 /code/app/blockchain/deploy.py

# Read the deployed contract address
CONTRACT_ADDRESS=$(cat app/blockchain/contracts/StampAddress.txt)
echo "✅ Contract deployed at: $CONTRACT_ADDRESS"

# Update .env file with new contract address
if [ ! -z "$CONTRACT_ADDRESS" ]; then
    # Update or add STAMP_CONTRACT_ADDRESS
    if grep -q "^STAMP_CONTRACT_ADDRESS=" .env; then
        sed -i "s|^STAMP_CONTRACT_ADDRESS=.*|STAMP_CONTRACT_ADDRESS=$CONTRACT_ADDRESS|" .env
    else
        echo "STAMP_CONTRACT_ADDRESS=$CONTRACT_ADDRESS" >> .env
    fi
    echo "✅ Updated .env with new contract address"
fi

# Restart services to pick up new contract address
echo "🔄 Restarting services with new contract address..."
podman-compose restart api worker

echo ""
echo "✅ Deployment complete!"
echo "=================================="
echo "Contract Address: $CONTRACT_ADDRESS"
echo "API: http://localhost:8000"
echo "Swagger UI: http://localhost:8000/docs"
echo ""
echo "To verify blockchain integration:"
echo "  1. Create account: curl -X POST http://localhost:8000/auth/register ..."
echo "  2. Login and get token"
echo "  3. Upload tender with token"
echo "  4. Verify on blockchain"
