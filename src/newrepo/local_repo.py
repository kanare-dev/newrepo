"""ローカル側の作業（ディレクトリ作成・README作成・git操作・リネーム）。"""

from __future__ import annotations

from pathlib import Path

from . import shell
from .exceptions import (
    CommandExecutionError,
    DirectoryExistsError,
    NotAGitRepositoryError,
    RepositoryNotFoundError,
)

INITIAL_COMMIT_MESSAGE = "Initial commit"


def create_directory(path: Path) -> None:
    if path.exists():
        raise DirectoryExistsError(path)
    path.mkdir(parents=True)


def create_readme(path: Path, name: str) -> None:
    readme = path / "README.md"
    readme.write_text(f"# {name}\n", encoding="utf-8")


def git_init(path: Path) -> None:
    result = shell.run(["git", "init"], cwd=path)
    if result.returncode != 0:
        raise CommandExecutionError("git init", result.stderr)


def git_add_all(path: Path) -> None:
    result = shell.run(["git", "add", "."], cwd=path)
    if result.returncode != 0:
        raise CommandExecutionError("git add", result.stderr)


def git_commit(path: Path, message: str = INITIAL_COMMIT_MESSAGE) -> None:
    result = shell.run(["git", "commit", "-m", message], cwd=path)
    if result.returncode != 0:
        raise CommandExecutionError("Initial Commit の作成", result.stderr)


def check_directory_exists(path: Path) -> None:
    if not path.is_dir():
        raise RepositoryNotFoundError(path)


def check_is_git_repo(path: Path) -> None:
    if not (path / ".git").is_dir():
        raise NotAGitRepositoryError(path)


def rename_directory(old_path: Path, new_path: Path) -> None:
    if new_path.exists():
        raise DirectoryExistsError(new_path)
    try:
        old_path.rename(new_path)
    except OSError as exc:
        raise CommandExecutionError("ディレクトリのリネーム", str(exc)) from exc
