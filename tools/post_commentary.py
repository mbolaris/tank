#!/usr/bin/env python3
"""Post agent commentary to a running Tank World simulation (the "Insights" feed).

This is the thin, dependency-free client an AI agent (or a human) uses to share
an observation about a *running* simulation so it shows up live in the web UI's
**Insights** tab. It is the write counterpart to the read-only
``tools/evolution_report.py``: that tool tells you *what* is happening; this one
*narrates it to the UI*.

It talks to the commentary REST API (see ``backend/routers/commentary.py``):

    POST   /api/world/{world_id}/commentary
    GET    /api/world/{world_id}/commentary

Posting is purely additive telemetry - it never perturbs the simulation.

Examples
--------
    # Post a single observation to the default world
    python tools/post_commentary.py --url http://127.0.0.1:8000 \
        --text "Selection is real: pursuit_aggression mean +12% over 40k frames" \
        --tags selection,foraging --severity insight --author claude

    # Attach a couple of supporting numbers
    python tools/post_commentary.py --text "Starvation dominates deaths" \
        --severity warning --metric starvation_pct=0.91 --metric max_generation=14

    # Read back what agents have already said (so you don't repeat yourself)
    python tools/post_commentary.py --read --limit 10

    # Scripted narrator: run a command each interval and post its stdout
    python tools/post_commentary.py --watch --interval 300 \
        --cmd "python tools/evolution_report.py --url http://127.0.0.1:8000 --oneline"

For the LLM-driven "live narrator" loop (re-observe and post *genuinely
interesting* insights), use the ``/observe-sim`` skill, which drives this tool.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_URL = "http://127.0.0.1:8000"
DEFAULT_INTERVAL = 300.0
VALID_SEVERITIES = ("info", "insight", "warning", "concern")


# ---------------------------------------------------------------------------
# HTTP (stdlib only; trusted local/LAN URL pointing at the user's own server)
# ---------------------------------------------------------------------------
def _http_get_json(url: str, timeout: float = 10.0) -> Any:
    with urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def _http_post_json(url: str, payload: dict[str, Any], timeout: float = 10.0) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def resolve_world_id(base_url: str, world_id: str | None) -> str:
    """Return an explicit world id, falling back to the server's default world.

    If the default cannot be resolved, returns the literal ``"default"`` - the
    API understands it - so commenting still works on a single-world server.
    """
    if world_id:
        return world_id
    try:
        data = _http_get_json(f"{base_url}/api/worlds/default/id")
        return str(data["world_id"])
    except Exception:
        return "default"


# ---------------------------------------------------------------------------
# Public helpers (importable)
# ---------------------------------------------------------------------------
def post_comment(
    base_url: str,
    text: str,
    *,
    world_id: str | None = None,
    author: str | None = None,
    tags: Any = None,
    severity: str | None = None,
    metrics: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """POST one comment; returns the stored comment dict from the server."""
    base_url = base_url.rstrip("/")
    wid = resolve_world_id(base_url, world_id)
    payload: dict[str, Any] = {"text": text}
    if author:
        payload["author"] = author
    if tags:
        payload["tags"] = tags
    if severity:
        payload["severity"] = severity
    if metrics:
        payload["metrics"] = metrics
    result = _http_post_json(f"{base_url}/api/world/{wid}/commentary", payload, timeout=timeout)
    return result.get("comment", result) if isinstance(result, dict) else {}


def read_comments(
    base_url: str,
    *,
    world_id: str | None = None,
    limit: int | None = None,
    since_id: int | None = None,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    """GET recent comments for a world (newest last)."""
    base_url = base_url.rstrip("/")
    wid = resolve_world_id(base_url, world_id)
    query = []
    if limit is not None:
        query.append(f"limit={limit}")
    if since_id is not None:
        query.append(f"since_id={since_id}")
    suffix = ("?" + "&".join(query)) if query else ""
    data = _http_get_json(f"{base_url}/api/world/{wid}/commentary{suffix}", timeout=timeout)
    comments = data.get("comments", []) if isinstance(data, dict) else []
    return list(comments)


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------
def _parse_metric_value(raw: str) -> Any:
    """Coerce a CLI metric value to int/float/bool when it looks like one."""
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    low = raw.strip().lower()
    if low in ("true", "false"):
        return low == "true"
    return raw


def _parse_metrics(pairs: list[str] | None) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for item in pairs or []:
        if "=" not in item:
            print(f"warning: ignoring --metric '{item}' (expected KEY=VALUE)", file=sys.stderr)
            continue
        key, raw = item.split("=", 1)
        key = key.strip()
        if key:
            metrics[key] = _parse_metric_value(raw)
    return metrics


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.replace(",", " ").split() if t.strip()]


def _format_comment(c: dict[str, Any]) -> str:
    sev = c.get("severity", "info")
    author = c.get("author", "agent")
    frame = c.get("frame", 0)
    tags = c.get("tags") or []
    tag_str = (" [" + ", ".join(tags) + "]") if tags else ""
    return f"#{c.get('id', '?')} {sev:<8} {author} @frame {frame}{tag_str}\n    {c.get('text', '')}"


def _run_cmd(cmd: str) -> str:
    """Run a shell command and return its stdout (for --watch narrator mode)."""
    import subprocess  # local import: only needed in watch mode

    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if proc.returncode != 0:
        err = proc.stderr.strip() or f"exit code {proc.returncode}"
        print(f"warning: --cmd failed: {err}", file=sys.stderr)
    return proc.stdout.strip()


def _resolve_text(text_arg: str | None) -> str:
    """Resolve --text, reading stdin when it is '-'."""
    if text_arg == "-":
        return sys.stdin.read().strip()
    return (text_arg or "").strip()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Post or read agent commentary on a running Tank World simulation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--url", default=DEFAULT_URL, help=f"Server base URL (default: {DEFAULT_URL})")
    p.add_argument("--world", default=None, help="World id (default: the server's default world)")
    p.add_argument("--text", default=None, help="Comment text (use '-' to read from stdin)")
    p.add_argument(
        "--author",
        default=os.getenv("TANK_AGENT") or "agent",
        help="Author name (default: $TANK_AGENT or 'agent')",
    )
    p.add_argument("--tags", default=None, help="Comma/space-separated tags")
    p.add_argument(
        "--severity",
        default="info",
        choices=VALID_SEVERITIES,
        help="Severity (default: info)",
    )
    p.add_argument(
        "--metric",
        action="append",
        dest="metrics",
        metavar="KEY=VALUE",
        help="Attach a metric (repeatable); numbers are parsed as numbers",
    )
    p.add_argument("--read", action="store_true", help="Read recent comments instead of posting")
    p.add_argument("--limit", type=int, default=None, help="Max comments for --read")
    p.add_argument("--since-id", type=int, default=None, help="Only comments newer than this id")
    p.add_argument("--watch", action="store_true", help="Loop forever (scripted narrator)")
    p.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL,
        help=f"Seconds between --watch iterations (default: {DEFAULT_INTERVAL:.0f})",
    )
    p.add_argument(
        "--cmd", default=None, help="In --watch mode, run this each interval and post its stdout"
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base_url = args.url.rstrip("/")

    # --- read mode -------------------------------------------------------
    if args.read:
        try:
            comments = read_comments(
                base_url, world_id=args.world, limit=args.limit, since_id=args.since_id
            )
        except (HTTPError, URLError) as e:
            print(f"error: could not reach {base_url}: {e}", file=sys.stderr)
            return 2
        if not comments:
            print("(no commentary yet)")
            return 0
        for c in comments:
            print(_format_comment(c))
        return 0

    metrics = _parse_metrics(args.metrics)
    tags = _parse_tags(args.tags)

    # --- watch / narrator mode ------------------------------------------
    if args.watch:
        if not args.cmd:
            print(
                "error: --watch needs --cmd (the command whose stdout becomes each comment).\n"
                "For an LLM-driven narrator that forms its own insights, use the /observe-sim "
                "skill instead.",
                file=sys.stderr,
            )
            return 2
        print(
            f"watching: posting `{args.cmd}` output to {base_url} every {args.interval:.0f}s "
            "(Ctrl-C to stop)",
            file=sys.stderr,
        )
        try:
            while True:
                text = _run_cmd(args.cmd)
                if text:
                    try:
                        c = post_comment(
                            base_url,
                            text,
                            world_id=args.world,
                            author=args.author,
                            tags=tags,
                            severity=args.severity,
                            metrics=metrics or None,
                        )
                        print(_format_comment(c))
                    except (HTTPError, URLError) as e:
                        print(f"warning: post failed: {e}", file=sys.stderr)
                else:
                    print("warning: --cmd produced no output; skipping", file=sys.stderr)
                time.sleep(max(1.0, args.interval))
        except KeyboardInterrupt:
            print("\nstopped.", file=sys.stderr)
            return 0

    # --- one-shot post mode ---------------------------------------------
    text = _resolve_text(args.text)
    if not text:
        print("error: --text is required (or pipe text and pass --text -)", file=sys.stderr)
        return 2

    try:
        comment = post_comment(
            base_url,
            text,
            world_id=args.world,
            author=args.author,
            tags=tags,
            severity=args.severity,
            metrics=metrics or None,
        )
    except HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read().decode("utf-8")).get("detail", "")
        except Exception:
            pass
        print(f"error: server returned {e.code}: {detail or e.reason}", file=sys.stderr)
        return 2
    except URLError as e:
        print(f"error: could not reach {base_url}: {e}", file=sys.stderr)
        return 2

    print(_format_comment(comment))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
