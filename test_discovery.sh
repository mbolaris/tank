#!/bin/bash
# Test script for distributed server discovery
#
# This script demonstrates how to test the multi-server discovery infrastructure
# by running multiple servers and verifying they can discover each other.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Tank World Net - Discovery Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to wait for server to be ready
wait_for_server() {
    local port=$1
    local max_attempts=30
    local attempt=0

    echo -e "${YELLOW}Waiting for server on port $port to be ready...${NC}"

    while [ $attempt -lt $max_attempts ]; do
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Server on port $port is ready${NC}"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    echo -e "${YELLOW}⚠ Server on port $port did not respond in time${NC}"
    return 1
}

# Function to register server with another
register_server() {
    local target_port=$1
    local source_port=$2

    echo -e "${YELLOW}Registering server $source_port with server $target_port...${NC}"

    # Get source server info
    local server_info=$(curl -s "http://localhost:$source_port/api/servers/local")

    # Register with target
    local response=$(curl -s -X POST "http://localhost:$target_port/api/discovery/register" \
        -H "Content-Type: application/json" \
        -d "$server_info")

    echo -e "${GREEN}✓ Registration complete${NC}"
}

# Function to list servers
list_servers() {
    local port=$1
    echo -e "${BLUE}Servers registered on port $port:${NC}"
    curl -s "http://localhost:$port/api/discovery/servers" | python3 -m json.tool
    echo ""
}

# Check if we should start servers or just run tests
if [ "$1" = "test-only" ]; then
    echo -e "${YELLOW}Running tests on existing servers...${NC}"
    echo ""
else
    echo -e "${BLUE}Starting three server instances...${NC}"
    echo ""

    # Start Server 1 on port 8001
    echo -e "${YELLOW}Starting Server 1 on port 8001...${NC}"
    cd /home/user/tank
    PORT=8001 SERVER_ID=tank-server-1 nohup python3 -m backend.main > /tmp/tank-server-1.log 2>&1 &
    SERVER1_PID=$!
    echo "Server 1 PID: $SERVER1_PID"

    # Start Server 2 on port 8002
    echo -e "${YELLOW}Starting Server 2 on port 8002...${NC}"
    PORT=8002 SERVER_ID=tank-server-2 nohup python3 -m backend.main > /tmp/tank-server-2.log 2>&1 &
    SERVER2_PID=$!
    echo "Server 2 PID: $SERVER2_PID"

    # Start Server 3 on port 8003
    echo -e "${YELLOW}Starting Server 3 on port 8003...${NC}"
    PORT=8003 SERVER_ID=tank-server-3 nohup python3 -m backend.main > /tmp/tank-server-3.log 2>&1 &
    SERVER3_PID=$!
    echo "Server 3 PID: $SERVER3_PID"

    echo ""

    # Wait for servers to be ready
    wait_for_server 8001
    wait_for_server 8002
    wait_for_server 8003

    echo ""
fi

# Test discovery functionality
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing Server Discovery${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check initial state - each server should only see itself
echo -e "${BLUE}1. Initial state (each server sees only itself):${NC}"
list_servers 8001

# Register Server 2 with Server 1
echo -e "${BLUE}2. Registering Server 2 with Server 1...${NC}"
register_server 8001 8002
echo ""

# Check Server 1 now sees Server 2
echo -e "${BLUE}3. Server 1 should now see both servers:${NC}"
list_servers 8001

# Register Server 3 with Server 1
echo -e "${BLUE}4. Registering Server 3 with Server 1...${NC}"
register_server 8001 8003
echo ""

# Check Server 1 sees all three servers
echo -e "${BLUE}5. Server 1 should now see all three servers:${NC}"
list_servers 8001

# Test cross-registration (Server 1 registers with Server 2)
echo -e "${BLUE}6. Registering Server 1 with Server 2...${NC}"
register_server 8002 8001
echo ""

echo -e "${BLUE}7. Server 2 should now see Server 1 and itself:${NC}"
list_servers 8002

# Test the /api/servers endpoint (includes tanks)
echo -e "${BLUE}8. Getting all servers with tanks from Server 1:${NC}"
curl -s "http://localhost:8001/api/servers" | python3 -m json.tool | head -50
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Discovery test complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ "$1" != "test-only" ]; then
    echo -e "${YELLOW}Servers are still running in the background.${NC}"
    echo -e "${YELLOW}To stop them, run:${NC}"
    echo -e "  kill $SERVER1_PID $SERVER2_PID $SERVER3_PID"
    echo ""
    echo -e "${YELLOW}Or use: pkill -f 'python3 -m backend.main'${NC}"
    echo ""

    # Save PIDs to file for easy cleanup
    echo "$SERVER1_PID $SERVER2_PID $SERVER3_PID" > /tmp/tank-server-pids.txt
    echo -e "${YELLOW}PIDs saved to /tmp/tank-server-pids.txt${NC}"
fi
