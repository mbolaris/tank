import importlib
from types import SimpleNamespace
from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.models import ServerInfo


class FakeTankManager:
    def __init__(self, tank_id: str, name: str, allow_transfers: bool = True, running: bool = True):
        self.tank_id = tank_id
        self.tank_info = SimpleNamespace(name=name, allow_transfers=allow_transfers)
        self.world = SimpleNamespace(paused=False)
        self.running = running

    def get_status(self) -> Dict[str, object]:
        return {
            "tank_id": self.tank_id,
            "name": self.tank_info.name,
            "running": self.running,
            "paused": self.world.paused,
        }

    def start(self, start_paused: bool = False) -> None:
        self.running = True
        self.world.paused = start_paused

    def stop(self) -> None:
        self.running = False
        self.world.paused = True


class FakeTankRegistry:
    def __init__(self, managers: Optional[List[FakeTankManager]] = None):
        self.managers: Dict[str, FakeTankManager] = {}
        for manager in managers or []:
            self.managers[manager.tank_id] = manager
        self._default_tank_id: Optional[str] = next(iter(self.managers), None)

    def __iter__(self):
        return iter(self.managers.values())

    @property
    def tank_count(self) -> int:
        return len(self.managers)

    @property
    def default_tank_id(self) -> Optional[str]:
        return self._default_tank_id

    @property
    def default_tank(self) -> Optional[FakeTankManager]:
        return self.managers.get(self._default_tank_id)

    def list_tanks(self, include_private: bool = False):
        return [m.get_status() for m in self.managers.values()]

    def create_tank(self, **kwargs) -> FakeTankManager:
        tank_id = kwargs.get("tank_id") or f"tank-{len(self.managers) + 1}"
        manager = FakeTankManager(
            tank_id=tank_id,
            name=kwargs.get("name", tank_id),
            allow_transfers=kwargs.get("allow_transfers", True),
            running=False,
        )
        self.managers[tank_id] = manager
        if self._default_tank_id is None:
            self._default_tank_id = tank_id
        return manager

    def get_tank(self, tank_id: str) -> Optional[FakeTankManager]:
        return self.managers.get(tank_id)

    def remove_tank(self, tank_id: str, delete_persistent_data: bool = False) -> bool:
        if tank_id in self.managers:
            del self.managers[tank_id]
            if tank_id == self._default_tank_id:
                self._default_tank_id = next(iter(self.managers), None)
            return True
        return False

    def restore_tank_from_snapshot(self, *_args, **_kwargs):
        return None


class FakeDiscoveryService:
    def __init__(self, servers: Optional[List[ServerInfo]] = None):
        self.servers: Dict[str, ServerInfo] = {s.server_id: s for s in servers or []}

    async def register_server(self, server_info: ServerInfo) -> None:
        self.servers[server_info.server_id] = server_info

    async def heartbeat(self, server_id: str, server_info: Optional[ServerInfo] = None) -> bool:
        if server_id not in self.servers:
            return False
        if server_info is not None:
            self.servers[server_id] = server_info
        return True

    async def list_servers(self, status_filter: Optional[str] = None, include_local: bool = True):
        servers = list(self.servers.values())
        if not include_local:
            servers = [s for s in servers if not s.is_local]
        if status_filter:
            servers = [s for s in servers if s.status == status_filter]
        return servers

    async def get_server(self, server_id: str) -> Optional[ServerInfo]:
        return self.servers.get(server_id)

    async def unregister_server(self, server_id: str) -> bool:
        return self.servers.pop(server_id, None) is not None

    async def stop(self) -> None:
        return None


class FakeServerClient:
    def __init__(self, remote_tanks: Optional[List[Dict[str, object]]] = None, should_fail: bool = False):
        self.remote_tanks = remote_tanks or []
        self.should_fail = should_fail

    async def list_tanks(self, _server_info: ServerInfo):
        if self.should_fail:
            raise RuntimeError("remote error")
        return self.remote_tanks

    async def close(self):
        return None

    async def send_heartbeat(self, *_args, **_kwargs):
        return True


async def noop_broadcast(*_args, **_kwargs):
    return None


async def tracking_broadcast(manager: FakeTankManager, calls: List[str]):
    calls.append(manager.tank_id)
    return None


def get_router_module(module_path: str):
    module = importlib.import_module(module_path)
    return importlib.reload(module)


def build_servers_client(tank_registry, discovery_service, server_client, server_info: ServerInfo):
    servers_module = get_router_module("backend.routers.servers")
    app = FastAPI()
    app.include_router(
        servers_module.setup_router(
            tank_registry=tank_registry,
            discovery_service=discovery_service,
            server_client=server_client,
            get_server_info_callback=lambda: server_info,
        )
    )
    return TestClient(app)


def build_tanks_client(tank_registry, start_calls: Optional[List[str]] = None):
    tanks_module = get_router_module("backend.routers.tanks")
    app = FastAPI()
    app.include_router(
        tanks_module.setup_router(
            tank_registry=tank_registry,
            server_id="local-server",
            start_broadcast_callback=(
                (lambda manager: tracking_broadcast(manager, start_calls)) if start_calls is not None else noop_broadcast
            ),
            stop_broadcast_callback=noop_broadcast,
        )
    )
    return TestClient(app)


