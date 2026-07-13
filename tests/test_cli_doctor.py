"""`newrepo --doctor` のユニットテスト。"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from newrepo import preflight
from newrepo.cli import app
from newrepo.preflight import CheckResult

runner = CliRunner()


def test_doctor_reports_success_when_all_checks_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        preflight,
        "run_checks",
        lambda: [
            CheckResult("git is installed", True),
            CheckResult("gh is installed", True),
            CheckResult("gh is authenticated", True),
        ],
    )

    result = runner.invoke(app, ["--doctor"])

    assert result.exit_code == 0
    assert "✓ git is installed" in result.stdout
    assert "All checks passed" in result.stdout


def test_doctor_reports_failure_with_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        preflight,
        "run_checks",
        lambda: [
            CheckResult("git is installed", True),
            CheckResult(
                "gh is installed",
                False,
                "https://cli.github.com/ からインストールしてください。",
            ),
            CheckResult(
                "gh is authenticated",
                False,
                "gh コマンドが見つからないため確認できません。",
            ),
        ],
    )

    result = runner.invoke(app, ["--doctor"])

    assert result.exit_code == 1
    assert "✗ gh is installed" in result.stdout
    assert "https://cli.github.com/" in result.stdout
    assert "Some checks failed" in result.stdout


def test_missing_name_without_doctor_is_an_error() -> None:
    result = runner.invoke(app, [])

    assert result.exit_code == 1
    assert "NAME を指定してください" in result.output
