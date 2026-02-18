"""Transfer history API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.transfer_history import get_transfer_by_id, get_transfer_history

router = APIRouter(prefix="/api/transfers", tags=["transfers"])


def setup_router() -> APIRouter:
    """Create and configure the transfers router."""

    @router.get("")
    async def list_transfers(
        limit: int = Query(default=50, ge=1, le=200),
        world_id: str | None = Query(default=None),
        success_only: bool = Query(default=False),
    ) -> JSONResponse:
        """List recent transfers with optional filters."""
        transfers = get_transfer_history(
            limit=limit,
            world_id=world_id,
            success_only=success_only,
        )
        return JSONResponse({"transfers": transfers, "count": len(transfers)})

    @router.get("/{transfer_id}")
    async def get_transfer(transfer_id: str) -> JSONResponse:
        """Get a single transfer record by ID."""
        record = get_transfer_by_id(transfer_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"Transfer not found: {transfer_id}")
        return JSONResponse(record)

    return router
