#!/usr/bin/env python3
"""Render a static longitudinal report from ``skill_history.jsonl``.

Examples:
    python tools/skill_report.py
    python tools/skill_report.py --format html --out skill_report.html
    python tools/skill_report.py --format json
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.research.skill_ledger import load_skill_history


def _group_records(records: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        key = (str(record["domain"]), str(record["benchmark_id"]))
        grouped[key].append(record)
    for values in grouped.values():
        values.sort(key=lambda item: float(item.get("timestamp", 0)))
    return dict(sorted(grouped.items()))


def summarize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one current-versus-first row per domain and benchmark."""
    rows: list[dict[str, Any]] = []
    for (domain, benchmark_id), values in _group_records(records).items():
        first = values[0]
        latest = values[-1]
        rows.append(
            {
                "domain": domain,
                "benchmark_id": benchmark_id,
                "skill_index": float(latest["skill_index"]),
                "change": float(latest["skill_index"]) - float(first["skill_index"]),
                "observations": len(values),
                "commits": len({value.get("git_sha") for value in values}),
                "config_hashes": len({value.get("config_hash") for value in values}),
                "last_timestamp": latest.get("timestamp"),
                "rungs": [
                    {
                        "rung": value.get("rung", value.get("rung_id")),
                        "rung_id": value.get("rung_id"),
                        "metric": value.get("metric"),
                        "beaten": value.get("beaten", False),
                    }
                    for value in values
                    if value.get("timestamp") == latest.get("timestamp")
                ],
            }
        )
    return rows


def render_text(rows: list[dict[str, Any]]) -> str:
    """Render a concise terminal summary."""
    if not rows:
        return "No skill history records found."
    lines = ["SKILL HISTORY (frozen-ruler longitudinal report)", "=" * 72]
    for row in rows:
        lines.append(
            f"{row['domain']:<10} {row['benchmark_id']:<30} "
            f"skill={row['skill_index']:7.2f}  change={row['change']:+7.2f}  "
            f"observations={row['observations']}  configs={row['config_hashes']}"
        )
        for rung in row["rungs"]:
            status = "beat" if rung["beaten"] else "----"
            lines.append(
                f"  {rung['rung']:<4} {rung['rung_id']:<24} {status} metric={rung['metric']}"
            )
    return "\n".join(lines)


def render_html(rows: list[dict[str, Any]], *, source: str) -> str:
    """Render a dependency-free static HTML report."""
    cards: list[str] = []
    for row in rows:
        index = float(row["skill_index"])
        width = max(0.0, min(100.0, index))
        rungs = "".join(
            f"<li><b>{html.escape(str(rung['rung']))}</b> "
            f"{html.escape(str(rung['rung_id']))}: "
            f"<span class={'beat' if rung['beaten'] else 'pending'}>"
            f"{'beaten' if rung['beaten'] else 'not yet'}</span>"
            f" (metric {html.escape(str(rung['metric']))})</li>"
            for rung in row["rungs"]
        )
        cards.append(
            "<section class='card'>"
            f"<h2>{html.escape(row['domain'])} <small>{html.escape(row['benchmark_id'])}</small></h2>"
            f"<div class='index'><div class='track'><div class='fill' style='width:{width:.2f}%'></div></div>"
            f"<strong>{index:.2f}</strong><span>/ 100</span></div>"
            f"<p>Change: <b>{row['change']:+.2f}</b> · {row['observations']} observations · "
            f"{row['config_hashes']} config hash(es)</p><ul>{rungs}</ul></section>"
        )
    body = "".join(cards) or "<p>No skill history records found.</p>"
    return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><title>Tank World Skill History</title>
<style>body{{font:15px system-ui;background:#0f172a;color:#e2e8f0;max-width:960px;margin:32px auto;padding:0 20px}}
.card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:18px;margin:16px 0}}
h1{{color:#93c5fd}}h2{{margin:0 0 12px}}small{{color:#94a3b8;font-size:12px;font-weight:400}}
.index{{display:flex;align-items:center;gap:10px}}.track{{height:10px;background:#0f172a;border-radius:6px;flex:1}}
.fill{{height:100%;background:#22c55e;border-radius:6px}}.index strong{{font-size:24px;color:#86efac}}
.index span,p,li{{color:#94a3b8}}li{{margin:5px 0}}.beat{{color:#86efac}}.pending{{color:#fbbf24}}
</style></head><body><h1>Tank World Skill History</h1>
<p>Append-only frozen-ruler observations from <code>{html.escape(source)}</code>.</p>{body}
</body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "history", nargs="?", default=str(ROOT / "research" / "skill_history.jsonl")
    )
    parser.add_argument("--format", choices=("text", "json", "html"), default="text")
    parser.add_argument("--out", help="Write the rendered report to a file")
    args = parser.parse_args()

    records = load_skill_history(args.history)
    rows = summarize(records)
    if args.format == "text":
        rendered = render_text(rows)
    elif args.format == "json":
        rendered = json.dumps({"source": args.history, "rows": rows}, indent=2)
    else:
        rendered = render_html(rows, source=args.history)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
