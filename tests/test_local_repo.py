"""local_repo モジュールのユニットテスト。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from newrepo import local_repo
from newrepo.exceptions import (
    CommandExecutionError,
    DirectoryExistsError,
    NotAGitRepositoryError,
    RepositoryNotFoundError,
)


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


def test_git_commit_raises_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args, returncode=1, stdout="", stderr="nothing to commit"
        )

    monkeypatch.setattr(local_repo.shell, "run", fake_run)

    with pytest.raises(CommandExecutionError):
        local_repo.git_commit(tmp_path)


def test_check_directory_exists_raises_if_missing(tmp_path: Path) -> None:
    with pytest.raises(RepositoryNotFoundError):
        local_repo.check_directory_exists(tmp_path / "missing")


def test_check_is_git_repo_raises_if_not_git(tmp_path: Path) -> None:
    with pytest.raises(NotAGitRepositoryError):
        local_repo.check_is_git_repo(tmp_path)


def test_rename_directory(tmp_path: Path) -> None:
    old_path = tmp_path / "old-name"
    old_path.mkdir()
    new_path = tmp_path / "new-name"

    local_repo.rename_directory(old_path, new_path)

    assert not old_path.exists()
    assert new_path.is_dir()


def test_rename_directory_raises_if_new_path_exists(tmp_path: Path) -> None:
    old_path = tmp_path / "old-name"
    old_path.mkdir()
    new_path = tmp_path / "new-name"
    new_path.mkdir()

    with pytest.raises(DirectoryExistsError):
        local_repo.rename_directory(old_path, new_path)


def test_delete_directory(tmp_path: Path) -> None:
    target = tmp_path / "my-project"
    target.mkdir()
    (target / "README.md").write_text("# my-project\n", encoding="utf-8")

    local_repo.delete_directory(target)

    assert not target.exists()


def test_delete_directory_raises_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "my-project"
    target.mkdir()

    def fake_rmtree(path: Path) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(local_repo.shutil, "rmtree", fake_rmtree)

    with pytest.raises(CommandExecutionError):
        local_repo.delete_directory(target)
