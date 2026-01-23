# Discovery Hub Guide

## Overview

The Tank World distributed network uses a **central discovery hub** pattern for server registration and discovery. This eliminates the need for manual peer-to-peer registration between every server.

## Architecture

```
                ┌──────────────────────┐
                │   Discovery Hub      │
                │   (Any Tank Server)  │
                │   Port 8000          │
                └──────────────────────┘
                          ▲
                          │ Auto-register
                          │ Send heartbeats
                ┌─────────┼──────────┐
                │         │          │
        ┌───────▼──┐  ┌──▼──────┐  ┌▼─────────┐
        │ Worker 1 │  │ Worker 2│  │ Worker 3 │
        │ Port 8001│  │ Port 8002│  │ Port 8003│
        └──────────┘  └─────────┘  └──────────┘
```

### How It Works

1. **Hub Server**: One server acts as the discovery hub (can be any server, no special configuration)
2. **Worker Servers**: Other servers point to the hub via `DISCOVERY_SERVER_URL`
3. **Auto-Registration**: Workers automatically register with the hub on startup
4. **Heartbeats**: Workers send periodic heartbeats (every 30 seconds) to stay registered
5. **Discovery**: Any server can query the hub to find all other servers

## Setup Instructions

### Step 1: Start the Discovery Hub

The hub is just a regular Tank server. Choose one machine to be your hub:

```bash
# Machine 1: Discovery Hub
TANK_SERVER_ID=hub-server \
TANK_API_PORT=8000 \
python -m backend.main
```

**Important**: Make sure port 8000 is open in your firewall!

```bash
# Linux (iptables)
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT

# Linux (firewalld)
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload

# Windows
netsh advfirewall firewall add rule name="Tank Hub" dir=in action=allow protocol=TCP localport=8000
```

### Step 2: Start Worker Servers

On other machines, start Tank servers with `DISCOVERY_SERVER_URL` pointing to the hub:

```bash
# Machine 2: Worker Server 1
TANK_SERVER_ID=worker-1 \
TANK_API_PORT=8001 \
DISCOVERY_SERVER_URL=http://192.168.1.10:8000 \
python -m backend.main

# Machine 3: Worker Server 2
TANK_SERVER_ID=worker-2 \
TANK_API_PORT=8002 \
DISCOVERY_SERVER_URL=http://192.168.1.10:8000 \
python -m backend.main
```

**Replace `192.168.1.10`** with the actual IP address of your hub server!

### Step 3: Verify Registration

Check that all servers are registered with the hub:

```bash
# Query the hub for all registered servers
curl http://192.168.1.10:8000/api/discovery/servers | python3 -m json.tool
```

Expected output:
```json
{
  "servers": [
    {
      "server_id": "hub-server",
      "host": "192.168.1.10",
      "port": 8000,
      "status": "online",
      ...
    },
    {
      "server_id": "worker-1",
      "host": "192.168.1.20",
      "port": 8001,
      "status": "online",
      ...
    },
    {
      "server_id": "worker-2",
      "host": "192.168.1.30",
      "port": 8002,
      "status": "online",
      ...
    }
  ],
  "count": 3
}
```

## Configuration Reference

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `TANK_SERVER_ID` | Yes | Unique identifier for this server | `hub-server` or `worker-1` |
| `TANK_API_PORT` | No | Port for this server's API (default: 8000) | `8001` |
| `DISCOVERY_SERVER_URL` | No | URL of the discovery hub (omit for hub server) | `http://192.168.1.10:8000` |

### Firewall Requirements

**Hub Server:**
- Must accept incoming connections on its API port (default 8000)
- This port must be reachable from all worker servers

**Worker Servers:**
- Only need outbound access to reach the hub
- Incoming connections optional (unless you want direct cross-server migrations)

## Features

### Automatic Registration

Workers automatically register with the hub on startup. Look for this in the logs:

```
INFO:__main__:Registering with remote discovery hub...
INFO:__main__:Successfully registered with discovery hub at 192.168.1.10:8000
```

### Automatic Heartbeats

Workers send heartbeats every 30 seconds to maintain registration:

```
DEBUG:__main__:Heartbeat sent to remote discovery hub at 192.168.1.10:8000
```

### Network IP Detection

Servers automatically detect their network IP address (instead of using "localhost"). This enables cross-machine communication.

### Health Monitoring

The hub automatically marks servers as offline if they miss heartbeats:
- **Degraded**: No heartbeat for 60+ seconds
- **Offline**: No heartbeat for 90+ seconds

## Troubleshooting

### Workers Can't Register with Hub

**Symptom:**
```
WARNING:__main__:Failed to register with discovery hub at 192.168.1.10:8000
```

**Solutions:**
1. Check firewall: `curl http://192.168.1.10:8000/health`
2. Verify hub is running: Check hub server logs
3. Check DISCOVERY_SERVER_URL format: Must start with `http://`

