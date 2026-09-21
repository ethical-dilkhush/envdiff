from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, TextIO

ENV_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")

ANSI_COLORS = {
    "added": "\033[32m",
    "removed": "\033[31m",
    "changed": "\033[33m",
    "unchanged": "\033[37m",
    "reset": "\033[0m",
}


class EnvDiffError(Exception):
    pass


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ENV_LINE_RE.match(stripped)
        if not match:
            continue
        key = match.group(1)
        raw = match.group(2) or ""
        if len(raw) >= 2 and raw[0] in ('"', "'") and raw[-1] == raw[0]:
            raw = raw[1:-1]
        env[key] = raw
    return env


def parse_live_env() -> dict[str, str]:
    return dict(os.environ)


def diff_envs(old: dict[str, str], new: dict[str, str]) -> dict[str, Any]:
    old_keys = set(old)
    new_keys = set(new)
    added = {k: new[k] for k in sorted(new_keys - old_keys)}
    removed = {k: old[k] for k in sorted(old_keys - new_keys)}
    common = old_keys & new_keys
    changed = {
        k: {"old": old[k], "new": new[k]}
        for k in sorted(common)
        if old[k] != new[k]
    }
    unchanged = {k: new[k] for k in sorted(common) if old[k] == new[k]}
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
    }


def colorize(text: str, kind: str) -> str:
    return f"{ANSI_COLORS.get(kind, '')}{text}{ANSI_COLORS['reset']}"


def format_plain(report: dict[str, Any]) -> str:
    kinds = ["added", "removed", "changed", "unchanged"]
    out: list[str] = []
    for kind in kinds:
        items = report.get(kind, {})
        if not items:
            continue
        out.append(colorize(kind.upper(), kind) + ":")
        if kind == "changed":
            for k, v in items.items():
                out.append(f"  {k}: {v['old']} -> {v['new']}")
        else:
            for k, v in items.items():
                out.append(f"  {k}={v}")
        out.append("")
    if not out:
        return "No differences found.\n"
    return "\n".join(out) + "\n"


def format_markdown(report: dict[str, Any]) -> str:
    sections: list[str] = []
    for kind in ("added", "removed", "changed"):
        items = report.get(kind, {})
        if not items:
            continue
        sections.append(f"### {kind.capitalize()}\n")
        if kind in ("added", "removed"):
            sections.append("| Key | Value |")
            sections.append("|-----|-------|")
            for k, v in items.items():
                sections.append(f"| {k} | {v} |")
        else:
            sections.append("| Key | Old | New |")
            sections.append("|-----|-----|-----|")
            for k, v in items.items():
                sections.append(f"| {k} | {v['old']} | {v['new']} |")
        sections.append("")
    if not sections:
        return "No differences found.\n"
    return "\n".join(sections) + "\n"


def format_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2) + "\n"


def apply_only(report: dict[str, Any], only: str) -> dict[str, Any]:
    return {
        "added": report.get("added", {}) if only == "added" else {},
        "removed": report.get("removed", {}) if only == "removed" else {},
        "changed": report.get("changed", {}) if only == "changed" else {},
        "unchanged": report.get("unchanged", {}) if only == "unchanged" else {},
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envdiff",
        description="Diff environment variables across files or live process environments.",
    )
    parser.add_argument("old", nargs="?", default=None, help="Path to the old env source")
    parser.add_argument("new", nargs="?", default=None, help="Path to the new env source")
    parser.add_argument(
        "--live-old",
        action="store_true",
        help="Treat OLD as the current live process environment instead of a file.",
    )
    parser.add_argument(
        "--live-new",
        action="store_true",
        help="Treat NEW as the current live process environment instead of a file.",
    )
    parser.add_argument(
        "--format",
        choices=["plain", "markdown", "json"],
        default="plain",
        help="Output format (default: plain).",
    )
    parser.add_argument(
        "--only",
        choices=["added", "removed", "changed", "unchanged"],
        help="Show only changes of this kind.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color in plain output.",
    )
    return parser


def _resolve_source(path: str | None, live: bool) -> dict[str, str]:
    if live:
        return parse_live_env()
    if path is None:
        raise EnvDiffError("missing env source path")
    source = Path(path)
    if not source.exists():
        raise EnvDiffError(f"env file not found: {source}")
    return parse_env_file(source)


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None) -> int:
    out = sys.stdout if stdout is None else stdout
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.old is None and args.new is None and not args.live_old and not args.live_new:
        print("error: old and new sources are required unless --live-old/--live-new is used", file=sys.stderr)
        return 2

    try:
        old = _resolve_source(args.old, args.live_old)
        new = _resolve_source(args.new, args.live_new)
    except EnvDiffError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    report = diff_envs(old, new)
    if args.only:
        report = apply_only(report, args.only)

    if args.format == "json":
        output = format_json(report)
    elif args.format == "markdown":
        output = format_markdown(report)
    else:
        output = format_plain(report)
        if args.no_color:
            for kind in ANSI_COLORS:
                if kind != "reset":
                    output = output.replace(ANSI_COLORS[kind], "")
            output = output.replace(ANSI_COLORS["reset"], "")

    out.write(output)
    return 1 if any(report.get(k) for k in ("added", "removed", "changed")) else 0


if __name__ == "__main__":
    raise SystemExit(main())
