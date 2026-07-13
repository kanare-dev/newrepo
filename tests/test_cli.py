"""CLI 全体（サブコマンド dispatch・doctor・バリデーション）のユニットテスト。"""

from __future__ import annotations

from pathlib import Path

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

    result = runner.invoke(app, ["doctor"])

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

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 1
    assert "✗ gh is installed" in result.stdout
    assert "https://cli.github.com/" in result.stdout
    assert "Some checks failed" in result.stdout


def test_bare_invocation_shows_help() -> None:
    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "create" in result.output
    assert "doctor" in result.output
    assert "rename" in result.output
    assert "delete" in result.output


def test_create_without_name_is_an_error() -> None:
    result = runner.invoke(app, ["create"])

    assert result.exit_code != 0


def test_rename_without_new_name_is_an_error() -> None:
    result = runner.invoke(app, ["rename", "my-project"])

    assert result.exit_code != 0


def test_delete_without_name_is_an_error() -> None:
    result = runner.invoke(app, ["delete"])

    assert result.exit_code != 0


def test_rename_dispatches_name_and_new_name_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`newrepo rename NAME NEW_NAME` の引数順が入れ替わっていないことを確認する。"""
    from newrepo import local_repo

    target = tmp_path / "old-name"
    (target / ".git").mkdir(parents=True)

    monkeypatch.setattr(preflight, "run_all", lambda: None)
    monkeypatch.setattr(
        "newrepo.cli.github_repo.get_remote_origin_url",
        lambda path: "https://github.com/you/old-name.git",
    )
    renamed_to: list[str] = []
    monkeypatch.setattr(
        "newrepo.cli.github_repo.rename_repo_on_github",
        lambda path, new_name: renamed_to.append(new_name),
    )
    monkeypatch.setattr(
        "newrepo.cli.github_repo.update_remote_url_after_rename", lambda path, new_name: None
    )
    monkeypatch.setattr(
        "newrepo.cli.github_repo.get_repo_url",
        lambda path: "https://github.com/you/new-name",
    )
    monkeypatch.setattr(local_repo, "rename_directory", lambda old, new: None)

    result = runner.invoke(
        app, ["rename", "old-name", "new-name", "--directory", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert renamed_to == ["new-name"]
    assert "Repository renamed successfully" in result.output


def _stub_delete_preconditions(monkeypatch: pytest.MonkeyPatch) -> None:
    from newrepo import local_repo

    monkeypatch.setattr(preflight, "run_all", lambda: None)
    monkeypatch.setattr(local_repo, "check_directory_exists", lambda path: None)
    monkeypatch.setattr(local_repo, "check_is_git_repo", lambda path: None)
    monkeypatch.setattr(
        "newrepo.cli.github_repo.get_remote_origin_url",
        lambda path: "https://github.com/you/my-project.git",
    )


def test_delete_aborts_when_confirmation_name_does_not_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_delete_preconditions(monkeypatch)
    deleted_on_github = []
    monkeypatch.setattr(
        "newrepo.cli.github_repo.delete_repo_on_github",
        lambda path: deleted_on_github.append(path),
    )

    result = runner.invoke(
        app,
        ["delete", "my-project", "--directory", str(tmp_path)],
        input="wrong-name\n",
    )

    assert result.exit_code == 1
    assert "一致しないため" in result.output
    assert deleted_on_github == []


def test_delete_proceeds_when_confirmation_name_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from newrepo import local_repo

    _stub_delete_preconditions(monkeypatch)
    deleted_on_github = []
    deleted_locally = []
    monkeypatch.setattr(
        "newrepo.cli.github_repo.delete_repo_on_github",
        lambda path: deleted_on_github.append(path),
    )
    monkeypatch.setattr(
        local_repo, "delete_directory", lambda path: deleted_locally.append(path)
    )

    result = runner.invoke(
        app,
        ["delete", "my-project", "--directory", str(tmp_path)],
        input="my-project\n",
    )

    assert result.exit_code == 0, result.output
    assert len(deleted_on_github) == 1
    assert len(deleted_locally) == 1
    assert "Repository deleted successfully" in result.output


def test_delete_with_yes_flag_skips_confirmation_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from newrepo import local_repo

    _stub_delete_preconditions(monkeypatch)
    deleted_on_github = []
    deleted_locally = []
    monkeypatch.setattr(
        "newrepo.cli.github_repo.delete_repo_on_github",
        lambda path: deleted_on_github.append(path),
    )
    monkeypatch.setattr(
        local_repo, "delete_directory", lambda path: deleted_locally.append(path)
    )

    result = runner.invoke(
        app, ["delete", "my-project", "--directory", str(tmp_path), "--yes"]
    )

    assert result.exit_code == 0, result.output
    assert len(deleted_on_github) == 1
    assert len(deleted_locally) == 1
