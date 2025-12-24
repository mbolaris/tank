"""FastAPI backend application entry point.

This module initializes the application using the factory pattern.
It serves as the entry point for uvicorn.
"""
import os
import uvicorn
from typing import Any

from backend.app_factory import create_app

# Create the application instance using the factory
# This global 'app' variable is what uvicorn looks for
app = create_app()


def main() -> None:
    """Run the application using uvicorn when executed directly."""
    # Use environment variables for configuration
    port = int(os.getenv("TANK_API_PORT", "8000"))
    
    # Enable reload by default unless in production
    is_production = os.getenv("PRODUCTION", "false").lower() == "true"
    
    # Configure uvicorn
    uvicorn.run(
        "backend.main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=not is_production, 
        log_level="info",
        # Use safe defaults for loop policy on Windows
        loop="asyncio" if os.name == "nt" else "auto"
    )


if __name__ == "__main__":
    main()
