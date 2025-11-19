"""FastAPI backend for fish tank simulation."""

import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Add parent directory to path so we can import from root tank/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models import Command
from backend.simulation_runner import SimulationRunner

from core.constants import DEFAULT_API_PORT, FRAME_RATE

# Global simulation runner
simulation = SimulationRunner()

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting simulation...")
    simulation.start()
    logger.info("Simulation started!")

    # Start broadcast task
    broadcast_task = asyncio.create_task(broadcast_updates())

    yield

    # Shutdown
    logger.info("Stopping simulation...")
    simulation.stop()
    broadcast_task.cancel()
    with suppress(asyncio.CancelledError):
        await broadcast_task
    logger.info("Simulation stopped!")


# Create FastAPI app with lifespan handler
app = FastAPI(title="Fish Tank Simulation API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast_updates():
    """Broadcast simulation updates to all connected clients."""
    while True:
        if connected_clients:
            try:
                # Get current state
                state = simulation.get_state()

                # Convert to JSON
                state_json = state.model_dump_json()

                # Broadcast to all clients
                disconnected = set()
                for client in connected_clients:
                    try:
                        await client.send_text(state_json)
                    except Exception as e:
                        logger.error(f"Error sending to client: {e}", exc_info=True)
                        disconnected.add(client)

                # Remove disconnected clients
                connected_clients.difference_update(disconnected)
            except Exception as e:
                logger.error(f"Error in broadcast_updates: {e}", exc_info=True)

        # Wait for next frame
        await asyncio.sleep(1 / FRAME_RATE)


@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse(
        {
            "message": "Fish Tank Simulation API",
            "version": "1.0.0",
            "endpoints": {"websocket": "/ws", "health": "/health"},
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    stats = simulation.get_state()
    return JSONResponse(
        {
            "status": "healthy",
            "simulation_running": simulation.running,
            "frame": stats.frame,
            "population": stats.stats.population,
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time simulation updates."""
    await websocket.accept()
    connected_clients.add(websocket)

    logger.info(f"Client connected. Total clients: {len(connected_clients)}")

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            try:
                # Parse command
                command_data = json.loads(data)
                command = Command(**command_data)

                # Handle command
                simulation.handle_command(command.command, command.data)

                # Send acknowledgment
                await websocket.send_json(
                    {"type": "ack", "command": command.command, "status": "success"}
                )

            except Exception as e:
                # Send error response
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        logger.info(f"Client disconnected. Total clients: {len(connected_clients) - 1}")
    finally:
        connected_clients.discard(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_API_PORT)
