# Tank World Net Server Metadata

This note describes how the backend exposes server information in a way that works across
heterogeneous hardware (desktop workstations, cloud VMs, and ARM SBCs like Raspberry Pi).

## What the API Returns

The `/api/servers` and `/api/servers/{server_id}` endpoints now return a `server` payload
alongside the tanks that server is running. Each `server` object includes:

- **Identity & connectivity**: `server_id`, `hostname`, `host`, `port`, `status`, `version`
- **Usage**: `uptime_seconds`, `tank_count`, `is_local`
- **Runtime metrics (optional)**: `cpu_percent`, `memory_mb` when `psutil` is installed
- **Portable hardware descriptors**: `platform`, `architecture`, `hardware_model`, `logical_cpus`

## Portability Notes

- Hardware descriptors rely on Python's standard `platform` and `os` modules, which report
  consistent values across Linux, macOS, Windows, and ARM devices. They avoid shell commands
  or vendor-specific utilities so the data stays portable.
- Runtime metrics only appear when `psutil` is available; the API omits them gracefully on
  constrained systems where `psutil` is not installed or cannot be built.
- Client code should treat `hardware_model` as optional, because some platforms return an
  empty string for `platform.processor()`; in those cases the field will be `null`.

## Example Response

```json
{
  "servers": [
    {
      "server": {
        "server_id": "local-server",
        "hostname": "pi-sim-01",
        "host": "192.168.1.42",
        "port": 8000,
        "status": "online",
        "tank_count": 3,
        "version": "1.0.0",
        "uptime_seconds": 45210.3,
        "cpu_percent": 7.5,
        "memory_mb": 230.1,
        "is_local": true,
        "platform": "Linux",
        "architecture": "arm64",
        "hardware_model": "Apple M1",
        "logical_cpus": 8
      },
      "tanks": [
        { "tank_id": "reef" },
        { "tank_id": "kelp-forest" }
      ]
    }
  ]
}
```
