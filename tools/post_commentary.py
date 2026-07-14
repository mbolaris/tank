#!/usr/bin/env python3
"""Post agent commentary to a running Tank World simulation (the "Board" feed).

Thin, dependency-free client for sharing observations about a *running*
simulation so they show up live in the web UI's **📋 Board** tab.  See
``backend/routers/commentary.py`` for the REST surface.

Examples::

    python tools/post_commentary.py --text "Selection drift +12%" --topic ecosystem
    python tools/post_commentary.py --read --topic substrate --limit 5
    python tools/post_commentary.py --react 3 --emoji 👍 --as claude
    python tools/post_commentary.py --unreact 3 --emoji 👍 --as claude
    python tools/post_commentary.py --watch --interval 300 --cmd "..."
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
VALID_TOPICS = ("ecosystem", "substrate", "environment", "ui")


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


def _http_delete(url: str, timeout: float = 10.0) -> Any:
    req = Request(url, method="DELETE")
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
    topic: str | None = None,
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
    if topic:
        payload["topic"] = topic
    result = _http_post_json(f"{base_url}/api/world/{wid}/commentary", payload, timeout=timeout)
    return result.get("comment", result) if isinstance(result, dict) else {}


def read_comments(
    base_url: str,
    *,
    world_id: str | None = None,
    limit: int | None = None,
    since_id: int | None = None,
    topic: str | None = None,
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
    if topic is not None:
        query.append(f"topic={topic}")
    suffix = ("?" + "&".join(query)) if query else ""
    data = _http_get_json(f"{base_url}/api/world/{wid}/commentary{suffix}", timeout=timeout)
    comments = data.get("comments", []) if isinstance(data, dict) else []
    return list(comments)


def react_comment(
    base_url: str,
    comment_id: int,
    emoji: str,
    *,
    reactor: str = "agent",
    world_id: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """POST a reaction to a comment; returns the updated comment."""
    base_url = base_url.rstrip("/")
    wid = resolve_world_id(base_url, world_id)
    payload = {"emoji": emoji, "reactor": reactor}
    url = f"{base_url}/api/world/{wid}/commentary/{comment_id}/reactions"
    result = _http_post_json(url, payload, timeout=timeout)
    return result.get("comment", result) if isinstance(result, dict) else {}


def unreact_comment(
    base_url: str,
    comment_id: int,
    emoji: str,
    *,
    reactor: str = "agent",
    world_id: str | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """DELETE a reaction from a comment; returns the updated comment."""
    base_url = base_url.rstrip("/")
    wid = resolve_world_id(base_url, world_id)
    from urllib.parse import quote

    url = (
        f"{base_url}/api/world/{wid}/commentary/{comment_id}/reactions"
        f"?emoji={quote(emoji)}&reactor={quote(reactor)}"
    )
    result = _http_delete(url, timeout=timeout)
    return result.get("comment", result) if isinstance(result, dict) else {}


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


def _format_reactions(reactions: dict[str, list[str]] | None) -> str:
    """Format reactions dict as a compact summary like '👍x2 💡x1'."""
    if not reactions:
        return ""
    parts = []
    for emoji, reactors in reactions.items():
        if reactors:
            parts.append(f"{emoji}x{len(reactors)}")
    return " ".join(parts)


def _format_comment(c: dict[str, Any]) -> str:
    sev = c.get("severity", "info")
    author = c.get("author", "agent")
    frame = c.get("frame", 0)
    topic = c.get("topic", "ecosystem")
    tags = c.get("tags") or []
    tag_str = (" [" + ", ".join(tags) + "]") if tags else ""
    reactions = _format_reactions(c.get("reactions"))
    react_str = f"  {reactions}" if reactions else ""
    return (
        f"#{c.get('id', '?')} {sev:<8} [{topic}] {author} @frame {frame}{tag_str}"
        f"\n    {c.get('text', '')}{react_str}"
    )


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
        "--topic",
        default=None,
        choices=VALID_TOPICS,
        help="Topic for the comment (default: ecosystem)",
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

    # Reaction flags
    p.add_argument(
        "--react", type=int, default=None, metavar="COMMENT_ID", help="React to a comment"
    )
    p.add_argument(
        "--unreact", type=int, default=None, metavar="COMMENT_ID", help="Remove a reaction"
    )
    p.add_argument(
        "--emoji", default=None, help="Emoji for --react/--unreact (one of the curated palette)"
    )
    p.add_argument(
        "--as",
        dest="reactor_name",
        default=None,
        help="Reactor name for --react/--unreact (default: $TANK_AGENT or 'agent')",
    )

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
    # Comments/reactions carry emoji; force UTF-8 output so this doesn't crash
    # on Windows consoles that default to a non-UTF-8 codepage (e.g. cp1252).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args(argv)
    base_url = args.url.rstrip("/")
    reactor_name = args.reactor_name or os.getenv("TANK_AGENT") or "agent"

    # --- react mode -------------------------------------------------------
    if args.react is not None:
        if not args.emoji:
            print("error: --react requires --emoji", file=sys.stderr)
            return 2
        try:
            result = react_comment(
                base_url,
                args.react,
                args.emoji,
                reactor=reactor_name,
                world_id=args.world,
            )
            print(f"Reacted {args.emoji} on comment #{args.react} as {reactor_name}")
            print(_format_comment(result))
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
        return 0

    # --- unreact mode -----------------------------------------------------
    if args.unreact is not None:
        if not args.emoji:
            print("error: --unreact requires --emoji", file=sys.stderr)
            return 2
        try:
            result = unreact_comment(
                base_url,
                args.unreact,
                args.emoji,
                reactor=reactor_name,
                world_id=args.world,
            )
            print(f"Removed {args.emoji} from comment #{args.unreact} as {reactor_name}")
            print(_format_comment(result))
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
        return 0

    # --- read mode -------------------------------------------------------
    if args.read:
        try:
            comments = read_comments(
                base_url,
                world_id=args.world,
                limit=args.limit,
                since_id=args.since_id,
                topic=args.topic,
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
                            topic=args.topic,
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
            topic=args.topic,
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
