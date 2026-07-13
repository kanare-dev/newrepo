"""newrepo の CLI エントリポイント。

``newrepo <name>`` 実行時の一連の処理（ディレクトリ作成 → README作成 →
git init → Initial Commit → GitHub リポジトリ作成 → push）を
順番に実行し、各ステップの結果を画面に出力する。
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Optional

import typer

from . import github_repo, local_repo, preflight
from .exceptions import NewRepoError

app = typer.Typer(
    add_completion=False,
    help="GitHub リポジトリ作成の定型作業を自動化する CLI ツール",
)


def _step(label: str, action: Callable[[], None]) -> None:
    """1つの作業ステップを実行し、成功したらチェックマーク付きで表示する。"""
    action()
    typer.secho(f"✓ {label}", fg=typer.colors.GREEN)


@app.command()
def main(
    name: str = typer.Argument(
        ...,
        help="作成するリポジトリ名（ローカルディレクトリ名 = GitHub リポジトリ名）",
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


if __name__ == "__main__":
    app()
