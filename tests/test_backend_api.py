import importlib
from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.models import ServerInfo


class MockWorldStatus:
    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return self.data


# Mock WorldManager instead of defining a full Fake class
class FakeWorldManager:
    def __init__(self, worlds: Optional[List[Dict]] = None):
        self.worlds = [MockWorldStatus(w) for w in worlds or []]

    def list_worlds(self):
        return self.worlds


def get_router_module(module_path: str):
    module = importlib.import_module(module_path)
    return importlib.reload(module)


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
    def __init__(
        self, remote_worlds: Optional[List[Dict[str, object]]] = None, should_fail: bool = False
    ):
        self.remote_worlds = remote_worlds or []
        self.should_fail = should_fail

    async def list_worlds(self, _server_info: ServerInfo):
        if self.should_fail:
            raise RuntimeError("remote error")
        return self.remote_worlds

    async def close(self):
        return None

    async def send_heartbeat(self, *_args, **_kwargs):
        return True


def build_servers_client(world_manager, discovery_service, server_client, server_info: ServerInfo):
    servers_module = get_router_module("backend.routers.servers")
    app = FastAPI()
    app.include_router(
        servers_module.setup_router(
            world_manager=world_manager,
            discovery_service=discovery_service,
            server_client=server_client,
            get_server_info_callback=lambda: server_info,
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
        world_count=1,
        version="1.0",
        is_local=is_local,
        uptime_seconds=0.0,
    )


def test_get_local_server_info_returns_callback_value():
    world_manager = FakeWorldManager([{"world_id": "w1", "name": "World 1", "world_type": "tank"}])
    local_info = make_server_info("local", True)
    client = build_servers_client(
        world_manager=world_manager,
        discovery_service=FakeDiscoveryService([local_info]),
        server_client=FakeServerClient(),
        server_info=local_info,
    )

    response = client.get("/api/servers/local")

    assert response.status_code == 200
    assert response.json()["server_id"] == "local"


def test_list_servers_combines_local_and_remote_worlds():
    worlds = [{"world_id": "w1", "name": "World 1", "world_type": "tank"}]
    world_manager = FakeWorldManager(worlds)
    local_info = make_server_info("local", True)
    remote_info = make_server_info("remote", False)
    remote_worlds: list[dict[str, object]] = [{"world_id": "remote-1"}]
    discovery_service = FakeDiscoveryService([local_info, remote_info])
    client = build_servers_client(
        world_manager=world_manager,
        discovery_service=discovery_service,
        server_client=FakeServerClient(remote_worlds=remote_worlds),
        server_info=local_info,
    )

    response = client.get("/api/servers")

    assert response.status_code == 200
    servers = {s["server"]["server_id"]: s for s in response.json()["servers"]}
    assert servers["local"]["worlds"] == worlds
    assert servers["remote"]["worlds"] == remote_worlds


def test_get_server_returns_not_found_when_missing():
    world_manager = FakeWorldManager()
    local_info = make_server_info("local", True)
    discovery_service = FakeDiscoveryService([local_info])
    client = build_servers_client(
        world_manager=world_manager,
        discovery_service=discovery_service,
        server_client=FakeServerClient(),
        server_info=local_info,
    )

    response = client.get("/api/servers/unknown")

    assert response.status_code == 404
    assert "Server not found" in response.json()["error"]


def test_remote_server_errors_return_empty_worlds():
    world_manager = FakeWorldManager()
    local_info = make_server_info("local", True)
    remote_info = make_server_info("remote", False)
    discovery_service = FakeDiscoveryService([local_info, remote_info])
    client = build_servers_client(
        world_manager=world_manager,
        discovery_service=discovery_service,
        server_client=FakeServerClient(should_fail=True),
        server_info=local_info,
    )

    response = client.get("/api/servers/remote")

    assert response.status_code == 200
    assert response.json()["worlds"] == []


def test_discovery_registration_and_listing():
    service = FakeDiscoveryService()
    client = build_discovery_client(service)

    server_info = make_server_info("discovery-test", True)
    register_response = client.post("/api/discovery/register", json=server_info.model_dump())
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
