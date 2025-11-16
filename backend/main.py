"""FastAPI backend for fish tank simulation."""

import asyncio
import json
from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from simulation_runner import SimulationRunner
from models import Command

# Create FastAPI app
app = FastAPI(title="Fish Tank Simulation API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global simulation runner
simulation = SimulationRunner()

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()


@app.on_event("startup")
async def startup_event():
    """Start the simulation when the server starts."""
    print("Starting simulation...")
    simulation.start()
    print("Simulation started!")

    # Start broadcast task
    asyncio.create_task(broadcast_updates())


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the simulation when the server shuts down."""
    print("Stopping simulation...")
    simulation.stop()
    print("Simulation stopped!")


async def broadcast_updates():
    """Broadcast simulation updates to all connected clients."""
    while True:
        if connected_clients:
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
                    print(f"Error sending to client: {e}")
                    disconnected.add(client)

            # Remove disconnected clients
            connected_clients.difference_update(disconnected)

        # Wait for next frame (30 FPS)
        await asyncio.sleep(1 / 30)


@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse({
        "message": "Fish Tank Simulation API",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws",
            "health": "/health"
        }
    })


@app.get("/health")
async def health():
    """Health check endpoint."""
    stats = simulation.get_state()
    return JSONResponse({
        "status": "healthy",
        "simulation_running": simulation.running,
        "frame": stats.frame,
        "population": stats.stats.population
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time simulation updates."""
    await websocket.accept()
    connected_clients.add(websocket)

    print(f"Client connected. Total clients: {len(connected_clients)}")

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
                await websocket.send_json({
                    "type": "ack",
                    "command": command.command,
                    "status": "success"
                })

            except Exception as e:
                # Send error response
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        print(f"Client disconnected. Total clients: {len(connected_clients) - 1}")
    finally:
        connected_clients.discard(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
