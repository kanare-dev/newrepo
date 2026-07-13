"""`newrepo --version` のユニットテスト。"""

from __future__ import annotations

from importlib.metadata import version as package_version

from typer.testing import CliRunner

from newrepo.cli import app

runner = CliRunner()


def test_version_prints_installed_package_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"newrepo {package_version('newrepo')}"