### Servers Show "localhost" Instead of Real IP

This is normal in local testing. The network IP detection uses a socket connection to determine the actual network interface.

If you need to force a specific IP:
1. The system auto-detects network IP via `_get_network_ip()`
2. For containers/special networks, you may need to modify this function

### Heartbeats Failing

**Symptom:**
```
WARNING:__main__:Failed to send heartbeat to discovery hub
```

**Solutions:**
1. Check network connectivity: `ping 192.168.1.10`
2. Verify hub is still running
3. Check hub logs for errors

### Server Shows as Offline Despite Being Running

Wait 30-60 seconds for heartbeats to update the status. Servers are marked offline after 90 seconds without heartbeat.

## Testing

A test script is provided to verify the discovery hub pattern:

```bash
./scripts/test_discovery_hub.sh
```

This will:
1. Start a hub server on port 8000
2. Start 2 worker servers on ports 8001-8002
3. Verify automatic registration
4. Display all registered servers

## Comparison: Old vs New

### Old Manual Registration (Before)

```bash
# Start 3 servers
python -m backend.main --port 8000
python -m backend.main --port 8001
python -m backend.main --port 8002

# Manually register each server with every other server (9 API calls!)
curl -X POST http://localhost:8000/api/discovery/register -d "$(curl http://localhost:8001/api/servers/local)"
curl -X POST http://localhost:8000/api/discovery/register -d "$(curl http://localhost:8002/api/servers/local)"
curl -X POST http://localhost:8001/api/discovery/register -d "$(curl http://localhost:8000/api/servers/local)"
# ... 6 more calls ...
```

### New Hub Pattern (After)

```bash
# Start hub
TANK_SERVER_ID=hub python -m backend.main

# Start workers (auto-register!)
TANK_SERVER_ID=w1 TANK_API_PORT=8001 DISCOVERY_SERVER_URL=http://localhost:8000 python -m backend.main
TANK_SERVER_ID=w2 TANK_API_PORT=8002 DISCOVERY_SERVER_URL=http://localhost:8000 python -m backend.main

# Done! All servers registered automatically.
```

## Advanced Usage

### Multiple Hubs (High Availability)

For production, you can run multiple hub servers with a load balancer in front:

```bash
# Hub 1
TANK_SERVER_ID=hub-1 TANK_API_PORT=8000 python -m backend.main

# Hub 2 (also points to Hub 1 to sync)
TANK_SERVER_ID=hub-2 TANK_API_PORT=8000 DISCOVERY_SERVER_URL=http://hub-1:8000 python -m backend.main

# Workers point to load balancer
DISCOVERY_SERVER_URL=http://load-balancer:8000 python -m backend.main
```

### Docker Compose Example

```yaml
version: '3.8'

services:
  hub:
    build: .
    environment:
      - TANK_SERVER_ID=hub-server
      - TANK_API_PORT=8000
    ports:
      - "8000:8000"
    networks:
      - tank-network

  worker1:
    build: .
    environment:
      - TANK_SERVER_ID=worker-1
      - TANK_API_PORT=8001
      - DISCOVERY_SERVER_URL=http://hub:8000
    depends_on:
      - hub
    networks:
      - tank-network

  worker2:
    build: .
    environment:
      - TANK_SERVER_ID=worker-2
      - TANK_API_PORT=8002
      - DISCOVERY_SERVER_URL=http://hub:8000
    depends_on:
      - hub
    networks:
      - tank-network

networks:
  tank-network:
    driver: bridge
```

### Kubernetes Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tank-hub
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: tank
        image: tank-world:latest
        env:
        - name: TANK_SERVER_ID
          value: "hub-server"
        - name: TANK_API_PORT
          value: "8000"
        ports:
        - containerPort: 8000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tank-workers
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: tank
        image: tank-world:latest
        env:
        - name: TANK_SERVER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: TANK_API_PORT
          value: "8000"
        - name: DISCOVERY_SERVER_URL
          value: "http://tank-hub:8000"
```

## API Reference

### Hub Endpoints

The discovery hub provides these endpoints:

- `POST /api/discovery/register` - Register a server
- `POST /api/discovery/heartbeat/{server_id}` - Send heartbeat
- `GET /api/discovery/servers` - List all registered servers
- `DELETE /api/discovery/unregister/{server_id}` - Unregister a server

### Health Check

- `GET /health` - Check if server is running

## Next Steps

After setting up discovery:
1. ✅ Servers can discover each other automatically
2. ✅ Health monitoring via heartbeats
3. ⏭️ Create cross-server tank connections for entity migration
4. ⏭️ Test entity migration between servers

See `TESTING_DISTRIBUTED_SERVERS.md` for cross-server migration setup.
