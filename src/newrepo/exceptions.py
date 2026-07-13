"""newrepo で発生する既知のエラーを表す例外クラス群。

すべての例外は :class:`NewRepoError` を継承し、``str(exc)`` が
そのままユーザー向けの分かりやすいメッセージになるようにしている。
"""

from __future__ import annotations

from pathlib import Path


class NewRepoError(Exception):
    """newrepo CLI 内で発生する既知のエラーの基底クラス。"""


class DependencyNotFoundError(NewRepoError):
    """必須コマンド（git / gh）が見つからない場合のエラー。"""

    def __init__(self, command: str, install_hint: str) -> None:
        self.command = command
        super().__init__(
            f"'{command}' コマンドが見つかりません。{install_hint}"
        )


class GitHubAuthError(NewRepoError):
    """GitHub CLI が未認証の場合のエラー。"""

    def __init__(self) -> None:
        super().__init__(
            "GitHub CLI が認証されていません。"
            "`gh auth login` を実行してから再度お試しください。"
        )


class DirectoryExistsError(NewRepoError):
    """作成先ディレクトリが既に存在する場合のエラー。"""

    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"ディレクトリが既に存在します: {path}")


class CommandExecutionError(NewRepoError):
    """外部コマンド（git / gh）の実行に失敗した場合のエラー。"""

    def __init__(self, description: str, stderr: str) -> None:
        self.description = description
        self.stderr = stderr
        message = f"{description}に失敗しました。"
        detail = stderr.strip()
        if detail:
            message += f"\n詳細:\n{detail}"
        super().__init__(message)
