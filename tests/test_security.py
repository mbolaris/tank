import json
import re
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
    is_origin_allowed,
    resolve_allowed_origins,
    resolve_bind_host,
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


# ---------------------------------------------------------------------------
# Browser origin policy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://[::1]:3000",
        "https://localhost",
        "http://192.168.1.42:3000",
        "http://10.0.0.7:3000",
        "http://172.16.5.4:3000",
    ],
)
def test_local_origins_allowed_by_default(origin: str) -> None:
    """Loopback and private-network origins keep working with no config.

    The frontend derives its socket URL from window.location.hostname, so a
    LAN-accessed UI presents a private-IP origin; rejecting those would break
    the supported workflow.
    """
    assert is_origin_allowed(origin, [])


@pytest.mark.parametrize(
    "origin",
    [
        "http://evil.example",
        "https://attacker.test:3000",
        "http://8.8.8.8:3000",
        "http://localhost.evil.example",
        "http://127.0.0.1.evil.example",
        "file://",
        "null",
    ],
)
def test_public_origins_rejected_by_default(origin: str) -> None:
    """Any origin off the local network is refused.

    Covers the real attack: a page the operator happens to visit reaching the
    unauthenticated simulation API. Includes suffix-confusion hosts, which a
    naive substring check on "localhost"/"127.0.0.1" would wrongly admit.
    """
    assert not is_origin_allowed(origin, [])


def test_missing_origin_allowed_for_non_browser_clients() -> None:
    """curl and the tools/ CLI scripts send no Origin and must keep working."""
    assert is_origin_allowed(None, [])
    assert is_origin_allowed("", [])


def test_explicit_allowlist_is_exact_and_overrides_local_default() -> None:
    """An explicit ALLOWED_ORIGINS wins outright — including over loopback."""
    allowed = ["https://tank.example.com"]
    assert is_origin_allowed("https://tank.example.com", allowed)
    assert not is_origin_allowed("https://tank.example.com.evil.test", allowed)
    assert not is_origin_allowed("http://localhost:3000", allowed)


def test_resolve_allowed_origins_parses_and_trims() -> None:
    assert resolve_allowed_origins("https://a.test, https://b.test ,") == [
        "https://a.test",
        "https://b.test",
    ]
    assert resolve_allowed_origins("") == []


def test_local_origin_regex_matches_predicate() -> None:
    """CORSMiddleware matches by regex while the WS path uses the predicate;
    they must agree or the two surfaces would drift apart."""
    pattern = re.compile(security_module.LOCAL_ORIGIN_REGEX)
    for origin in ("http://localhost:3000", "http://192.168.1.9:5173", "http://[::1]:8000"):
        assert pattern.match(origin), origin
        assert is_origin_allowed(origin, [])
    for origin in ("http://evil.example", "http://127.0.0.1.evil.example"):
        assert not pattern.match(origin), origin


def test_resolve_bind_host_defaults_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    """The API is unauthenticated, so it must not reach the LAN by default."""
    monkeypatch.delenv("TANK_BIND_HOST", raising=False)
    assert resolve_bind_host() == "127.0.0.1"

    monkeypatch.setenv("TANK_BIND_HOST", "0.0.0.0")
    assert resolve_bind_host() == "0.0.0.0"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("origin", "expect_rejected"),
    [
        ("http://evil.example", True),
        ("http://localhost:3000", False),
        ("http://192.168.1.42:3000", False),
        (None, False),
    ],
)
async def test_websocket_handshake_enforces_origin(
    origin: str | None, expect_rejected: bool
) -> None:
    """The WS handshake must close disallowed origins *before* accept().

    CORS does not cover WebSockets, so without this check any page the
    operator visits could open the socket and issue simulation commands
    (pause/reset/config). Rejection must happen before accept() so a blocked
    origin never reaches the command loop.
    """
    from backend.routers.websocket import _reject_disallowed_origin

    closed: list[int] = []
    accepted: list[bool] = []

    class _FakeWebSocket:
        headers = Headers({"origin": origin} if origin else {})

        async def close(self, code: int = 1000) -> None:
            closed.append(code)

        async def accept(self) -> None:
            accepted.append(True)

    ws = _FakeWebSocket()
    rejected = await _reject_disallowed_origin(ws, "world-1234abcd")  # type: ignore[arg-type]

    assert rejected is expect_rejected
    assert accepted == []  # never accepted during the check
    assert closed == ([4403] if expect_rejected else [])
