"""envdiff — compare two .env files or environment snapshots.

Report added, removed, and changed variables with clear diff-style output.
Supports JSON and plain-text output formats, and can read from files or
from the current process environment for snapshot comparison.

Usage:
    envdiff .env.base .env.current
    envdiff --format json .env.base .env.current
    envdiff --current-env .env.saved
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence


def parse_env_file(path: str) -> dict[str, str]:
    """Parse a .env-style file into an ordered dict of key=value pairs.

    Handles:
    - KEY=VALUE (quote-aware: strips surrounding single/double quotes)
    - Comments (# to EOL)
    - Blank lines
    - Export prefix (export KEY=VALUE)
    - Variables without values (KEY= or KEY)

    Returns a dict preserving the order of first appearance.
    """
    result: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for lineno, raw_line in enumerate(fh, 1):
                line = raw_line.strip()

                # Blank or comment
                if not line or line.startswith("#"):
                    continue

                # Strip export prefix
                if line.startswith("export "):
                    line = line[len("export ") :]

                # Find first = (quote-aware: don't split inside quotes)
                if "=" not in line:
                    continue

                key, _, value = line.partition("=")
                key = key.strip()

                if not key:
                    continue

                # Unquote value if quoted
                value = value.strip()
                if len(value) >= 2:
                    if (value[0] == '"' and value[-1] == '"') or (
                        value[0] == "'" and value[-1] == "'"
                    ):
                        value = value[1:-1]

                result[key] = value
    except FileNotFoundError:
        sys.stderr.write(f"envdiff: file not found: {path}\n")
        sys.exit(2)
    except OSError as e:
        sys.stderr.write(f"envdiff: cannot read {path}: {e}\n")
        sys.exit(2)

    return result


def get_current_env() -> dict[str, str]:
    """Snapshot of the current process environment (os.environ)."""
    return dict(os.environ)


def diff_envs(
    left: dict[str, str], right: dict[str, str]
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]], list[tuple[str, str, str, str]]]:
    """Compare two env dicts.

    Returns (added, removed, changed) where:
    - added: list of (key, _, new_value) — keys in right not in left
    - removed: list of (key, old_value, _) — keys in left not in right
    - changed: list of (key, old_value, new_value, _) — keys in both with different values
    """
    left_keys = set(left)
    right_keys = set(right)

    added_keys = right_keys - left_keys
    removed_keys = left_keys - right_keys
    common_keys = left_keys & right_keys

    added: list[tuple[str, str, str]] = []
    removed: list[tuple[str, str, str]] = []
    changed: list[tuple[str, str, str, str]] = []

    for key in sorted(added_keys):
        added.append((key, "", right[key]))

    for key in sorted(removed_keys):
        removed.append((key, left[key], ""))

    for key in sorted(common_keys):
        if left[key] != right[key]:
            changed.append((key, left[key], right[key], ""))

    return added, removed, changed


def format_text(
    added: list[tuple[str, str, str]],
    removed: list[tuple[str, str, str]],
    changed: list[tuple[str, str, str, str]],
) -> str:
    """Plain-text diff output."""
    lines: list[str] = []

    if added:
        lines.append("--- ADDED ---")
        for key, _, new_value in added:
            lines.append(f"+ {key}={new_value}")

    if removed:
        lines.append("--- REMOVED ---")
        for key, old_value, _ in removed:
            lines.append(f"- {key}={old_value}")

    if changed:
        lines.append("--- CHANGED ---")
        for key, old_value, new_value, _ in changed:
            lines.append(f"~ {key}")
            lines.append(f"  - {old_value}")
            lines.append(f"  + {new_value}")

    if not added and not removed and not changed:
        lines.append("No differences.")

    return "\n".join(lines) + "\n"


def format_json(
    added: list[tuple[str, str, str]],
    removed: list[tuple[str, str, str]],
    changed: list[tuple[str, str, str, str]],
) -> str:
    """JSON diff output."""
    result: dict[str, object] = {
        "added": [{"key": k, "value": v} for k, _, v in added],
        "removed": [{"key": k, "value": v} for k, v, _ in removed],
        "changed": [{"key": k, "old": o, "new": n} for k, o, n, _ in changed],
    }
    return json.dumps(result, indent=2) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="envdiff",
        description="Compare two .env files or environment snapshots.",
    )
    parser.add_argument(
        "left",
        nargs="?",
        help="Left-side file path (or omit with --current-env for right-side only)",
    )
    parser.add_argument(
        "right",
        nargs="?",
        help="Right-side file path",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--current-env",
        action="store_true",
        help="Use current process environment as the left side",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Shorthand for --format json",
    )

    args = parser.parse_args(argv)

    # --json overrides --format
    if args.json:
        args.format = "json"  # type: ignore[assignment]

    # Determine left side
    if args.current_env:
        left = get_current_env()
        left_source = "current-env"
    elif args.left:
        left = parse_env_file(args.left)
        left_source = args.left
    else:
        # No left side provided — print help and exit
        parser.print_help()
        return 0

    # Determine right side
    if args.right:
        right = parse_env_file(args.right)
        right_source = args.right
    elif args.current_env:
        right = get_current_env()
        right_source = "current-env"
    else:
        # Only left side — compare against empty
        right = {}
        right_source = "(empty)"

    added, removed, changed = diff_envs(left, right)

    if args.format == "json":
        sys.stdout.write(format_json(added, removed, changed))
    else:
        # Text mode: add header
        header = f"envdiff: {left_source} -> {right_source}\n"
        sys.stdout.write(header)
        sys.stdout.write(format_text(added, removed, changed))

    # Exit code: 0 if no differences, 1 if differences found
    if added or removed or changed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
