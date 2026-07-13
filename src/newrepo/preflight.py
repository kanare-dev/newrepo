"""実行前に必要な環境（git / gh のインストール状況・認証状態）を確認する。"""

from __future__ import annotations

import shutil

from . import shell
from .exceptions import DependencyNotFoundError, GitHubAuthError


def check_git_installed() -> None:
    if shutil.which("git") is None:
        raise DependencyNotFoundError(
            "git",
            "https://git-scm.com/downloads からインストールしてください。",
        )


def check_gh_installed() -> None:
    if shutil.which("gh") is None:
        raise DependencyNotFoundError(
            "gh",
            "https://cli.github.com/ からインストールしてください。",
        )


def check_gh_auth() -> None:
    result = shell.run(["gh", "auth", "status"])
    if result.returncode != 0:
        raise GitHubAuthError()


def run_all() -> None:
    """git / gh の存在確認と GitHub CLI の認証状態確認をまとめて行う。"""
    check_git_installed()
    check_gh_installed()
    check_gh_auth()
