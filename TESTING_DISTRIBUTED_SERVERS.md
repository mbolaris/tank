# Testing Distributed Server Discovery

This guide explains how to test the distributed server discovery and communication infrastructure.

## Quick Start - Manual Testing

### Step 1: Start Server 1 (Port 8001)

```bash
cd /home/user/tank
TANK_SERVER_ID=tank-server-1 TANK_API_PORT=8001 python -m backend.main
```

In a new terminal...

### Step 2: Start Server 2 (Port 8002)

```bash
cd /home/user/tank
TANK_SERVER_ID=tank-server-2 TANK_API_PORT=8002 python -m backend.main
```

In a new terminal...

### Step 3: Start Server 3 (Port 8003)

```bash
cd /home/user/tank
TANK_SERVER_ID=tank-server-3 TANK_API_PORT=8003 python -m backend.main
```

### Step 4: Test Discovery

In a new terminal, test the discovery service:

```bash
# Check Server 1's registered servers (should only see itself initially)
curl http://localhost:8001/api/discovery/servers | python -m json.tool

# Register Server 2 with Server 1
SERVER2_INFO=$(curl -s http://localhost:8002/api/servers/local)
curl -X POST http://localhost:8001/api/discovery/register \
  -H "Content-Type: application/json" \
  -d "$SERVER2_INFO"

# Check Server 1 again (should now see both servers)
curl http://localhost:8001/api/discovery/servers | python -m json.tool

# Register Server 3 with Server 1
SERVER3_INFO=$(curl -s http://localhost:8003/api/servers/local)
curl -X POST http://localhost:8001/api/discovery/register \
  -H "Content-Type: application/json" \
  -d "$SERVER3_INFO"

# Check Server 1 again (should now see all three servers)
curl http://localhost:8001/api/discovery/servers | python -m json.tool

# View all servers with their tanks
curl http://localhost:8001/api/servers | python -m json.tool
```

## Automated Testing

Run the automated test script:

```bash
cd /home/user/tank
./test_discovery.sh
```

This will:
1. Start three server instances on ports 8001, 8002, 8003
2. Register servers with each other
3. Verify discovery is working
4. Show all servers and their tanks

To stop the test servers:

```bash
pkill -f "python.*backend.main"
```

## What to Look For

### 1. Server Registration
✅ Servers should appear in `/api/discovery/servers` after registration
✅ Each server should have status "online"
✅ Server metadata (CPU, memory, platform) should be populated

### 2. Heartbeat Monitoring
✅ Servers send heartbeats every 30 seconds
✅ Servers marked "offline" after 90 seconds without heartbeat
✅ Check logs for: "Heartbeat sent to discovery service"

### 3. Tank Visibility
✅ `/api/servers` endpoint shows all registered servers
✅ Each server includes its list of tanks
✅ Can query tanks on remote servers via discovery

### 4. Health Status
✅ Servers automatically detect when others go offline
✅ Status changes logged: "Server X status changed to offline"
✅ Stopping a server should show it as offline within ~90 seconds

## Testing Cross-Server Tank Queries

Once servers are registered:

```bash
# List all tanks across all servers (from Server 1's perspective)
curl http://localhost:8001/api/servers | python -m json.tool

# Get a specific server's info (Server 2 via Server 1)
curl http://localhost:8001/api/servers/tank-server-2 | python -m json.tool

# Create a tank on Server 2
curl -X POST http://localhost:8002/api/tanks \
  -H "Content-Type: application/json" \
  -d '{"name": "Remote Tank", "description": "A tank on server 2"}'

# Query Server 1 to see Server 2's tanks
curl http://localhost:8001/api/servers/tank-server-2 | python -m json.tool
```

## Data Directories

Each server stores its data in:
- Default: `/home/user/tank/data/`
- Server registry: `data/server_registry.json`
- Transfer logs: `data/transfers.log`

For isolated testing, you can set `TANK_DATA_DIR`:

```bash
TANK_SERVER_ID=test-server TANK_API_PORT=9000 TANK_DATA_DIR=/tmp/tank-test python -m backend.main
```

## Troubleshooting

### Servers can't see each other
- Verify registration: `curl http://localhost:8001/api/discovery/servers`
- Check server logs for "Server registered" messages
- Ensure SERVER_ID is unique per server

### Heartbeats not working
- Check logs for "Heartbeat sent to discovery service"
- Verify discovery service started: Look for "DiscoveryService cleanup loop started"
- Default heartbeat interval is 30 seconds

### Port conflicts
- Use different ports: `TANK_API_PORT=8001`, `TANK_API_PORT=8002`, etc.
- Check running servers: `lsof -i :8000`

## Next Steps

After verifying discovery works:
1. ✅ Servers can register with each other
2. ✅ Servers can query each other's tanks
3. ⏭️ Implement cross-server entity migration (Phase 2)
4. ⏭️ Test entity migration between servers
