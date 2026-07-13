"""newrepo の CLI エントリポイント。

``newrepo <name>`` 実行時の一連の処理（ディレクトリ作成 → README作成 →
git init → Initial Commit → GitHub リポジトリ作成 → push）を
順番に実行し、各ステップの結果を画面に出力する。

``--doctor`` / ``--rename`` はサブコマンドではなくオプションとして実装している。
NAME を位置引数として受け取る単一コマンドに Typer のサブコマンドを追加すると、
Click の引数解析上「サブコマンド名」と「NAME」を区別できず誤動作するため。
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version
from pathlib import Path
from typing import Optional

import typer

from . import github_repo, local_repo, preflight
from .exceptions import NewRepoError

app = typer.Typer(
    add_completion=False,
    help="GitHub リポジトリ作成の定型作業を自動化する CLI ツール",
)


def _version_callback(value: bool) -> None:
    """`--version` 指定時にバージョンを表示して終了する。

    バージョン番号は ``pyproject.toml`` の ``version`` フィールドを
    唯一の情報源とし、インストール済みパッケージのメタデータ経由で取得する。
    """
    if not value:
        return
    try:
        typer.echo(f"newrepo {_package_version('newrepo')}")
    except PackageNotFoundError:
        typer.echo("newrepo (バージョン情報を取得できませんでした)")
    raise typer.Exit()


def _step(label: str, action: Callable[[], None]) -> None:
    """1つの作業ステップを実行し、成功したらチェックマーク付きで表示する。"""
    action()
    typer.secho(f"✓ {label}", fg=typer.colors.GREEN)


def _run_doctor() -> None:
    """git / gh の準備状況をチェックし、結果を表示して終了する。"""
    typer.echo("Checking environment...")

    results = preflight.run_checks()
    for result in results:
        if result.ok:
            typer.secho(f"✓ {result.label}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"✗ {result.label}", fg=typer.colors.RED)
            if result.detail:
                typer.secho(f"  → {result.detail}", fg=typer.colors.RED)

    if all(result.ok for result in results):
        typer.echo("All checks passed. newrepo is ready to use.")
        raise typer.Exit(code=0)

    typer.echo("Some checks failed. Please fix the issues above before using newrepo.")
    raise typer.Exit(code=1)


def _run_rename(name: str, new_name: str, directory: Optional[Path]) -> None:
    """既存のリポジトリを、ローカルディレクトリ・GitHub の両方でリネームする。"""
    if new_name == name:
        typer.secho(
            "エラー: 新しい名前が現在の名前と同じです。",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    base_dir = (directory or Path.cwd()).expanduser().resolve()
    target = base_dir / name
    new_target = base_dir / new_name

    typer.echo("Renaming repository...")

    try:
        preflight.run_all()

        local_repo.check_directory_exists(target)
        local_repo.check_is_git_repo(target)
        github_repo.get_remote_origin_url(target)

        _step(
            "GitHub repository renamed",
            lambda: github_repo.rename_repo_on_github(target, new_name),
        )
        _step(
            "Remote URL updated",
            lambda: github_repo.update_remote_url_after_rename(target, new_name),
        )
        _step(
            "Directory renamed",
            lambda: local_repo.rename_directory(target, new_target),
        )
    except NewRepoError as exc:
        typer.secho(f"✗ {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    github_url = github_repo.get_repo_url(new_target)

    typer.echo("Repository renamed successfully")
    typer.echo("Location:")
    typer.echo(str(new_target))
    typer.echo("GitHub:")
    typer.echo(github_url)


@app.command()
def main(
    name: Optional[str] = typer.Argument(
        None,
        help="作成/操作対象のリポジトリ名(ローカルディレクトリ名 = GitHub リポジトリ名)。"
        "--doctor / --version 指定時は不要。",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="バージョンを表示して終了する",
        callback=_version_callback,
        is_eager=True,
    ),
    public: bool = typer.Option(
        False,
        "--public",
        help="GitHub リポジトリを Public として作成する（デフォルト: Private）",
    ),
    directory: Optional[Path] = typer.Option(
        None,
        "--directory",
        "-d",
        help="対象の親ディレクトリ（デフォルト: カレントディレクトリ）",
    ),
    doctor: bool = typer.Option(
        False,
        "--doctor",
        help="git/gh のインストール状況と GitHub CLI の認証状態のみを確認して終了する",
    ),
    rename: Optional[str] = typer.Option(
        None,
        "--rename",
        metavar="NEW_NAME",
        help="NAME で指定した既存のリポジトリを NEW_NAME にリネームする"
        "（ローカルディレクトリ・GitHub リポジトリの両方）",
    ),
) -> None:
    """新規ディレクトリの作成から GitHub への push までを一括実行する。"""
    if doctor:
        _run_doctor()
        return

    if rename is not None:
        if name is None:
            typer.secho(
                "エラー: リネーム対象の現在の名前（NAME）を指定してください"
                "（例: newrepo my-project --rename new-name）",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
        _run_rename(name=name, new_name=rename, directory=directory)
        return

    if name is None:
        typer.secho(
            "エラー: NAME を指定してください（例: newrepo my-project）",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    base_dir = (directory or Path.cwd()).expanduser().resolve()
    target = base_dir / name

    typer.echo("Creating repository...")

    try:
        preflight.run_all()

        _step("Directory created", lambda: local_repo.create_directory(target))
        _step("README created", lambda: local_repo.create_readme(target, name))
        _step("Git initialized", lambda: local_repo.git_init(target))

        local_repo.git_add_all(target)
        _step("Initial commit created", lambda: local_repo.git_commit(target))

        _step(
            "GitHub repository created",
            lambda: github_repo.create_repo(target, name, public),
        )
        _step("Pushed to origin", lambda: github_repo.push(target))
    except NewRepoError as exc:
        typer.secho(f"✗ {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    github_url = github_repo.get_repo_url(target)

    typer.echo("Repository created successfully")
    typer.echo("Location:")
    typer.echo(str(target))
    typer.echo("GitHub:")
    typer.echo(github_url)


if __name__ == "__main__":
    app()