def build_discovery_client(discovery_service):
    discovery_module = get_router_module("backend.routers.discovery")
    app = FastAPI()
    app.include_router(discovery_module.setup_router(discovery_service))
    return TestClient(app)


def make_server_info(server_id: str, is_local: bool) -> ServerInfo:
    return ServerInfo(
        server_id=server_id,
        hostname=f"{server_id}-host",
        host="127.0.0.1",
        port=8000,
        status="online",
        tank_count=1,
        version="1.0",
        is_local=is_local,
        uptime_seconds=0.0,
    )


def test_get_local_server_info_returns_callback_value():
    registry = FakeTankRegistry([FakeTankManager("tank-1", "Tank 1")])
    local_info = make_server_info("local", True)
    client = build_servers_client(
        tank_registry=registry,
        discovery_service=FakeDiscoveryService([local_info]),
        server_client=FakeServerClient(),
        server_info=local_info,
    )

    response = client.get("/api/servers/local")

    assert response.status_code == 200
    assert response.json()["server_id"] == "local"


def test_list_servers_combines_local_and_remote_tanks():
    registry = FakeTankRegistry([FakeTankManager("tank-1", "Tank 1")])
    local_info = make_server_info("local", True)
    remote_info = make_server_info("remote", False)
    remote_tanks = [{"tank_id": "remote-1"}]
    discovery_service = FakeDiscoveryService([local_info, remote_info])
    client = build_servers_client(
        tank_registry=registry,
        discovery_service=discovery_service,
        server_client=FakeServerClient(remote_tanks=remote_tanks),
        server_info=local_info,
    )

    response = client.get("/api/servers")

    assert response.status_code == 200
    servers = {s["server"]["server_id"]: s for s in response.json()["servers"]}
    assert servers["local"]["tanks"] == registry.list_tanks()
    assert servers["remote"]["tanks"] == remote_tanks


def test_get_server_returns_not_found_when_missing():
    registry = FakeTankRegistry([FakeTankManager("tank-1", "Tank 1")])
    local_info = make_server_info("local", True)
    discovery_service = FakeDiscoveryService([local_info])
    client = build_servers_client(
        tank_registry=registry,
        discovery_service=discovery_service,
        server_client=FakeServerClient(),
        server_info=local_info,
    )

    response = client.get("/api/servers/unknown")

    assert response.status_code == 404
    assert "Server not found" in response.json()["error"]


def test_remote_server_errors_return_empty_tanks():
    registry = FakeTankRegistry([FakeTankManager("tank-1", "Tank 1")])
    local_info = make_server_info("local", True)
    remote_info = make_server_info("remote", False)
    discovery_service = FakeDiscoveryService([local_info, remote_info])
    client = build_servers_client(
        tank_registry=registry,
        discovery_service=discovery_service,
        server_client=FakeServerClient(should_fail=True),
        server_info=local_info,
    )

    response = client.get("/api/servers/remote")

    assert response.status_code == 200
    assert response.json()["tanks"] == []


def test_list_tanks_reports_count_and_default():
    registry = FakeTankRegistry([FakeTankManager("tank-1", "Tank 1")])
    start_calls: List[str] = []
    client = build_tanks_client(registry, start_calls)

    response = client.get("/api/tanks")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["default_tank_id"] == registry.default_tank_id


def test_pause_and_resume_update_status_and_trigger_broadcast():
    manager = FakeTankManager("tank-1", "Tank 1")
    registry = FakeTankRegistry([manager])
    start_calls: List[str] = []
    client = build_tanks_client(registry, start_calls)

    pause_response = client.post(f"/api/tanks/{manager.tank_id}/pause")
    assert pause_response.status_code == 200
    assert manager.world.paused is True

    resume_response = client.post(f"/api/tanks/{manager.tank_id}/resume")
    assert resume_response.status_code == 200
    assert manager.world.paused is False
    assert start_calls == [manager.tank_id]


def test_can_delete_last_remaining_tank():
    manager = FakeTankManager("tank-1", "Tank 1")
    registry = FakeTankRegistry([manager])
    client = build_tanks_client(registry)

    response = client.delete(f"/api/tanks/{manager.tank_id}")

    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()


def test_create_tank_rejects_invalid_server():
    registry = FakeTankRegistry()
    client = build_tanks_client(registry)

    response = client.post(
        "/api/tanks",
        params={"name": "New Tank", "server_id_param": "remote-server"},
    )

    assert response.status_code == 400
    assert "Invalid server_id" in response.json()["error"]


def test_discovery_registration_and_listing():
    service = FakeDiscoveryService()
    client = build_discovery_client(service)

    server_info = make_server_info("discovery-test", True)
    register_response = client.post("/api/discovery/register", json=server_info.dict())
    assert register_response.status_code == 200

    list_response = client.get("/api/discovery/servers")
    assert list_response.status_code == 200
    listed_ids = {srv["server_id"] for srv in list_response.json()["servers"]}
    assert "discovery-test" in listed_ids


def test_heartbeat_requires_registration():
    service = FakeDiscoveryService()
    client = build_discovery_client(service)

    response = client.post("/api/discovery/heartbeat/missing")

    assert response.status_code == 404
    assert "not registered" in response.json()["message"]
