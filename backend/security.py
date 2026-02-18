"""Security middleware and utilities for production deployment.

This module provides:
- Rate limiting for API endpoints
- Request validation
- Security headers
- IP-based access control (optional)
"""

import os
import time
from collections import defaultdict
from functools import wraps
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Configuration from environment
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))  # requests per window
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # window in seconds

# Whitelist for internal/development IPs
IP_WHITELIST = set(filter(None, os.getenv("IP_WHITELIST", "127.0.0.1,::1").split(",")))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware.

    For production with multiple workers, use Redis-based rate limiting instead.
    """

    def __init__(self, app, requests_per_window: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.request_counts: dict[str, list] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, considering proxy headers."""
        # Check for proxy headers (when behind nginx/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the chain (original client)
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limit."""
        if not RATE_LIMIT_ENABLED:
            return False

        # Whitelist check
        if client_ip in IP_WHITELIST:
            return False

        current_time = time.time()
        window_start = current_time - self.window_seconds

        # Clean old requests outside the window
        self.request_counts[client_ip] = [
            ts for ts in self.request_counts[client_ip] if ts > window_start
        ]

        # Check if over limit
        if len(self.request_counts[client_ip]) >= self.requests_per_window:
            return True

        # Record this request
        self.request_counts[client_ip].append(current_time)
        return False

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)

        # Skip rate limiting for health checks and WebSocket upgrades
        if request.url.path in ["/health", "/ws"] or request.url.path.startswith("/ws/"):
            return await call_next(request)

        if self._is_rate_limited(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.requests_per_window} per {self.window_seconds}s",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Prevent caching of sensitive data
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate incoming requests for basic security."""

    # Maximum content length (10MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_CONTENT_LENGTH:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"error": "Request too large", "max_size": self.MAX_CONTENT_LENGTH},
            )

        return await call_next(request)


def setup_security_middleware(app, enable_rate_limiting: bool = True):
    """Setup all security middleware for the FastAPI app.

    Args:
        app: FastAPI application instance
        enable_rate_limiting: Whether to enable rate limiting
    """
    # Add middlewares in order (last added = first executed)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware)

    if enable_rate_limiting and RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_window=RATE_LIMIT_REQUESTS,
            window_seconds=RATE_LIMIT_WINDOW,
        )


# Decorator for endpoint-specific rate limiting
def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Decorator for endpoint-specific rate limiting.

    Usage:
        @app.get("/api/expensive-operation")
        @rate_limit(max_requests=5, window_seconds=60)
        async def expensive_operation():
            ...
    """
    request_counts: dict[str, list] = defaultdict(list)

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not RATE_LIMIT_ENABLED:
                return await func(request, *args, **kwargs)

            # Get client IP
            client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            if not client_ip:
                client_ip = request.headers.get("X-Real-IP", "")
            if not client_ip and request.client:
                client_ip = request.client.host

            # Whitelist check
            if client_ip in IP_WHITELIST:
                return await func(request, *args, **kwargs)

            current_time = time.time()
            window_start = current_time - window_seconds

            # Clean old requests
            request_counts[client_ip] = [
                ts for ts in request_counts[client_ip] if ts > window_start
            ]

            if len(request_counts[client_ip]) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s",
                    headers={"Retry-After": str(window_seconds)},
                )

            request_counts[client_ip].append(current_time)
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


# WebSocket connection limiter
class WebSocketLimiter:
    """Limit WebSocket connections per IP."""

    def __init__(self, max_connections_per_ip: int = 5):
        self.max_connections = max_connections_per_ip
        self.connections: dict[str, int] = defaultdict(int)

    def can_connect(self, client_ip: str) -> bool:
        """Check if client can open a new WebSocket connection."""
        if client_ip in IP_WHITELIST:
            return True
        return self.connections[client_ip] < self.max_connections

    def connect(self, client_ip: str) -> bool:
        """Register a new connection. Returns False if limit exceeded."""
        if not self.can_connect(client_ip):
            return False
        self.connections[client_ip] += 1
        return True

    def disconnect(self, client_ip: str):
        """Unregister a connection."""
        if self.connections[client_ip] > 0:
            self.connections[client_ip] -= 1


# Global WebSocket limiter instance
websocket_limiter = WebSocketLimiter(max_connections_per_ip=5)
