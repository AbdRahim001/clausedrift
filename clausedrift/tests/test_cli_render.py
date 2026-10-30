"""Tests for report rendering and the CLI."""

from __future__ import annotations

import json

import pytest

from clausedrift import compare
from clausedrift.cli import main
from clausedrift.render import render_json, render_markdown, render_text

OLD = "The fee is $50 per month. Payment is due on the first day."
NEW = "The fee is $75 per month. Payment is due within 30 days. Late fees apply."


@pytest.fixture()
def report():
    return compare(OLD, NEW)


class TestRenderJson:
    def test_valid_json(self, report):
        payload = json.loads(render_json(report))
        assert payload["drift_score"] == report.drift_score

    def test_includes_every_change(self, report):
        payload = json.loads(render_json(report))
        assert len(payload["changes"]) == len(report.changes)


class TestRenderMarkdown:
    def test_has_heading_and_table(self, report):
        out = render_markdown(report)
        assert "# ClauseDrift report" in out
        assert "| Metric | Value |" in out

    def test_lists_changed_rows(self, report):
        out = render_markdown(report)
        assert "Edited" in out or "Added" in out

    def test_no_differences_message(self):
        out = render_markdown(compare("Same.", "Same."))
        assert "No differences found" in out


class TestRenderText:
    def test_plain_when_colour_disabled(self, report):
        out = render_text(report, colour=False)
        assert "\033[" not in out

    def test_shows_drift_score(self, report):
        assert "drift score" in render_text(report, colour=False)


class TestCli:
    def _write(self, tmp_path, name, content):
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_exit_zero_on_success(self, tmp_path, capsys):
        old = self._write(tmp_path, "old.txt", OLD)
        new = self._write(tmp_path, "new.txt", NEW)
        assert main([str(old), str(new)]) == 0
        assert "drift score" in capsys.readouterr().out

    def test_missing_file_returns_two(self, tmp_path):
        path = self._write(tmp_path, "old.txt", OLD)
        assert main([str(path), str(tmp_path / "nope.txt")]) == 2

    def test_json_format(self, tmp_path, capsys):
        old = self._write(tmp_path, "old.txt", OLD)
        new = self._write(tmp_path, "new.txt", NEW)
        main([str(old), str(new), "-f", "json"])
        assert "drift_score" in json.loads(capsys.readouterr().out)

    def test_quiet_prints_only_score(self, tmp_path, capsys):
        old = self._write(tmp_path, "old.txt", OLD)
        new = self._write(tmp_path, "new.txt", NEW)
        main([str(old), str(new), "-q"])
        out = capsys.readouterr().out.strip()
        assert float(out) >= 0.0

    def test_output_file(self, tmp_path):
        old = self._write(tmp_path, "old.txt", OLD)
        new = self._write(tmp_path, "new.txt", NEW)
        target = tmp_path / "report.md"
        main([str(old), str(new), "-f", "markdown", "-o", str(target)])
        assert target.exists() and "# ClauseDrift report" in target.read_text()

    def test_fail_over_gate_trips(self, tmp_path):
        old = self._write(tmp_path, "old.txt", OLD)
        new = self._write(tmp_path, "new.txt", NEW)
        assert main([str(old), str(new), "-q", "--fail-over", "0"]) == 1

    def test_fail_over_gate_passes(self, tmp_path):
        old = self._write(tmp_path, "a.txt", OLD)
        new = self._write(tmp_path, "b.txt", OLD)
        assert main([str(old), str(new), "-q", "--fail-over", "5"]) == 0
