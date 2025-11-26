#!/usr/bin/env python3
"""Test script for running multiple Tank World servers for distributed testing.

This script helps test the distributed server discovery and communication
infrastructure by making it easy to run multiple server instances on different
ports with different server IDs.

Usage:
    # Run server on port 8000 (default)
    python test_distributed_servers.py

    # Run server on port 8001 with custom server ID
    python test_distributed_servers.py --port 8001 --server-id tank-server-2

    # Run server on port 8002 and register with another server
    python test_distributed_servers.py --port 8002 --server-id tank-server-3 --register-with http://localhost:8001
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)


async def register_with_remote_server(
    local_host: str,
    local_port: int,
    local_server_id: str,
    remote_url: str,
) -> bool:
    """Register this server with a remote discovery service.

    Args:
        local_host: This server's host
        local_port: This server's port
        local_server_id: This server's ID
        remote_url: Remote server URL (e.g., http://localhost:8000)

    Returns:
        True if registration successful, False otherwise
    """
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            # Get our own server info
            response = await client.get(f"http://{local_host}:{local_port}/api/servers/local")
            if response.status_code != 200:
                logger.error("Failed to get local server info")
                return False

            local_server_info = response.json()

            # Register with remote server
            register_url = f"{remote_url}/api/discovery/register"
            response = await client.post(register_url, json=local_server_info)

            if response.status_code == 200:
                logger.info(f"Successfully registered with {remote_url}")
                return True
            else:
                logger.error(f"Failed to register with {remote_url}: {response.status_code}")
                return False

    except Exception as e:
        logger.error(f"Error registering with remote server: {e}")
        return False


async def start_with_registration(
    port: int,
    server_id: str,
    register_with: str | None,
    data_dir: str,
) -> None:
    """Start server and optionally register with another server.

    Args:
        port: Port to run on
        server_id: Server ID to use
        register_with: Optional remote server URL to register with
        data_dir: Data directory for this server
    """
    # Wait for server to start
    await asyncio.sleep(5)

    if register_with:
        logger.info(f"Attempting to register with {register_with}...")
        await register_with_remote_server("localhost", port, server_id, register_with)


def main():
    parser = argparse.ArgumentParser(
        description="Run a Tank World server for distributed testing"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)",
    )
    parser.add_argument(
        "--server-id",
        type=str,
        default="local-server",
        help="Server ID (default: local-server)",
    )
    parser.add_argument(
        "--register-with",
        type=str,
        help="Remote server URL to register with (e.g., http://localhost:8001)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Data directory for this server (default: data_<port>)",
    )
    parser.add_argument(
        "--no-default-tank",
        action="store_true",
        help="Don't create a default tank on startup",
    )

    args = parser.parse_args()

    # Set data directory
    if args.data_dir:
        data_dir = args.data_dir
    else:
        data_dir = f"data_{args.port}"

    os.makedirs(data_dir, exist_ok=True)

    # Set environment variables for this server instance
    os.environ["TANK_SERVER_ID"] = args.server_id
    os.environ["TANK_API_PORT"] = str(args.port)
    os.environ["TANK_DATA_DIR"] = data_dir

    logger.info("=" * 60)
    logger.info(f"Starting Tank World Server")
    logger.info(f"  Server ID: {args.server_id}")
    logger.info(f"  Port: {args.port}")
    logger.info(f"  Data Dir: {data_dir}")
    if args.register_with:
        logger.info(f"  Will register with: {args.register_with}")
    logger.info("=" * 60)

    # Import and modify backend settings
    from backend import main as backend_main

    # Override server ID and port
    backend_main.SERVER_ID = args.server_id
    backend_main.DEFAULT_API_PORT = args.port

    # Override data directory for discovery service
    from pathlib import Path
    backend_main.discovery_service._data_dir = Path(data_dir)
    backend_main.discovery_service._registry_file = Path(data_dir) / "server_registry.json"

    # Optionally skip default tank creation
    if args.no_default_tank and backend_main.tank_registry._default_tank_id:
        tank_id = backend_main.tank_registry._default_tank_id
        backend_main.tank_registry.remove_tank(tank_id)
        logger.info("Removed default tank")

    # Schedule registration if needed
    if args.register_with:
        asyncio.create_task(
            start_with_registration(
                args.port,
                args.server_id,
                args.register_with,
                data_dir,
            )
        )

    # Start the server
    import uvicorn
    # Suppress uvicorn access logs for test runs to avoid noisy output
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    uvicorn.run(backend_main.app, host="0.0.0.0", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
