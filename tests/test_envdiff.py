from __future__ import annotations

import io
import os
from pathlib import Path

import pytest

import envdiff


def test_parse_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("APP=1\nBANNED=\"2\"\n# comment\nEMPTY=\n", encoding="utf-8")
    parsed = envdiff.parse_env_file(env_file)
    assert parsed == {"APP": "1", "BANNED": "2", "EMPTY": ""}


def test_diff_envs_report_changes() -> None:
    report = envdiff.diff_envs({"A": "1", "B": "2"}, {"A": "1", "B": "3", "C": "9"})
    assert report["added"] == {"C": "9"}
    assert report["removed"] == {}
    assert report["changed"] == {"B": {"old": "2", "new": "3"}}
    assert report["unchanged"] == {"A": "1"}


def test_diff_envs_no_changes_returns_zero_exit_code() -> None:
    rc = envdiff.main(
        [
            "tests/fixtures/old.env",
            "tests/fixtures/old.env",
            "--no-color",
        ],
        stdout=io.StringIO(),
    )
    assert rc == 0


def test_main_reports_difference_exit_code_and_plain_output() -> None:
    stdout = io.StringIO()
    rc = envdiff.main(
        [
            "tests/fixtures/old.env",
            "tests/fixtures/new.env",
            "--no-color",
        ],
        stdout=stdout,
    )
    assert rc == 1
    output = stdout.getvalue()
    assert "ADDED:" in output
    assert "REMOVED:" in output
    assert "CHANGED:" in output


def test_main_markdown_format_contains_tables() -> None:
    stdout = io.StringIO()
    envdiff.main(
        [
            "tests/fixtures/old.env",
            "tests/fixtures/new.env",
            "--format", "markdown",
        ],
        stdout=stdout,
    )
    output = stdout.getvalue()
    assert "| Key | Value |" in output
    assert "| Key | Old | New |" in output


def test_main_json_format_parses_as_json() -> None:
    stdout = io.StringIO()
    rc = envdiff.main(
        [
            "tests/fixtures/old.env",
            "tests/fixtures/new.env",
            "--format", "json",
        ],
        stdout=stdout,
    )
    assert rc == 1
    parsed = __import__("json").loads(stdout.getvalue())
    assert "added" in parsed and "removed" in parsed


def test_main_missing_file_returns_two() -> None:
    rc = envdiff.main(
        [
            "tests/fixtures/missing.env",
            "tests/fixtures/new.env",
        ],
        stdout=io.StringIO(),
    )
    assert rc == 2


def test_only_added_filters_output() -> None:
    stdout = io.StringIO()
    envdiff.main(
        [
            "tests/fixtures/old.env",
            "tests/fixtures/new.env",
            "--only", "added",
            "--no-color",
        ],
        stdout=stdout,
    )
    output = stdout.getvalue()
    assert "ADDED:" in output
    assert "REMOVED:" not in output
    assert "CHANGED:" not in output


def test_no_color_strips_ansi() -> None:
    stdout = io.StringIO()
    envdiff.main(
        [
            "tests/fixtures/old.env",
            "tests/fixtures/new.env",
            "--no-color",
        ],
        stdout=stdout,
    )
    output = stdout.getvalue()
    assert "\033[" not in output
    assert "ADDED:" in output
