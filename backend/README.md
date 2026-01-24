# Tank World Backend

FastAPI backend that runs Tank World simulations and provides real-time updates via WebSocket.

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Running the Server

```bash
# From the backend directory
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will start on `http://localhost:8000`

## API Endpoints

### HTTP Endpoints

- `GET /` - API information (includes Tank World Net status)
- `GET /health` - Health check with simulation stats
- `GET /api/lineage` - Get phylogenetic lineage data for default tank

### Tank World Net - Multi-World API

Tank World Net enables running multiple independent world simulations on a single server:

- `GET /api/worlds` - List all worlds in the registry
- `POST /api/worlds?name=...&description=...` - Create a new world
- `GET /api/worlds/{world_id}` - Get specific world info
- `DELETE /api/worlds/{world_id}` - Remove a world
- `GET /api/worlds/{world_id}/lineage` - Get lineage for specific world

**Query Parameters for POST /api/worlds:**
- `name` (required): Human-readable world name
- `description`: World description
- `seed`: Random seed for deterministic behavior
- `owner`: Owner identifier
- `is_public`: Whether world is publicly visible (default: true)
- `allow_transfers`: Enable entity transfers between worlds (default: true)

#### World Control API

- `POST /api/worlds/{world_id}/pause` - Pause a running world simulation
- `POST /api/worlds/{world_id}/resume` - Resume a paused world simulation
- `POST /api/worlds/{world_id}/start` - Start a stopped world simulation
- `POST /api/worlds/{world_id}/stop` - Stop a running world and its broadcast task

#### Server Inventory API

Use these endpoints to understand what servers are available in the Tank World Net and what
hardware they are running on (all values are generated with portable `platform`/`os`
functions, so they work across Linux, macOS, Windows, and ARM boards like Raspberry Pi):

- `GET /api/servers` - List all servers and the worlds running on each one
- `GET /api/servers/{server_id}` - Get a single server with its world list

**Server metadata fields:**

- `server_id`, `hostname`, `host`, `port`, `status`, `version`, `uptime_seconds` - lifecycle metadata
- `tank_count`, `is_local` - multi-world awareness flags
- `cpu_percent`, `memory_mb` - optional runtime usage if `psutil` is available
- `platform`, `architecture`, `hardware_model`, `logical_cpus` - portable hardware descriptors useful for heterogeneous fleets

#### Entity Transfer API

- `POST /api/worlds/{source_world_id}/transfer?entity_id={id}&destination_world_id={dest_id}` - Transfer entity between worlds

**Requirements:**
- Both source and destination worlds must have `allow_transfers: true`
- Only Fish and Plant entities can be transferred (Food/Nectar excluded)
- Entity receives new ID in destination world for proper isolation
- Transfer is atomic with automatic rollback on failure

**Response:**
```json
{
  "success": true,
  "message": "Entity transferred successfully",
  "entity": {
    "old_id": 12345,
    "new_id": 67890,
    "type": "fish",
    "source_world": "world-abc123",
    "destination_world": "world-def456"
  }
}
```

**Error Responses:**
- `403` - World does not allow transfers
- `404` - World or entity not found
- `400` - Entity type cannot be transferred
- `500` - Transfer failed (entity restored to source world)

#### World Persistence API (Phase 4A)

- `POST /api/worlds/{world_id}/save` - Save world state to a snapshot file
- `POST /api/worlds/load?snapshot_path={path}` - Load world from snapshot file
- `GET /api/worlds/{world_id}/snapshots` - List all snapshots for a world
- `DELETE /api/worlds/{world_id}/snapshots/{filename}` - Delete a specific snapshot

**Features:**
- Automatic cleanup (keeps last 10 snapshots per world)
- Complete state preservation (entities, ecosystem stats, frame number)
- Atomic load with validation
- Snapshots stored in `data/worlds/{world_id}/snapshots/`

#### Transfer History API (Phase 4A)

- `GET /api/transfers?limit=50&world_id={id}&success_only=true` - Get transfer history
- `GET /api/transfers/{transfer_id}` - Get specific transfer by ID
- `GET /api/worlds/{world_id}/transfer-stats` - Get transfer statistics for a world

**Features:**
- Logs all transfer attempts (success and failure)
- In-memory buffer (last 100 transfers)
- Persistent log file: `data/transfers.log`
- Real-time history updates

### WebSocket Endpoints

- `WS /ws` - Connect to default world
- `WS /ws/world/{world_id}` - Connect to a specific world by ID

**Frontend URL Parameters:**
- `?world={world_id}` - Connect to a specific world
- `?server=ws://host:port` - Connect to a remote server

## WebSocket Protocol

### Server → Client (Updates)

The server broadcasts simulation state at 30 FPS:

```json
{
  "type": "update",
  "world_id": "world-123",
  "frame": 123,
  "entities": [
    {
      "id": 12345,
      "type": "fish",
      "x": 100.5,
      "y": 200.3,
      "width": 32,
      "height": 32,
      "energy": 75.5,
      "species": "neural",
      "generation": 2,
      "age": 450,
      "genome_data": {
        "speed": 1.1,
        "size": 0.95,
        "color_hue": 180
      }
    },
    {
      "id": 12346,
      "type": "food",
      "x": 300,
      "y": 400,
      "width": 16,
      "height": 16,
      "food_type": 0
    }
  ],
  "stats": {
    "frame": 123,
    "population": 10,
    "generation": 2,
    "births": 15,
    "deaths": 5,
    "capacity": "20%",
    "time": "Day",
    "death_causes": {
      "starvation": 3,
      "old_age": 2
    },
    "fish_count": 10,
    "food_count": 5,
    "plant_count": 3
  }
}
```

### Client → Server (Commands)

```json
{"command": "add_food"}
{"command": "pause"}
{"command": "resume"}
{"command": "reset"}
```

### Server → Client (Acknowledgments)

```json
{
  "type": "ack",
  "command": "add_food",
  "status": "success"
}
```

## Architecture

- `main.py` - FastAPI app with WebSocket endpoint
- `simulation_runner.py` - Background thread running the simulation
- `models.py` - Pydantic models for data serialization
- `requirements.txt` - Python dependencies

## Development

The backend automatically starts the simulation on startup and broadcasts updates to all connected WebSocket clients.

The simulation runs in a separate thread at 30 FPS, and state updates are broadcast asynchronously to avoid blocking the simulation.
