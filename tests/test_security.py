import json
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.responses import JSONResponse
from starlette.requests import Request

from backend.security import RequestValidationMiddleware


def _make_request(*, content_length: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if content_length is not None:
        headers.append((b"content-length", content_length.encode("ascii")))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/test",
        "raw_path": b"/api/test",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive)


@pytest.mark.asyncio
async def test_request_validation_rejects_malformed_content_length() -> None:
    middleware = RequestValidationMiddleware(app=AsyncMock())
    request = _make_request(content_length="not-a-number")
    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert json.loads(response.body) == {"error": "Invalid Content-Length header"}
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_request_validation_rejects_oversized_content_length() -> None:
    middleware = RequestValidationMiddleware(app=AsyncMock())
    request = _make_request(content_length=str(RequestValidationMiddleware.MAX_CONTENT_LENGTH + 1))
    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert json.loads(response.body) == {
        "error": "Request too large",
        "max_size": RequestValidationMiddleware.MAX_CONTENT_LENGTH,
    }
    call_next.assert_not_called()
