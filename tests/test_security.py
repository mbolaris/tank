import json
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.requests import Request

import backend.security as security_module
from backend.security import (
    RequestValidationMiddleware,
    WebSocketLimiter,
    WebSocketMessageRateLimiter,
    resolve_client_ip,
)


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


def test_resolve_client_ip_ignores_forwarded_header_from_untrusted_direct_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a configured trusted proxy, a direct client cannot spoof its IP."""
    monkeypatch.setattr(security_module, "TRUSTED_PROXIES", set())

    client_ip = resolve_client_ip("203.0.113.5", Headers({"X-Forwarded-For": "1.2.3.4"}))

    assert client_ip == "203.0.113.5"


def test_resolve_client_ip_honors_forwarded_header_from_trusted_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured trusted proxy's X-Forwarded-For is used as the real client IP."""
    monkeypatch.setattr(security_module, "TRUSTED_PROXIES", {"10.0.0.1"})

    client_ip = resolve_client_ip("10.0.0.1", Headers({"X-Forwarded-For": "203.0.113.5, 10.0.0.1"}))

    assert client_ip == "203.0.113.5"


def test_resolve_client_ip_falls_back_to_real_ip_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security_module, "TRUSTED_PROXIES", {"10.0.0.1"})

    client_ip = resolve_client_ip("10.0.0.1", Headers({"X-Real-IP": "203.0.113.9"}))

    assert client_ip == "203.0.113.9"


def test_resolve_client_ip_handles_missing_direct_ip() -> None:
    assert resolve_client_ip(None, Headers({})) == "unknown"


def test_ws_message_limiter_allows_under_limit_then_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(security_module, "IP_WHITELIST", set())
    limiter = WebSocketMessageRateLimiter(max_messages=3, window_seconds=60)

    assert all(limiter.allow("203.0.113.5") for _ in range(3))
    assert not limiter.allow("203.0.113.5")
    # Another IP has its own budget.
    assert limiter.allow("203.0.113.6")


def test_ws_message_limiter_window_expiry_frees_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(security_module, "IP_WHITELIST", set())
    limiter = WebSocketMessageRateLimiter(max_messages=1, window_seconds=60)

    assert limiter.allow("203.0.113.5")
    assert not limiter.allow("203.0.113.5")

    # Age the recorded message past the window; the budget frees up.
    limiter.message_times["203.0.113.5"] = [ts - 61 for ts in limiter.message_times["203.0.113.5"]]
    assert limiter.allow("203.0.113.5")


def test_ws_message_limiter_exempts_whitelist_and_disabled_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limiter = WebSocketMessageRateLimiter(max_messages=1, window_seconds=60)

    monkeypatch.setattr(security_module, "IP_WHITELIST", {"127.0.0.1"})
    assert all(limiter.allow("127.0.0.1") for _ in range(10))

    monkeypatch.setattr(security_module, "IP_WHITELIST", set())
    monkeypatch.setattr(security_module, "RATE_LIMIT_ENABLED", False)
    assert all(limiter.allow("203.0.113.5") for _ in range(10))


def test_ws_message_limiter_forget_drops_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security_module, "IP_WHITELIST", set())
    limiter = WebSocketMessageRateLimiter(max_messages=1, window_seconds=60)

    assert limiter.allow("203.0.113.5")
    assert not limiter.allow("203.0.113.5")

    limiter.forget("203.0.113.5")
    assert "203.0.113.5" not in limiter.message_times
    assert limiter.allow("203.0.113.5")


def test_ws_connection_limiter_disconnect_reports_remaining() -> None:
    limiter = WebSocketLimiter(max_connections_per_ip=5)

    assert limiter.connect("203.0.113.5")
    assert limiter.connect("203.0.113.5")
    assert limiter.disconnect("203.0.113.5") == 1
    assert limiter.disconnect("203.0.113.5") == 0
    # Never goes negative.
    assert limiter.disconnect("203.0.113.5") == 0


@pytest.mark.asyncio
async def test_ws_receive_loop_drops_commands_over_message_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single accepted connection cannot spam commands: once over budget,
    commands are rejected with a rate_limited error and never reach the
    adapter's command handler."""
    import backend.routers.websocket as ws_module

    monkeypatch.setattr(security_module, "IP_WHITELIST", set())
    monkeypatch.setattr(
        ws_module,
        "websocket_message_limiter",
        WebSocketMessageRateLimiter(max_messages=1, window_seconds=60),
    )

    command = json.dumps({"command": "ping", "data": None})
    incoming = [
        {"type": "websocket.receive", "text": command},
        {"type": "websocket.receive", "text": command},
        {"type": "websocket.disconnect"},
    ]
    sent: list[bytes] = []

    class _FakeAddress:
        host = "203.0.113.5"

    class _FakeWebSocket:
        client = _FakeAddress()
        headers = Headers({})

        async def accept(self) -> None:
            pass

        async def receive(self) -> dict:
            return incoming.pop(0)

        async def send_bytes(self, payload: bytes) -> None:
            sent.append(payload)

    handled_commands: list[str] = []

    class _FakeAdapter:
        def add_client(self, ws) -> None:
            pass

        def remove_client(self, ws) -> None:
            pass

        async def get_state_async(self, force_full: bool, allow_delta: bool):
            return None

        def serialize_state(self, state) -> bytes:
            return b"{}"

        async def handle_command_async(self, command: str, data):
            handled_commands.append(command)
            return {"ok": True}

    await ws_module._handle_websocket_for_adapter(
        _FakeWebSocket(),  # type: ignore[arg-type]
        _FakeAdapter(),  # type: ignore[arg-type]
        "test-world",
    )

    # First command handled, second dropped by the limiter.
    assert handled_commands == ["ping"]
    responses = [json.loads(payload) for payload in sent]
    assert responses[0] == {"ok": True}
    assert responses[1]["error"] == "rate_limited"
    assert responses[1]["retry_after"] == 60


def test_websocket_get_client_ip_shares_http_trust_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WebSocket connections must resolve client IP the same way HTTP does,
    so a deployment behind TRUSTED_PROXIES doesn't misattribute every
    connection to the proxy's own IP (which would starve the per-IP
    WebSocket connection limit for real clients)."""
    from backend.routers.websocket import _get_client_ip

    monkeypatch.setattr(security_module, "TRUSTED_PROXIES", {"10.0.0.1"})

    class _FakeAddress:
        host = "10.0.0.1"

    class _FakeWebSocket:
        client = _FakeAddress()
        headers = Headers({"X-Forwarded-For": "203.0.113.5"})

    assert _get_client_ip(_FakeWebSocket()) == "203.0.113.5"  # type: ignore[arg-type]
