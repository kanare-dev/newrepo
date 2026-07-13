"""local_repo モジュールのユニットテスト。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from newrepo import local_repo
from newrepo.exceptions import CommandExecutionError, DirectoryExistsError


def test_create_directory(tmp_path: Path) -> None:
    target = tmp_path / "my-project"
    local_repo.create_directory(target)
    assert target.is_dir()


def test_create_directory_raises_if_exists(tmp_path: Path) -> None:
    target = tmp_path / "my-project"
    target.mkdir()
    with pytest.raises(DirectoryExistsError):
        local_repo.create_directory(target)


def test_create_readme(tmp_path: Path) -> None:
    local_repo.create_readme(tmp_path, "my-project")
    readme = tmp_path / "README.md"
    assert readme.read_text(encoding="utf-8") == "# my-project\n"


def test_git_commit_raises_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="nothing to commit")

    monkeypatch.setattr(local_repo.shell, "run", fake_run)

    with pytest.raises(CommandExecutionError):
        local_repo.git_commit(tmp_path)
