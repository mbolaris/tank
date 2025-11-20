"""FastAPI backend for fish tank simulation."""

import asyncio
import json
import logging
import platform
import sys
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Set up logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)

# Windows-specific asyncio configuration
if platform.system() == "Windows":
    logger.info("Windows detected - configuring asyncio event loop policy")
    try:
        # Use ProactorEventLoop on Windows for better compatibility
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info("Set WindowsProactorEventLoopPolicy for asyncio")
    except Exception as e:
        logger.warning(f"Could not set Windows event loop policy: {e}")

# Add parent directory to path so we can import from root tank/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models import Command
from backend.simulation_runner import SimulationRunner
from core.constants import DEFAULT_API_PORT, FRAME_RATE

# Global simulation runner
simulation = SimulationRunner()

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()


def _handle_task_exception(task: asyncio.Task) -> None:
    """Handle exceptions from background tasks."""
    try:
        exc = task.exception()
        if exc is not None:
            logger.error(
                f"Unhandled exception in task {task.get_name()}: {exc}",
                exc_info=(type(exc), exc, exc.__traceback__),
            )
    except asyncio.CancelledError:
        logger.debug(f"Task {task.get_name()} was cancelled")
    except Exception as e:
        logger.error(f"Error getting task exception: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    broadcast_task = None
    try:
        # Startup
        logger.info("=" * 60)
        logger.info("LIFESPAN STARTUP: Beginning initialization")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Python: {sys.version}")
        logger.info("=" * 60)

        logger.info("Starting simulation...")
        try:
            simulation.start()
            logger.info("Simulation started successfully!")
        except Exception as e:
            logger.error(f"Failed to start simulation: {e}", exc_info=True)
            raise

        # Start broadcast task with exception callback
        logger.info("Starting broadcast task...")
        broadcast_task = asyncio.create_task(broadcast_updates(), name="broadcast_updates")
        broadcast_task.add_done_callback(_handle_task_exception)
        logger.info("Broadcast task started successfully!")

        logger.info("LIFESPAN STARTUP: Complete - yielding control to app")
        yield
        logger.info("LIFESPAN SHUTDOWN: Received shutdown signal")

    except Exception as e:
        logger.error(f"Exception in lifespan startup: {e}", exc_info=True)
        raise
    finally:
        # Shutdown
        logger.info("LIFESPAN SHUTDOWN: Cleaning up resources...")
        try:
            logger.info("Stopping simulation...")
            simulation.stop()
            logger.info("Simulation stopped!")
        except Exception as e:
            logger.error(f"Error stopping simulation: {e}", exc_info=True)

        if broadcast_task:
            try:
                logger.info("Cancelling broadcast task...")
                broadcast_task.cancel()
                with suppress(asyncio.CancelledError):
                    await broadcast_task
                logger.info("Broadcast task cancelled!")
            except Exception as e:
                logger.error(f"Error cancelling broadcast task: {e}", exc_info=True)

        logger.info("LIFESPAN SHUTDOWN: Complete")
        logger.info("=" * 60)


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
    logger.info("broadcast_updates: Task started")

    # Unpause simulation now that broadcast task is ready
    # This prevents initial fish from aging before the frontend sees them
    simulation.world.paused = False
    logger.info("broadcast_updates: Simulation unpaused")

    frame_count = 0
    try:
        while True:
            try:
                frame_count += 1

                if connected_clients:
                    if frame_count % 60 == 0:  # Log every 60 frames (~2 seconds)
                        logger.debug(
                            f"broadcast_updates: Frame {frame_count}, clients: {len(connected_clients)}"
                        )

                    try:
                        # Get current state
                        state = simulation.get_state()
                    except Exception as e:
                        logger.error(
                            f"broadcast_updates: Error getting simulation state: {e}", exc_info=True
                        )
                        await asyncio.sleep(1 / FRAME_RATE)
                        continue

                    try:
                        # Convert to JSON
                        state_json = state.model_dump_json()
                    except Exception as e:
                        logger.error(
                            f"broadcast_updates: Error serializing state to JSON: {e}", exc_info=True
                        )
                        await asyncio.sleep(1 / FRAME_RATE)
                        continue

                    # Broadcast to all clients
                    disconnected = set()
                    for client in list(connected_clients):  # Copy to avoid modification during iteration
                        try:
                            await client.send_text(state_json)
                        except Exception as e:
                            logger.warning(
                                f"broadcast_updates: Error sending to client, marking for removal: {e}"
                            )
                            disconnected.add(client)

                    # Remove disconnected clients
                    if disconnected:
                        logger.info(
                            f"broadcast_updates: Removing {len(disconnected)} disconnected clients"
                        )
                        connected_clients.difference_update(disconnected)

            except asyncio.CancelledError:
                logger.info("broadcast_updates: Task cancelled")
                raise
            except Exception as e:
                logger.error(
                    f"broadcast_updates: Unexpected error in main loop: {e}", exc_info=True
                )
                # Continue running even if there's an error
                await asyncio.sleep(1 / FRAME_RATE)
                continue

            # Wait for next frame
            try:
                await asyncio.sleep(1 / FRAME_RATE)
            except asyncio.CancelledError:
                logger.info("broadcast_updates: Task cancelled during sleep")
                raise

    except asyncio.CancelledError:
        logger.info("broadcast_updates: Task cancelled (outer handler)")
        raise
    except Exception as e:
        logger.error(f"broadcast_updates: Fatal error, task exiting: {e}", exc_info=True)
        raise
    finally:
        logger.info("broadcast_updates: Task ended")


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


@app.get("/api/lineage")
async def get_lineage():
    """Get phylogenetic lineage data for all fish.

    Returns:
        List of lineage records with parent-child relationships for tree visualization
    """
    try:
        # Get lineage data from ecosystem manager
        lineage_data = simulation.world.ecosystem.get_lineage_data()
        logger.info(f"Lineage API: Returning {len(lineage_data)} lineage records")
        if len(lineage_data) == 0:
            logger.warning("Lineage API: lineage_log is empty! This should contain records for all fish ever born.")
            logger.warning(
                f"Lineage API: Current stats - total_births: {simulation.world.ecosystem.total_births}, "
                f"next_fish_id: {simulation.world.ecosystem.next_fish_id}"
            )
        return JSONResponse(lineage_data)
    except Exception as e:
        logger.error(f"Error getting lineage data: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time simulation updates."""
    client_id = id(websocket)
    logger.info(f"WebSocket: New connection attempt from client {client_id}")

    try:
        await websocket.accept()
        logger.info(f"WebSocket: Accepted connection from client {client_id}")
    except Exception as e:
        logger.error(f"WebSocket: Error accepting connection from client {client_id}: {e}", exc_info=True)
        return

    connected_clients.add(websocket)
    logger.info(f"WebSocket: Client {client_id} added to connected_clients. Total clients: {len(connected_clients)}")

    try:
        while True:
            try:
                # Receive messages from client
                logger.debug(f"WebSocket: Waiting for message from client {client_id}")
                data = await websocket.receive_text()
                logger.debug(f"WebSocket: Received message from client {client_id}: {data[:100]}...")

                try:
                    # Parse command
                    command_data = json.loads(data)
                    command = Command(**command_data)
                    logger.info(f"WebSocket: Client {client_id} sent command: {command.command}")

                    # Handle command
                    result = simulation.handle_command(command.command, command.data)

                    # Send response
                    if result is not None:
                        # Command returned a result (e.g., poker game state)
                        await websocket.send_json(result)
                    else:
                        # Send acknowledgment for commands that don't return data
                        await websocket.send_json(
                            {"type": "ack", "command": command.command, "status": "success"}
                        )
                    logger.debug(f"WebSocket: Sent response to client {client_id}")

                except json.JSONDecodeError as e:
                    logger.warning(f"WebSocket: Invalid JSON from client {client_id}: {e}")
                    await websocket.send_json({"type": "error", "message": f"Invalid JSON: {str(e)}"})
                except Exception as e:
                    logger.error(f"WebSocket: Error handling command from client {client_id}: {e}", exc_info=True)
                    await websocket.send_json({"type": "error", "message": str(e)})

            except WebSocketDisconnect:
                # Re-raise to be handled by outer exception handler
                raise
            except asyncio.CancelledError:
                logger.info(f"WebSocket: Connection cancelled for client {client_id}")
                raise
            except Exception as e:
                logger.error(f"WebSocket: Error in message loop for client {client_id}: {e}", exc_info=True)
                break

    except WebSocketDisconnect as e:
        disconnect_code = e.code if hasattr(e, 'code') else 'unknown'
        logger.info(f"WebSocket: Client {client_id} disconnected normally (code: {disconnect_code})")
    except Exception as e:
        logger.error(f"WebSocket: Unexpected error for client {client_id}: {e}", exc_info=True)
    finally:
        connected_clients.discard(websocket)
        logger.info(f"WebSocket: Client {client_id} removed. Total clients: {len(connected_clients)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_API_PORT)
