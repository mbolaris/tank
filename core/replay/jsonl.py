from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, TextIO


class ReplayFormatError(ValueError):
    pass


REPLAY_FORMAT_VERSION = 1


@dataclass(frozen=True)
class ReplayHeader:
    version: int
    seed: int
    initial_mode: str
    config: dict[str, Any]
    fingerprint: dict[str, Any]


class JsonlReplayWriter:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._fh: TextIO = self._path.open("w", encoding="utf-8", newline="\n")
        self._wrote_header = False

    @property
    def path(self) -> Path:
        return self._path

    def write_header(
        self,
        *,
        seed: int,
        initial_mode: str,
        config: dict[str, Any] | None = None,
        fingerprint: dict[str, Any] | None = None,
        version: int = REPLAY_FORMAT_VERSION,
    ) -> None:
        if self._wrote_header:
            raise ReplayFormatError("Replay header already written")
        header = {
            "type": "header",
            "version": int(version),
            "seed": int(seed),
            "initial_mode": str(initial_mode),
            "config": dict(config or {}),
            "fingerprint": dict(
                fingerprint
                or {
                    "algorithm": "blake2b",
                    "digest_size": 16,
                }
            ),
        }
        self._write_line(header)
        self._wrote_header = True

    def write_event(self, event: dict[str, Any]) -> None:
        if not self._wrote_header:
            raise ReplayFormatError("Replay header must be written before events")
        if not isinstance(event, dict):
            raise ReplayFormatError("Replay event must be a dict")
        if "type" not in event:
            raise ReplayFormatError("Replay event missing required key: type")
        self._write_line(event)

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> JsonlReplayWriter:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _write_line(self, obj: dict[str, Any]) -> None:
        self._fh.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=True))
        self._fh.write("\n")


class JsonlReplayReader:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def read_header(self) -> ReplayHeader:
        with self._path.open("r", encoding="utf-8") as fh:
            first = fh.readline()
        if not first:
            raise ReplayFormatError("Empty replay file")
        obj = json.loads(first)
        if obj.get("type") != "header":
            raise ReplayFormatError("First line must be a header record")
        return ReplayHeader(
            version=int(obj.get("version", 0)),
            seed=int(obj.get("seed")),
            initial_mode=str(obj.get("initial_mode")),
            config=dict(obj.get("config") or {}),
            fingerprint=dict(obj.get("fingerprint") or {}),
        )

    def iter_events(self) -> Iterator[dict[str, Any]]:
        with self._path.open("r", encoding="utf-8") as fh:
            first = fh.readline()
            if not first:
                return
            # Validate header line
            header = json.loads(first)
            if header.get("type") != "header":
                raise ReplayFormatError("First line must be a header record")
            for line_num, line in enumerate(fh, start=2):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception as exc:
                    raise ReplayFormatError(f"Invalid JSON on line {line_num}: {exc}") from exc
                if not isinstance(obj, dict):
                    raise ReplayFormatError(f"Replay event on line {line_num} must be a dict")
                yield obj
