"""GitHub 側の操作（リポジトリ作成・リモート設定・push・リネーム）。

リポジトリ作成とリモート ``origin`` の設定は ``gh repo create`` の
``--source`` / ``--remote`` オプションにまとめて任せることで、シンプルに
実装している。push はエラーの切り分けをしやすくするため別コマンドにしている。
"""

from __future__ import annotations

import re
from pathlib import Path

from . import shell
from .exceptions import CommandExecutionError, RemoteNotConfiguredError

_REMOTE_URL_PATTERN = re.compile(
    r"^(?P<prefix>.*[:/])(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?P<suffix>\.git)?$"
)


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


def get_remote_origin_url(path: Path) -> str:
    """remote ``origin`` の URL を取得する。設定されていなければエラー。"""
    result = shell.run(["git", "remote", "get-url", "origin"], cwd=path)
    if result.returncode != 0 or not result.stdout.strip():
        raise RemoteNotConfiguredError(path)
    return result.stdout.strip()


def rename_repo_on_github(path: Path, new_name: str) -> None:
    """GitHub 上のリポジトリ名を変更する（``gh repo rename``）。"""
    result = shell.run(["gh", "repo", "rename", new_name, "--yes"], cwd=path)
    if result.returncode != 0:
        raise CommandExecutionError("GitHub リポジトリのリネーム", result.stderr)


def _renamed_url(old_url: str, new_name: str) -> str:
    """remote URL 内のリポジトリ名部分だけを ``new_name`` に置き換える。

    HTTPS 形式（``https://github.com/owner/repo.git``）と
    SSH 形式（``git@github.com:owner/repo.git``）の両方に対応する。
    """
    match = _REMOTE_URL_PATTERN.match(old_url)
    if match is None:
        raise CommandExecutionError(
            "リモートURLの更新", f"remote URL の形式を解釈できませんでした: {old_url}"
        )
    prefix = match.group("prefix")
    owner = match.group("owner")
    suffix = match.group("suffix") or ""
    return f"{prefix}{owner}/{new_name}{suffix}"


def update_remote_url_after_rename(path: Path, new_name: str) -> None:
    """リネーム後の名前に合わせて、ローカルの remote ``origin`` の URL を更新する。"""
    old_url = get_remote_origin_url(path)
    new_url = _renamed_url(old_url, new_name)
    result = shell.run(["git", "remote", "set-url", "origin", new_url], cwd=path)
    if result.returncode != 0:
        raise CommandExecutionError("リモートURLの更新", result.stderr)
