"""GitHub 側の操作（リポジトリ作成・リモート設定・push）。

リポジトリ作成とリモート ``origin`` の設定は ``gh repo create`` の
``--source`` / ``--remote`` オプションにまとめて任せることで、シンプルに
実装している。push はエラーの切り分けをしやすくするため別コマンドにしている。
"""

from __future__ import annotations

from pathlib import Path

from . import shell
from .exceptions import CommandExecutionError


def create_repo(path: Path, name: str, public: bool) -> None:
    """GitHub 上にリポジトリを作成し、ローカルに remote ``origin`` を設定する。"""
    visibility = "--public" if public else "--private"
    result = shell.run(
        [
            "gh",
            "repo",
            "create",
            name,
            visibility,
            "--source=.",
            "--remote=origin",
        ],
        cwd=path,
    )
    if result.returncode != 0:
        raise CommandExecutionError("GitHub リポジトリの作成", result.stderr)


def push(path: Path) -> None:
    """現在のブランチを ``origin`` に push する。"""
    result = shell.run(["git", "push", "-u", "origin", "HEAD"], cwd=path)
    if result.returncode != 0:
        raise CommandExecutionError("push", result.stderr)


def get_repo_url(path: Path) -> str:
    """作成した GitHub リポジトリの URL を取得する。"""
    result = shell.run(
        ["gh", "repo", "view", "--json", "url", "--jq", ".url"],
        cwd=path,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    # gh repo view が使えない場合は git の remote URL からフォールバックする。
    fallback = shell.run(["git", "remote", "get-url", "origin"], cwd=path)
    return fallback.stdout.strip()
