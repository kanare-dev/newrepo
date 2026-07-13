"""実行前に必要な環境（git / gh のインストール状況・認証状態）を確認する。"""

from __future__ import annotations

import shutil
from dataclasses import dataclass

from . import shell
from .exceptions import DependencyNotFoundError, GitHubAuthError

GIT_INSTALL_HINT = "https://git-scm.com/downloads からインストールしてください。"
GH_INSTALL_HINT = "https://cli.github.com/ からインストールしてください。"
GH_AUTH_HINT = "`gh auth login` を実行してください。"


@dataclass
class CheckResult:
    """`newrepo --doctor` で表示する、1項目分のチェック結果。"""

    label: str
    ok: bool
    detail: str | None = None


def check_git() -> CheckResult:
    if shutil.which("git") is None:
        return CheckResult("git is installed", False, GIT_INSTALL_HINT)
    return CheckResult("git is installed", True)


def check_gh() -> CheckResult:
    if shutil.which("gh") is None:
        return CheckResult("gh is installed", False, GH_INSTALL_HINT)
    return CheckResult("gh is installed", True)


def check_gh_authenticated() -> CheckResult:
    if shutil.which("gh") is None:
        return CheckResult(
            "gh is authenticated", False, "gh コマンドが見つからないため確認できません。"
        )
    result = shell.run(["gh", "auth", "status"])
    if result.returncode != 0:
        return CheckResult("gh is authenticated", False, GH_AUTH_HINT)
    return CheckResult("gh is authenticated", True)


def run_checks() -> list[CheckResult]:
    """`newrepo --doctor` 用に、各チェックを最後まで実行し結果一覧を返す。"""
    return [check_git(), check_gh(), check_gh_authenticated()]


def check_git_installed() -> None:
    result = check_git()
    if not result.ok:
        raise DependencyNotFoundError("git", result.detail or GIT_INSTALL_HINT)


def check_gh_installed() -> None:
    result = check_gh()
    if not result.ok:
        raise DependencyNotFoundError("gh", result.detail or GH_INSTALL_HINT)


def check_gh_auth() -> None:
    result = check_gh_authenticated()
    if not result.ok:
        raise GitHubAuthError()


def run_all() -> None:
    """git / gh の存在確認と GitHub CLI の認証状態確認をまとめて行う（作成フロー用）。"""
    check_git_installed()
    check_gh_installed()
    check_gh_auth()
