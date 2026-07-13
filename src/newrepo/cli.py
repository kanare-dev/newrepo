"""newrepo の CLI エントリポイント。

サブコマンド構成:

- ``newrepo create NAME [OPTIONS]``            新規リポジトリの作成
- ``newrepo doctor``                           前提条件（git/gh）の確認
- ``newrepo rename NAME NEW_NAME [OPTIONS]``    リポジトリのリネーム
- ``newrepo delete NAME [OPTIONS]``             リポジトリの削除（ローカル+GitHub、取り消し不可）
- ``newrepo --version``                        バージョン表示

``--version`` だけは他の CLI ツール（git, docker 等）の慣例に合わせ、
サブコマンドではなくトップレベルのフラグとして実装している。
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version
from pathlib import Path

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


@app.callback(invoke_without_command=True)
def entry_point(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="バージョンを表示して終了する",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _step(label: str, action: Callable[[], None]) -> None:
    """1つの作業ステップを実行し、成功したらチェックマーク付きで表示する。"""
    action()
    typer.secho(f"✓ {label}", fg=typer.colors.GREEN)


@app.command()
def create(
    name: str = typer.Argument(
        help="作成するリポジトリ名（ローカルディレクトリ名 = GitHub リポジトリ名）",
    ),
    public: bool = typer.Option(
        False,
        "--public",
        help="GitHub リポジトリを Public として作成する（デフォルト: Private）",
    ),
    directory: Path | None = typer.Option(
        None,
        "--directory",
        "-d",
        help="作成先の親ディレクトリ（デフォルト: カレントディレクトリ）",
    ),
) -> None:
    """新規ディレクトリの作成から GitHub への push までを一括実行する。"""
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


@app.command()
def doctor() -> None:
    """git / gh のインストール状況と GitHub CLI の認証状態を確認する。"""
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


@app.command()
def rename(
    name: str = typer.Argument(
        help="現在のリポジトリ名（ローカルディレクトリ名 = GitHub リポジトリ名）",
    ),
    new_name: str = typer.Argument(help="変更後の新しい名前"),
    directory: Path | None = typer.Option(
        None,
        "--directory",
        "-d",
        help="対象の親ディレクトリ（デフォルト: カレントディレクトリ）",
    ),
) -> None:
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
def delete(
    name: str = typer.Argument(
        help="削除するリポジトリ名（ローカルディレクトリ名 = GitHub リポジトリ名）",
    ),
    directory: Path | None = typer.Option(
        None,
        "--directory",
        "-d",
        help="対象の親ディレクトリ（デフォルト: カレントディレクトリ）",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="確認プロンプトをスキップする（デフォルト: 確認あり。取り消せない操作のため注意）",
    ),
) -> None:
    """ローカルディレクトリと GitHub リポジトリの両方を削除する（取り消せません）。"""
    base_dir = (directory or Path.cwd()).expanduser().resolve()
    target = base_dir / name

    try:
        preflight.run_all()
        local_repo.check_directory_exists(target)
        local_repo.check_is_git_repo(target)
        github_repo.get_remote_origin_url(target)
    except NewRepoError as exc:
        typer.secho(f"✗ {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho(
        f"警告: '{name}' のローカルディレクトリと GitHub リポジトリを完全に削除します。"
        "この操作は取り消せません。",
        fg=typer.colors.RED,
    )

    if not yes:
        typed_name = typer.prompt(
            f"続行するには、リポジトリ名 '{name}' を入力してください"
        )
        if typed_name != name:
            typer.secho(
                "入力されたリポジトリ名が一致しないため、削除を中止しました。",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)

    typer.echo("Deleting repository...")

    try:
        _step(
            "GitHub repository deleted",
            lambda: github_repo.delete_repo_on_github(target),
        )
        _step("Directory deleted", lambda: local_repo.delete_directory(target))
    except NewRepoError as exc:
        typer.secho(f"✗ {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo("Repository deleted successfully")


if __name__ == "__main__":
    app()
