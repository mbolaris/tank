# Fish Tank Simulation Backend

FastAPI backend that runs the fish tank simulation and provides real-time updates via WebSocket.

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
- `GET /api/tank/info` - Get default tank metadata (backwards compatible)
- `GET /api/lineage` - Get phylogenetic lineage data for default tank

### Tank World Net - Multi-Tank API

Tank World Net enables running multiple independent tank simulations on a single server:

- `GET /api/tanks` - List all tanks in the registry
- `POST /api/tanks?name=...&description=...` - Create a new tank
- `GET /api/tanks/{tank_id}` - Get specific tank info
- `DELETE /api/tanks/{tank_id}` - Remove a tank
- `GET /api/tanks/{tank_id}/lineage` - Get lineage for specific tank

**Query Parameters for POST /api/tanks:**
- `name` (required): Human-readable tank name
- `description`: Tank description
- `seed`: Random seed for deterministic behavior
- `owner`: Owner identifier
- `is_public`: Whether tank is publicly visible (default: true)
- `allow_transfers`: Enable entity transfers between tanks (default: false)

#### Tank Control API

- `POST /api/tanks/{tank_id}/pause` - Pause a running tank simulation
- `POST /api/tanks/{tank_id}/resume` - Resume a paused tank simulation
- `POST /api/tanks/{tank_id}/start` - Start a stopped tank simulation
- `POST /api/tanks/{tank_id}/stop` - Stop a running tank and its broadcast task

#### Entity Transfer API

- `POST /api/tanks/{source_tank_id}/transfer?entity_id={id}&destination_tank_id={dest_id}` - Transfer entity between tanks

**Requirements:**
- Both source and destination tanks must have `allow_transfers: true`
- Only Fish and FractalPlant entities can be transferred (Food/Nectar excluded)
- Entity receives new ID in destination tank for proper isolation
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
    "source_tank": "tank-abc123",
    "destination_tank": "tank-def456"
  }
}
```

**Error Responses:**
- `403` - Tank does not allow transfers
- `404` - Tank or entity not found
- `400` - Entity type cannot be transferred
- `500` - Transfer failed (entity restored to source tank)

#### Tank Persistence API (Phase 4A)

- `POST /api/tanks/{tank_id}/save` - Save tank state to a snapshot file
- `POST /api/tanks/load?snapshot_path={path}` - Load tank from snapshot file
- `GET /api/tanks/{tank_id}/snapshots` - List all snapshots for a tank
- `DELETE /api/tanks/{tank_id}/snapshots/{filename}` - Delete a specific snapshot

**Features:**
- Automatic cleanup (keeps last 10 snapshots per tank)
- Complete state preservation (entities, ecosystem stats, frame number)
- Atomic load with validation
- Snapshots stored in `data/tanks/{tank_id}/snapshots/`

#### Transfer History API (Phase 4A)

- `GET /api/transfers?limit=50&tank_id={id}&success_only=true` - Get transfer history
- `GET /api/transfers/{transfer_id}` - Get specific transfer by ID
- `GET /api/tanks/{tank_id}/transfer-stats` - Get transfer statistics for a tank

**Features:**
- Logs all transfer attempts (success and failure)
- In-memory buffer (last 100 transfers)
- Persistent log file: `data/transfers.log`
- Real-time history updates

### WebSocket Endpoints

- `WS /ws` - Connect to default tank (backwards compatible)
- `WS /ws/{tank_id}` - Connect to a specific tank by ID

**Frontend URL Parameters:**
- `?tank={tank_id}` - Connect to a specific tank
- `?server=ws://host:port` - Connect to a remote server

## WebSocket Protocol

### Server → Client (Updates)

The server broadcasts simulation state at 30 FPS:

```json
{
  "type": "update",
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
