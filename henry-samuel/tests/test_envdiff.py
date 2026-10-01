"""Tests for envdiff — env file comparison CLI."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from envdiff import diff_envs, format_json, format_text, main, parse_env_file

# ---------------------------------------------------------------------------
# parse_env_file
# ---------------------------------------------------------------------------

class TestParseEnvFile:
    def test_simple_key_value(self, tmp_path):
        f = tmp_path / "test.env"
        f.write_text("FOO=bar\n")
        assert parse_env_file(str(f)) == {"FOO": "bar"}

    def test_multiple_keys(self, tmp_path):
        f = tmp_path / "test.env"
        f.write_text("FOO=bar\nBAZ=qux\n")
        assert parse_env_file(str(f)) == {"FOO": "bar", "BAZ": "qux"}

    def test_empty_value(self, tmp_path):
        f = tmp_path / "test.env"
        f.write_text("EMPTY=\n")
        assert parse_env_file(str(f)) == {"EMPTY": ""}

    def test_quoted_values(self, tmp_path):
        f = tmp_path / "test.env"
        f.write_text('FOO="hello world"\nBAR=\'single quotes\'\n')
        result = parse_env_file(str(f))
        assert result["FOO"] == "hello world"
        assert result["BAR"] == "single quotes"

    def test_comments_ignored(self, tmp_path):
        f = tmp_path / "test.env"
        f.write_text("# comment\nFOO=bar\n# another\nBAZ=qux\n")
        assert parse_env_file(str(f)) == {"FOO": "bar", "BAZ": "qux"}

    def test_blank_lines_ignored(self, tmp_path):
        f = tmp_path / "test.env"
        f.write_text("\n\nFOO=bar\n\n\nBAZ=qux\n")
        assert parse_env_file(str(f)) == {"FOO": "bar", "BAZ": "qux"}

    def test_export_prefix(self, tmp_path):
        f = tmp_path / "test.env"
        f.write_text("export FOO=bar\nexport BAZ=qux\n")
        assert parse_env_file(str(f)) == {"FOO": "bar", "BAZ": "qux"}

    def test_missing_file_exit(self, tmp_path):
        with pytest.raises(SystemExit) as exc:
            parse_env_file(str(tmp_path / "nonexistent.env"))
        assert exc.value.code == 2

    def test_preserves_order(self, tmp_path):
        f = tmp_path / "test.env"
        f.write_text("ZZZ=last\nAAA=first\nMMM=middle\n")
        keys = list(parse_env_file(str(f)).keys())
        assert keys == ["ZZZ", "AAA", "MMM"]


# ---------------------------------------------------------------------------
# diff_envs
# ---------------------------------------------------------------------------

class TestDiffEnvs:
    def test_identical(self):
        left = {"FOO": "bar", "BAZ": "qux"}
        right = {"FOO": "bar", "BAZ": "qux"}
        added, removed, changed = diff_envs(left, right)
        assert added == []
        assert removed == []
        assert changed == []

    def test_added_keys(self):
        left = {"FOO": "bar"}
        right = {"FOO": "bar", "BAZ": "qux"}
        added, removed, changed = diff_envs(left, right)
        assert len(added) == 1
        assert added[0][0] == "BAZ"
        assert added[0][2] == "qux"
        assert removed == []
        assert changed == []

    def test_removed_keys(self):
        left = {"FOO": "bar", "BAZ": "qux"}
        right = {"FOO": "bar"}
        added, removed, changed = diff_envs(left, right)
        assert len(removed) == 1
        assert removed[0][0] == "BAZ"
        assert removed[0][1] == "qux"
        assert added == []
        assert changed == []

    def test_changed_keys(self):
        left = {"FOO": "bar", "BAZ": "qux"}
        right = {"FOO": "bar", "BAZ": "newqux"}
        added, removed, changed = diff_envs(left, right)
        assert len(changed) == 1
        assert changed[0][0] == "BAZ"
        assert changed[0][1] == "qux"
        assert changed[0][2] == "newqux"
        assert added == []
        assert removed == []

    def test_all_three(self):
        left = {"OLD": "gone", "UNCHANGED": "same", "CHANGED": "old"}
        right = {"UNCHANGED": "same", "CHANGED": "new", "NEW": "fresh"}
        added, removed, changed = diff_envs(left, right)
        assert len(added) == 1 and added[0][0] == "NEW"
        assert len(removed) == 1 and removed[0][0] == "OLD"
        assert len(changed) == 1 and changed[0][0] == "CHANGED"

    def test_sorted_output(self):
        left = {"C": "1", "A": "2"}
        right = {"C": "1", "A": "3", "B": "4"}
        added, removed, changed = diff_envs(left, right)
        assert [k for k, _, _ in added] == ["B"]
        assert [k for k, _, _, _ in changed] == ["A"]


# ---------------------------------------------------------------------------
# format_text
# ---------------------------------------------------------------------------

class TestFormatText:
    def test_no_diffs(self):
        result = format_text([], [], [])
        assert result.strip() == "No differences."

    def test_added_only(self):
        result = format_text([("NEW", "", "value")], [], [])
        assert "--- ADDED ---" in result
        assert "+ NEW=value" in result

    def test_removed_only(self):
        result = format_text([], [("OLD", "val", "")], [])
        assert "--- REMOVED ---" in result
        assert "- OLD=val" in result

    def test_changed_only(self):
        result = format_text([], [], [("KEY", "old", "new", "")])
        assert "--- CHANGED ---" in result
        assert "~ KEY" in result
        assert "  - old" in result
        assert "  + new" in result

    def test_all_three(self):
        result = format_text(
            [("ADDED", "", "v")], [("REMOVED", "v", "")], [("CHANGED", "a", "b", "")]
        )
        assert "--- ADDED ---" in result
        assert "--- REMOVED ---" in result
        assert "--- CHANGED ---" in result


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------

class TestFormatJson:
    def test_no_diffs(self):
        result = format_json([], [], [])
        parsed = json.loads(result)
        assert parsed == {"added": [], "removed": [], "changed": []}

    def test_with_diffs(self):
        result = format_json(
            [("ADDED", "", "v")], [("REMOVED", "v", "")], [("CHANGED", "a", "b", "")]
        )
        parsed = json.loads(result)
        assert len(parsed["added"]) == 1
        assert parsed["added"][0]["key"] == "ADDED"
        assert len(parsed["removed"]) == 1
        assert len(parsed["changed"]) == 1


# ---------------------------------------------------------------------------
# CLI main — positive probes
# ---------------------------------------------------------------------------

class TestMainPositive:
    def test_two_files_identical(self, tmp_path):
        f1 = tmp_path / "a.env"
        f2 = tmp_path / "b.env"
        f1.write_text("FOO=bar\n")
        f2.write_text("FOO=bar\n")
        rc = main([str(f1), str(f2)])
        assert rc == 0

    def test_two_files_different(self, tmp_path):
        f1 = tmp_path / "a.env"
        f2 = tmp_path / "b.env"
        f1.write_text("FOO=bar\n")
        f2.write_text("FOO=baz\n")
        rc = main([str(f1), str(f2)])
        assert rc == 1

    def test_json_output(self, tmp_path, capsys):
        f1 = tmp_path / "a.env"
        f2 = tmp_path / "b.env"
        f1.write_text("FOO=bar\n")
        f2.write_text("FOO=baz\n")
        rc = main(["--json", str(f1), str(f2)])
        assert rc == 1
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "changed" in parsed

    def test_text_output(self, tmp_path, capsys):
        f1 = tmp_path / "a.env"
        f2 = tmp_path / "b.env"
        f1.write_text("FOO=bar\n")
        f2.write_text("BAZ=qux\n")
        rc = main([str(f1), str(f2)])
        assert rc == 1
        out = capsys.readouterr().out
        assert "--- ADDED ---" in out
        assert "--- REMOVED ---" in out

    def test_no_args_prints_help(self, capsys):
        rc = main([])
        assert rc == 0
        out = capsys.readouterr().out
        assert "usage" in out.lower() or "envdiff" in out

    def test_current_env_vs_file(self, tmp_path, capsys):
        f = tmp_path / "test.env"
        f.write_text(f"HOME={os.environ.get('HOME', '')}\n")
        # We can't assert exact HOME value cross-platform, but we can assert
        # the command runs without error
        rc = main(["--current-env", str(f)])
        assert rc in (0, 1)  # 0 if no diff, 1 if diff (HOME likely differs)

    def test_left_file_missing(self, tmp_path):
        f = tmp_path / "nonexistent.env"
        with pytest.raises(SystemExit) as exc:
            main([str(f), str(tmp_path / "other.env")])
        assert exc.value.code == 2


# ---------------------------------------------------------------------------
# CLI main — edge probes
# ---------------------------------------------------------------------------

class TestMainEdge:
    def test_empty_files(self, tmp_path):
        f1 = tmp_path / "a.env"
        f2 = tmp_path / "b.env"
        f1.write_text("")
        f2.write_text("")
        rc = main([str(f1), str(f2)])
        assert rc == 0

    def test_one_file_empty(self, tmp_path, capsys):
        f1 = tmp_path / "a.env"
        f2 = tmp_path / "b.env"
        f1.write_text("")
        f2.write_text("FOO=bar\n")
        rc = main([str(f1), str(f2)])
        assert rc == 1
        out = capsys.readouterr().out
        assert "--- ADDED ---" in out

    def test_comment_only_files(self, tmp_path):
        f1 = tmp_path / "a.env"
        f2 = tmp_path / "b.env"
        f1.write_text("# just a comment\n")
        f2.write_text("# another comment\n")
        rc = main([str(f1), str(f2)])
        assert rc == 0

    def test_export_prefix_in_file(self, tmp_path, capsys):
        f1 = tmp_path / "a.env"
        f2 = tmp_path / "b.env"
        f1.write_text("export FOO=bar\nexport BAZ=qux\n")
        f2.write_text("FOO=bar\nBAZ=qux\n")
        rc = main([str(f1), str(f2)])
        assert rc == 0  # identical after parsing

    def test_json_shorthand(self, tmp_path, capsys):
        f1 = tmp_path / "a.env"
        f2 = tmp_path / "b.env"
        f1.write_text("FOO=bar\n")
        f2.write_text("FOO=baz\n")
        main(["--json", str(f1), str(f2)])
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "changed" in parsed

    def test_right_file_missing(self, tmp_path):
        f = tmp_path / "nonexistent.env"
        with pytest.raises(SystemExit) as exc:
            main([str(tmp_path / "other.env"), str(f)])
        assert exc.value.code == 2
