# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# セットアップ（初回 / 依存関係変更後）
uv sync --all-groups

# テスト全体
uv run pytest

# 単体テストを1つだけ実行
uv run pytest tests/test_local_repo.py::test_create_directory -q

# lint
uv run ruff check .
uv run ruff check --fix .   # 自動修正可能な分だけ直す

# 型チェック
uv run mypy

# ローカルの編集を反映させた状態で `newrepo` コマンドをグローバルインストール
uv tool install --editable . --force

# バージョンを上げる（pyproject.toml の書き換え + 再ロックまで行う）
uv version --bump patch   # or minor / major
```

`main` への push・PR 作成時に `.github/workflows/ci.yml` が `pytest` / `ruff check` / `mypy` を自動実行する。ローカルで区別せずまとめて確認したい場合は上記3つを順に実行すればCIと同じ状態を再現できる。

テストは `shell.run()`（内部で `subprocess.run` を呼ぶ薄いラッパー）を `monkeypatch` で差し替えることで完結しており、実際の `git`/`gh` コマンドやネットワークには依存しない。そのため `pytest` は `gh auth login` 未実施の環境でも通る。

## アーキテクチャ

`newrepo` は GitHub リポジトリ作成の定型作業（ディレクトリ作成 → README → `git init` → Initial Commit → `gh repo create` → push）を自動化する Typer 製 CLI。`src/newrepo/` 配下は責務ごとに分離している。

- `cli.py` — Typer サブコマンド（`create` / `doctor` / `rename`）の定義と、各ステップの実行順序・チェックマーク付き出力のみを担当する「司令塔」。実際の処理ロジックは持たない。
- `preflight.py` — `git`/`gh` の存在確認と `gh auth status` による認証確認。`run_all()`（作成・リネームフロー用、失敗時に例外を送出）と `run_checks()`（`doctor` 用、全項目を実行しきって結果一覧を返す）の2系統がある。
- `local_repo.py` — ディレクトリ作成・README生成・git操作など、ローカルで完結する処理。
- `github_repo.py` — `gh`/`git` を使った GitHub 側の操作（リポジトリ作成・push・リネーム・remote URL取得）。SSH/HTTPS どちらの remote URL 形式もリネームできるよう正規表現でパースしている（`_renamed_url`）。
- `shell.py` — 全ての外部コマンド実行を集約する `subprocess.run` の薄いラッパー。ここを経由させることでテスト時にモックしやすくしている。
- `exceptions.py` — `NewRepoError` を基底クラスとした専用例外群。`str(exc)` がそのままユーザー向けの日本語エラーメッセージになる。`cli.py` 側は `NewRepoError` を1箇所で捕捉するだけでよい。

### 設計上の重要な制約（非自明な部分）

- **CLI のトップレベルはサブコマンド構成（`create`/`doctor`/`rename`）＋ `--version` のみフラグ**という非対称な構成になっている。理由は Typer（内部は Click）の制約: NAME を位置引数として受け取る単一コマンドに Click の Group（サブコマンド）を追加すると、「サブコマンド名」なのか「位置引数の値」なのかを Click が区別できず誤動作する（実装時に実際に再現して確認済み）。そのため裸の `newrepo NAME` のような呼び出し方は採用していない。今後サブコマンドを追加する際もこの制約を踏まえること。
- **`rename` は GitHub 側 → ローカルの順で実行する**（`gh repo rename` → `git remote set-url` → 最後に `Path.rename()` でローカルディレクトリをリネーム）。ディレクトリのリネームを最後にしているのは、途中で失敗した際に「ディレクトリだけ消えて中途半端な状態になる」事態を避けるため。
- **バージョンは `pyproject.toml` の `version` フィールドを唯一の情報源とする**。`cli.py` の `--version` はソースに文字列を埋め込まず `importlib.metadata.version("newrepo")` で取得している。バージョン更新は `uv version --bump <level>` を使う運用（README参照）。
- **`gh repo create --source=. --remote=origin`** を使うことで、GitHub上でのリポジトリ作成とローカルの remote 設定を1コマンドで済ませている（`gh` の機能に乗る形でシンプルさを優先）。push だけは失敗時の切り分けをしやすくするため `git push -u origin HEAD` として別コマンドにしている。
- **ruff の `B008` は意図的に無視している**（`pyproject.toml` の `[tool.ruff.lint]`）。Typer の `Option()`/`Argument()` を引数のデフォルト値として呼び出すのが定型パターンであり、これに対する誤検知のため。

### 実装していない機能（スコープ外）

テンプレート機能、`.gitignore`/LICENSE/GitHub Actions の自動生成（作成するリポジトリ側への生成）、設定ファイル対応、Organization対応、リポジトリ名の別名指定、削除コマンド（危険な操作のため保留中）は意図的に未実装。詳細と理由は README.md の「スコープ外」セクション参照。

## 環境まわりの注意点（macOS + SSH commit署名）

このリポジトリは commit を SSH 鍵で署名する設定（`git config commit.gpgsign` / `user.signingkey`）を使っている環境がある。署名鍵が ssh-agent に読み込まれていない状態だと、`git commit` 実行時に `ssh-keygen -Y sign` が passphrase 入力（Touch ID等）を待って非対話環境ではハングすることがある。

`git commit` がハングした・タイムアウトした場合は、まず `ssh-add -l` で対象の署名鍵がエージェントに読み込まれているか確認する。読み込まれていなければ、ユーザーに以下をユーザー自身のセッションで一度実行してもらう（秘密鍵に触れる操作のため Claude 側からは実行しない）。

```bash
ssh-add --apple-use-keychain ~/.ssh/<signing-key>
```

ただし Touch ID 認証には猶予期間があるだけで恒久的に不要になるわけではなく、認証から時間が経つと再度ハングしうる。`git commit`/`git push` をバックグラウンド実行する際は、シェルの `&`/`disown` ではなく Bash ツールの `run_in_background` オプションを使うこと（前者はサンドボックス内で確実に検知できないことがある）。
