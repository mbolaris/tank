# Distributed Tank World Net Architecture

## Table of Contents
1. [Current Architecture](#current-architecture)
2. [Target Distributed Architecture](#target-distributed-architecture)
3. [Implementation Roadmap](#implementation-roadmap)
4. [Technical Requirements](#technical-requirements)
5. [API Contracts](#api-contracts)
6. [Data Consistency](#data-consistency)
7. [Testing Strategy](#testing-strategy)

---

## Current Architecture

### Single-Server Design (v1.0 - Current)

```
┌─────────────────────────────────────────────────────┐
│         FastAPI Server (local-server)               │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │          TankRegistry                        │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐          │  │
│  │  │ Tank A │ │ Tank B │ │ Tank C │          │  │
│  │  │ (15 🐟)│ │ (8 🐟) │ │ (0 🐟) │          │  │
│  │  └────────┘ └────────┘ └────────┘          │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Storage: /data/tanks/{tank_id}/snapshots/         │
│  WebSocket: Per-tank broadcast tasks               │
│  API: REST endpoints for CRUD operations           │
└─────────────────────────────────────────────────────┘
```

**Characteristics:**
- ✅ All tanks run in single Python process
- ✅ In-memory TankRegistry (Dict[str, SimulationManager])
- ✅ File-based persistence (JSON snapshots)
- ✅ WebSocket broadcasts per tank (asyncio tasks)
- ✅ Server-aware data model (server_id tracked)
- ❌ Cannot scale horizontally
- ❌ Single point of failure
- ❌ Limited by single-machine resources

**What's Already in Place:**
- `ServerInfo` model with metadata
- `server_id` tracked in TankInfo
- Server selection UI in NetworkDashboard
- `/api/servers` endpoints
- Validation of server_id in create_tank

---

## Target Distributed Architecture

### Multi-Server Design (v2.0 - Target)

```
                    ┌──────────────────────────────┐
                    │   Discovery Service          │
                    │  - Server Registry           │
                    │  - Health Checks             │
                    │  - Load Balancing            │
                    └──────────────────────────────┘
                              ▲  ▲  ▲
                    ┌─────────┘  │  └─────────┐
                    │            │            │
            ┌───────▼────┐ ┌────▼─────┐ ┌───▼──────┐
            │ Server 1   │ │ Server 2 │ │ Server 3 │
            │ us-east-1  │ │ us-west-2│ │ eu-west-1│
            ├────────────┤ ├──────────┤ ├──────────┤
            │ Tank A, B  │ │ Tank C   │ │ (idle)   │
            │ 23 fish    │ │ 45 fish  │ │ 0 fish   │
            └────────────┘ └──────────┘ └──────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                    ┌──────────────────────────────┐
                    │   Shared State Store         │
                    │  - PostgreSQL (metadata)     │
                    │  - Redis (real-time state)   │
                    │  - S3 (snapshot backups)     │
                    └──────────────────────────────┘
```

**Characteristics:**
- ✅ Horizontal scaling (add more servers)
- ✅ Geographic distribution (latency optimization)
- ✅ High availability (failover)
- ✅ Load balancing (distribute tanks across servers)
- ✅ Cross-server entity transfers
- ✅ Centralized metadata store

---

## Implementation Roadmap

### Phase 1: Multi-Server Local Testing (1-2 weeks)

**Goal:** Run multiple backend instances on the same machine, test discovery.

#### 1.1 Create Discovery Service
**Location:** `backend/discovery_service.py`

```python
class DiscoveryService:
    """Central registry for Tank World Net servers."""

    def __init__(self):
        self.servers: Dict[str, ServerRegistration] = {}
        self.last_heartbeat: Dict[str, float] = {}

    def register_server(self, server_info: ServerInfo) -> bool:
        """Register a new server or update existing."""
        pass

    def deregister_server(self, server_id: str) -> bool:
        """Remove a server from the registry."""
        pass

    def get_servers(self, status: str = "online") -> List[ServerInfo]:
        """Get all servers matching status."""
        pass

    def heartbeat(self, server_id: str) -> bool:
        """Update server last-seen timestamp."""
        pass

    def check_health(self) -> None:
        """Mark servers offline if heartbeat expired (>30s)."""
        pass
```

**API Endpoints:**
```
POST   /discovery/register      # Register server
DELETE /discovery/{server_id}   # Deregister server
POST   /discovery/{server_id}/heartbeat  # Send heartbeat
GET    /discovery/servers        # List all servers
```

#### 1.2 Update Backend Server to Self-Register
**Location:** `backend/main.py`

```python
# On startup
async def register_with_discovery():
    """Register this server with discovery service."""
    server_info = get_server_info()
    response = await httpx.post(
        f"{DISCOVERY_URL}/discovery/register",
        json=server_info.model_dump()
    )
    # Start heartbeat task
    asyncio.create_task(send_heartbeats())

async def send_heartbeats():
    """Send periodic heartbeats to discovery service."""
    while True:
        await httpx.post(f"{DISCOVERY_URL}/discovery/{SERVER_ID}/heartbeat")
        await asyncio.sleep(10)  # Every 10 seconds
```

#### 1.3 Test Multi-Server Locally
```bash
# Terminal 1: Discovery Service
cd backend
python -m discovery_service --port 9000

# Terminal 2: Server 1
python -m main --port 8000 --server-id server-1 --discovery http://localhost:9000

# Terminal 3: Server 2
python -m main --port 8001 --server-id server-2 --discovery http://localhost:9000

# Terminal 4: Frontend
cd frontend && npm run dev
```

**Expected Result:**
- NetworkDashboard shows 2 servers
- Can create tanks on either server
- Each server reports independently

---

### Phase 2: Cross-Server Communication (2-3 weeks)

**Goal:** Enable viewing tanks on remote servers, cross-server transfers.

#### 2.1 API Gateway / Proxy
**Location:** `backend/gateway.py`

```python
class TankWorldGateway:
    """Routes requests to appropriate server."""

    def __init__(self, discovery_service: DiscoveryService):
        self.discovery = discovery_service

    async def get_tank(self, tank_id: str) -> TankStatus:
        """Get tank from any server in the network."""
        # 1. Query metadata store for tank location
        server_id = await self.get_tank_server(tank_id)

        # 2. Get server info from discovery
        server = self.discovery.get_server(server_id)

        # 3. Proxy request to target server
        response = await httpx.get(f"{server.host}:{server.port}/api/tanks/{tank_id}")
        return response.json()

    async def transfer_entity(
        self,
        entity_id: int,
        source_tank_id: str,
        dest_tank_id: str
    ) -> TransferResult:
        """Transfer entity across servers."""
        # 1. Get source and destination servers
        source_server = await self.get_tank_server(source_tank_id)
        dest_server = await self.get_tank_server(dest_tank_id)

        # 2. Serialize entity from source
        entity_data = await self.serialize_from_source(source_server, source_tank_id, entity_id)

        # 3. Transfer to destination
        result = await self.deserialize_to_dest(dest_server, dest_tank_id, entity_data)

        # 4. Remove from source if successful
        if result.success:
            await self.remove_from_source(source_server, source_tank_id, entity_id)

        return result
```

#### 2.2 Metadata Store (Tank → Server Mapping)
**Location:** `backend/metadata_store.py`

```python
class MetadataStore:
    """Persistent mapping of tanks to servers."""

    def __init__(self, db_url: str):
        # Use PostgreSQL or Redis
        self.db = create_engine(db_url)

    async def register_tank(self, tank_id: str, server_id: str) -> None:
        """Record which server hosts a tank."""
        await self.db.execute(
            "INSERT INTO tank_locations (tank_id, server_id, created_at) VALUES ($1, $2, NOW())",
            tank_id, server_id
        )

    async def get_tank_server(self, tank_id: str) -> Optional[str]:
        """Find which server hosts a tank."""
        result = await self.db.fetch_one(
            "SELECT server_id FROM tank_locations WHERE tank_id = $1",
            tank_id
        )
        return result['server_id'] if result else None

    async def migrate_tank(self, tank_id: str, new_server_id: str) -> None:
        """Update tank location (for migrations)."""
        await self.db.execute(
            "UPDATE tank_locations SET server_id = $1, migrated_at = NOW() WHERE tank_id = $2",
            new_server_id, tank_id
        )
```

**Database Schema:**
```sql
CREATE TABLE tank_locations (
    tank_id UUID PRIMARY KEY,
    server_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    migrated_at TIMESTAMP NULL,
    INDEX idx_server_id (server_id)
);

CREATE TABLE servers (
    server_id VARCHAR(255) PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INT NOT NULL,
    status VARCHAR(50) NOT NULL,
    last_heartbeat TIMESTAMP NOT NULL,
    registered_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### 2.3 WebSocket Federation
**Challenge:** Cross-server WebSocket connections

**Option A: Client Direct Connection**
```typescript
// Frontend connects directly to tank's server
const tankServer = await fetch(`/api/tanks/${tankId}/server`).json();
const ws = new WebSocket(`ws://${tankServer.host}:${tankServer.port}/ws/${tankId}`);
```

**Option B: WebSocket Proxy**
```python
# Gateway proxies WebSocket messages
async def websocket_proxy(websocket: WebSocket, tank_id: str):
    server = await metadata_store.get_tank_server(tank_id)
    remote_ws = await connect_websocket(f"{server.host}/ws/{tank_id}")

    # Bidirectional proxy
    async for message in remote_ws:
        await websocket.send_text(message)
```

---

### Phase 3: Production Hardening (3-4 weeks)

#### 3.1 Replace File Storage with PostgreSQL

**Current:**
```
/data/tanks/{tank_id}/snapshots/snapshot_20251124.json
```

**Target:**
```sql
CREATE TABLE tank_snapshots (
    snapshot_id UUID PRIMARY KEY,
    tank_id UUID NOT NULL,
    server_id VARCHAR(255) NOT NULL,
    frame INT NOT NULL,
    snapshot_data JSONB NOT NULL,  -- Full state
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    INDEX idx_tank_id (tank_id),
    INDEX idx_created_at (created_at DESC)
);

-- Optional: Separate table for entities
CREATE TABLE snapshot_entities (
    entity_id BIGSERIAL PRIMARY KEY,
    snapshot_id UUID REFERENCES tank_snapshots(snapshot_id),
    entity_type VARCHAR(50) NOT NULL,
    entity_data JSONB NOT NULL
);
```

**Benefits:**
- Querying capabilities (find tanks with specific properties)
- Atomic snapshots across distributed system
- Better backup/restore
- Compression (JSONB storage is efficient)

#### 3.2 Add Authentication & Authorization

```python
# JWT-based auth
class AuthMiddleware:
    def __init__(self, app, jwt_secret: str):
        self.app = app
        self.secret = jwt_secret

    async def __call__(self, scope, receive, send):
        # Extract token from Authorization header
        token = get_token_from_header(scope)

        # Verify JWT
        user = verify_jwt(token, self.secret)

        # Check permissions
        if not can_access_tank(user, tank_id):
            return JSONResponse({"error": "Forbidden"}, status_code=403)

        await self.app(scope, receive, send)
```

**Permissions Model:**
```sql
CREATE TABLE tank_permissions (
    tank_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    permission VARCHAR(50) NOT NULL,  -- 'read', 'write', 'admin'
    granted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tank_id, user_id, permission)
);
```

#### 3.3 Load Balancing & Health Checks

```python
class LoadBalancer:
    """Distribute tank creation across servers."""

    def select_server_for_new_tank(self) -> str:
        """Choose least-loaded server."""
        servers = discovery_service.get_servers(status="online")

        # Strategy 1: Least tanks
        return min(servers, key=lambda s: s.tank_count).server_id

        # Strategy 2: Least CPU/memory usage
        return min(servers, key=lambda s: (s.cpu_percent or 100)).server_id

        # Strategy 3: Geographic (if user location known)
        return self.nearest_server(user_location, servers)
```

#### 3.4 Monitoring & Observability

**Metrics to Track:**
- Server health (CPU, memory, disk, network)
- Tank counts per server
- WebSocket connection counts
- API request latency (p50, p95, p99)
- Entity transfer success/failure rates
- Snapshot save/restore times

**Tools:**
- Prometheus + Grafana (metrics)
- ELK Stack (logs)
- Jaeger (distributed tracing)
- Sentry (error tracking)

---

## Technical Requirements

### Infrastructure

#### Development Environment
- Python 3.10+
- PostgreSQL 15+ or Redis 7+
- Docker & Docker Compose (for local multi-server)
- Node.js 18+ (frontend)

#### Production Environment
- Kubernetes cluster (GKE, EKS, or AKS)
- Load balancer (nginx, HAProxy, or cloud LB)
- PostgreSQL cluster (RDS, Cloud SQL, or self-hosted)
- Redis cluster (ElastiCache, Cloud Memorystore, or self-hosted)
- S3-compatible storage (for snapshot backups)

### Dependencies to Add

**Backend:**
```txt
# Discovery & Service Mesh
httpx>=0.24.0          # Async HTTP client
consul-python>=1.1.0   # Service discovery (alternative to custom)

# Database
asyncpg>=0.28.0        # PostgreSQL async driver
redis>=4.5.0           # Redis client
sqlalchemy>=2.0.0      # ORM

# Monitoring
prometheus-client>=0.17.0
opentelemetry-api>=1.20.0

# Load Balancing
consistent-hash>=1.1   # For consistent hashing
```

**Frontend:**
```json
{
  "dependencies": {
    "socket.io-client": "^4.5.0"  // Better WebSocket management
  }
}
```

---

## API Contracts

### Discovery Service API

#### Register Server
```http
POST /discovery/register
Content-Type: application/json

{
  "server_id": "server-us-east-1-001",
  "hostname": "tank-server-1",
  "host": "10.0.1.5",
  "port": 8000,
  "status": "online",
  "tank_count": 0,
  "version": "2.0.0",
  "capabilities": ["entity-transfer", "poker-games"],
  "region": "us-east-1",
  "zone": "us-east-1a"
}

Response 201:
{
  "registered": true,
  "server_id": "server-us-east-1-001",
  "heartbeat_interval": 10,
  "heartbeat_timeout": 30
}
```

#### Heartbeat
```http
POST /discovery/{server_id}/heartbeat
Content-Type: application/json

{
  "tank_count": 5,
  "cpu_percent": 45.2,
  "memory_mb": 2048,
  "active_connections": 23
}

Response 200:
{
  "acknowledged": true,
  "ttl": 30
}
```

### Gateway API

#### Get Tank (Cross-Server)
```http
GET /gateway/tanks/{tank_id}
Authorization: Bearer <jwt_token>

Response 200:
{
  "tank": { ... },
  "server": {
    "server_id": "server-us-west-2-003",
    "host": "10.0.2.8",
    "port": 8000
  },
  "websocket_url": "ws://10.0.2.8:8000/ws/{tank_id}"
}
```

#### Transfer Entity (Cross-Server)
```http
POST /gateway/transfer
Content-Type: application/json

{
  "source_tank_id": "tank-abc-123",
  "dest_tank_id": "tank-def-456",
  "entity_id": 42,
  "entity_type": "fish"
}

Response 200:
{
  "success": true,
  "transfer_id": "xfer-789",
  "old_id": 42,
  "new_id": 105,
  "source_server": "server-1",
  "dest_server": "server-2",
  "timestamp": "2025-11-24T12:34:56Z"
}
```

---

## Data Consistency

### Challenge: Distributed State

When tanks run on different servers:
- How do we ensure snapshot consistency?
- What if server crashes during entity transfer?
- How do we handle network partitions?

### Solutions

#### 1. Two-Phase Commit (Entity Transfers)
```python
async def transfer_entity_2pc(source, dest, entity):
    # Phase 1: Prepare
    source_prepared = await source.prepare_transfer(entity)
    dest_prepared = await dest.prepare_receive(entity)

    if not (source_prepared and dest_prepared):
        # Rollback
        await source.abort_transfer(entity)
        await dest.abort_receive(entity)
        return False

    # Phase 2: Commit
    await dest.commit_receive(entity)
    await source.commit_transfer(entity)
    return True
```

#### 2. Idempotency (Retry Safety)
```python
@dataclass
class TransferOperation:
    transfer_id: str  # UUID
    source_tank: str
    dest_tank: str
    entity_id: int
    idempotency_key: str  # Client-generated

# Store in database with unique constraint on idempotency_key
# If retried, return same result without re-executing
```

#### 3. Event Sourcing (Audit Trail)
```sql
CREATE TABLE transfer_events (
    event_id BIGSERIAL PRIMARY KEY,
    transfer_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,  -- 'initiated', 'prepared', 'committed', 'failed'
    event_data JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### 4. Eventual Consistency (Acceptable Delay)
- Tank snapshots don't need to be real-time synchronized
- Use background jobs to sync metadata periodically
- Accept 1-2 second delay in NetworkDashboard stats

---

## Testing Strategy

### Unit Tests
```python
# test_discovery_service.py
def test_register_server():
    discovery = DiscoveryService()
    server = ServerInfo(server_id="test-1", ...)
    assert discovery.register_server(server) == True
    assert "test-1" in discovery.servers

def test_heartbeat_timeout():
    discovery = DiscoveryService()
    discovery.register_server(server)

    # Simulate 35 seconds passing
    with freeze_time("+35 seconds"):
        discovery.check_health()
        assert discovery.get_server("test-1").status == "offline"
```

### Integration Tests
```python
# test_multi_server.py
async def test_cross_server_transfer():
    # Start 2 servers
    server1 = await start_server(port=8001)
    server2 = await start_server(port=8002)

    # Create tank on server1
    tank1 = await server1.create_tank("Tank A")
    fish = await tank1.spawn_fish()

    # Create tank on server2
    tank2 = await server2.create_tank("Tank B")

    # Transfer fish from tank1 to tank2
    result = await gateway.transfer_entity(
        source_tank_id=tank1.id,
        dest_tank_id=tank2.id,
        entity_id=fish.id
    )

    assert result.success == True
    assert len(await tank1.get_fish()) == 0
    assert len(await tank2.get_fish()) == 1
```

### Load Tests
```python
# test_load.py using locust
from locust import HttpUser, task, between

class TankWorldUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def view_tanks(self):
        self.client.get("/api/tanks")

    @task(1)
    def create_tank(self):
        self.client.post("/api/tanks", json={
            "name": f"Load Test Tank {uuid.uuid4()}",
            "description": "Performance test"
        })
```

**Target Metrics:**
- Support 100 tanks per server
- Handle 1000 concurrent WebSocket connections per server
- Tank creation < 500ms p95
- Entity transfer < 1s p95

---

## Migration Path

### Step 1: Deploy Discovery Service (No Downtime)
```bash
# Deploy discovery as separate service
docker run -d -p 9000:9000 tank-discovery:latest

# Existing server continues running
# No user-facing changes
```

### Step 2: Enable Multi-Server (Feature Flag)
```python
# Feature flag in config
ENABLE_DISTRIBUTED_MODE = os.getenv("DISTRIBUTED_MODE", "false") == "true"

if ENABLE_DISTRIBUTED_MODE:
    # Register with discovery
    await register_with_discovery()
else:
    # Single-server mode (current)
    pass
```

### Step 3: Gradual Rollout
```bash
# Week 1: 10% of traffic on new architecture
# Week 2: 50% of traffic
# Week 3: 100% of traffic
# Week 4: Remove feature flag, make distributed default
```

---

## Security Considerations

### 1. Server-to-Server Authentication
```python
# Each server has a shared secret or mTLS certificate
async def authenticate_server_request(request):
    # Option A: HMAC signature
    signature = request.headers.get("X-Server-Signature")
    expected = hmac.new(SECRET_KEY, request.body, "sha256").hexdigest()
    if signature != expected:
        raise Unauthorized()

    # Option B: mTLS (preferred)
    cert = request.transport.get_extra_info("ssl_object").getpeercert()
    if not verify_server_cert(cert):
        raise Unauthorized()
```

### 2. Network Segmentation
- Discovery service in private subnet
- Servers communicate via internal network only
- Public load balancer for client connections
- Firewall rules: servers can't be accessed directly from internet

### 3. Secrets Management
```python
# Use HashiCorp Vault or AWS Secrets Manager
from hvac import Client

vault = Client(url="https://vault.internal")
jwt_secret = vault.secrets.kv.v2.read_secret_version(path="tank-world/jwt-secret")
db_password = vault.secrets.kv.v2.read_secret_version(path="tank-world/db-password")
```

---

## Cost Estimation

### Development (3 servers, low traffic)
- 3x t3.medium EC2 (or equivalent): $75/month
- PostgreSQL RDS (db.t3.small): $30/month
- Redis ElastiCache (cache.t3.micro): $15/month
- **Total: ~$120/month**

### Production (10 servers, 1000 tanks)
- 10x c6i.2xlarge EC2: $1,200/month
- PostgreSQL RDS (db.r6g.xlarge): $400/month
- Redis ElastiCache (cache.r6g.large): $150/month
- Load Balancer: $25/month
- S3 Storage (100GB snapshots): $2/month
- Data Transfer: $50/month
- **Total: ~$1,827/month**

---

## Summary

**Current State (v1.0):**
- ✅ Single-server with server-aware data model
- ✅ Foundation for distributed architecture
- ✅ File-based persistence
- ✅ Server metadata tracked

**Next Implementation (v2.0):**
1. **Phase 1:** Discovery service + multi-server local testing (1-2 weeks)
2. **Phase 2:** Cross-server communication + metadata store (2-3 weeks)
3. **Phase 3:** Production hardening + PostgreSQL + auth (3-4 weeks)

**Total Time Estimate:** 6-9 weeks for fully distributed production system

**Key Design Decisions:**
- Use PostgreSQL for metadata (tank locations, permissions)
- Use Redis for real-time state caching (optional)
- Direct WebSocket connections (client → tank's server)
- Two-phase commit for entity transfers
- Eventual consistency for dashboard stats
- Load balancing based on tank count + resource usage

**Risk Mitigation:**
- Feature flags for gradual rollout
- Extensive integration tests
- Monitoring from day 1
- Graceful degradation (if discovery service down, servers continue running existing tanks)
