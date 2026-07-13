# newrepo

GitHub リポジトリ作成時の定型作業を自動化する CLI ツールです。

```
newrepo my-project
```

を実行するだけで、以下を一括で行います。

1. ディレクトリ作成
2. README.md 作成
3. `git init`
4. Initial Commit 作成
5. GitHub リポジトリ作成（`gh` を利用）
6. リモート（`origin`）設定
7. push

## 必要環境

- Python 3.12 以上
- [uv](https://docs.astral.sh/uv/)
- [git](https://git-scm.com/)
- [GitHub CLI (`gh`)](https://cli.github.com/) （`gh auth login` 済みであること）

## セットアップ

```bash
git clone <このリポジトリ>
cd newrepo
uv sync
```

`uv sync` で仮想環境の作成と依存関係のインストールが行われます。

## インストール（CLI として使う）

ローカルの `uv` プロジェクトから、`newrepo` コマンドをどこからでも実行できるようにインストールします。

```bash
uv tool install --editable .
```

インストール後は、任意のディレクトリで `newrepo` コマンドが使えます。

```bash
newrepo --help
```

開発中に手元のソースだけで動作確認したい場合は、プロジェクトディレクトリ内から次のように実行できます。

```bash
uv run newrepo --help
```

## 使い方

### 基本（カレントディレクトリ配下に作成）

```bash
newrepo my-project
```

`./my-project` ディレクトリが作成され、GitHub 上に **Private** リポジトリとして
`my-project` が作成・push されます。

### Public リポジトリとして作成する

```bash
newrepo my-project --public
```

### 作成先ディレクトリを指定する

```bash
newrepo my-project --directory ~/projects
```

`~/projects/my-project` が作成されます。`--directory` を省略した場合は
カレントディレクトリ配下に作成されます。

### 実行例（成功時の出力）

```
$ newrepo my-project
Creating repository...
✓ Directory created
✓ README created
✓ Git initialized
✓ Initial commit created
✓ GitHub repository created
✓ Pushed to origin
Repository created successfully
Location:
/Users/you/my-project
GitHub:
https://github.com/you/my-project
```

### 前提条件のチェック（`--doctor`）

`git` / `gh` のインストール状況と GitHub CLI の認証状態だけを確認したい場合は
`--doctor` フラグを使います（リポジトリの作成は行いません）。

```bash
newrepo --doctor
```

```
$ newrepo --doctor
Checking environment...
✓ git is installed
✓ gh is installed
✓ gh is authenticated
All checks passed. newrepo is ready to use.
```

いずれかのチェックに失敗した場合は `✗` と対処方法が表示され、終了コード 1 で終了します。

## エラーハンドリング

以下のケースでは、処理を中断しわかりやすいエラーメッセージを表示します（終了コード 1）。

- 作成先ディレクトリが既に存在する
- `git` がインストールされていない
- `gh` がインストールされていない
- `gh auth login` が未実施（GitHub CLI 未認証）
- `git commit` の失敗（例: コミット対象がない場合など）
- GitHub リポジトリ作成の失敗（例: 同名リポジトリが既に存在する場合など）
- push の失敗

## 開発

```bash
uv sync
uv run pytest
```

## 設計方針・ディレクトリ構成

```
newrepo/
├── pyproject.toml
├── README.md
├── src/
│   └── newrepo/
│       ├── __init__.py     # パッケージエントリポイント（app を re-export）
│       ├── cli.py          # Typer アプリ定義。処理フローの組み立てと画面出力のみを担当
│       ├── preflight.py    # git / gh の存在確認、gh auth 確認
│       ├── local_repo.py   # ディレクトリ作成・README作成・git 操作（ローカルのみ）
│       ├── github_repo.py  # gh によるリポジトリ作成・push・URL取得（GitHubのみ）
│       ├── shell.py        # subprocess 実行の薄いラッパー
│       └── exceptions.py   # ユーザー向けメッセージを持つ例外クラス群
└── tests/
    ├── test_local_repo.py
    └── test_cli_doctor.py
```

### 判断理由

- **`cli.py` に処理の詳細を書かない**
  `cli.py` は Typer のオプション定義と、各ステップを順番に呼び出して
  チェックマーク付きで出力するだけの「司令塔」に徹しています。
  実際の処理（ディレクトリ操作・git 操作・GitHub 操作）は
  `local_repo.py` / `github_repo.py` に分離しているため、
  将来 `.gitignore` 生成や LICENSE 生成などのステップを追加する場合も
  `cli.py` に1行 `_step(...)` を足すだけで済みます。

- **ローカル操作と GitHub 操作を別モジュールに分離**
  「ローカルで完結する処理」と「GitHub API/CLI に依存する処理」を
  分けることで、将来的にローカル操作だけを再利用したり、
  GitHub 以外のホスティング（GitLab等）に対応したりする際の変更範囲を
  局所化できます。

- **`--doctor` はサブコマンドではなくフラグとして実装**
  `newrepo my-project` のように NAME を位置引数として受け取りつつ、
  `newrepo doctor` のような名前付きサブコマンドも共存させようとすると、
  Click（Typerの内部実装）の引数解析の都合上、
  「`doctor` がサブコマンド名なのか、作成したいリポジトリ名なのか」を
  区別できず誤動作することを実装時に確認しました。
  この曖昧さを避けるため、事前チェックは `newrepo --doctor` という
  フラグとして実装し、既存の `newrepo <name>` の呼び出し方は一切変更していません。
  実体は `preflight.py` の `run_checks()` を呼び出すだけで、
  作成フロー用の `run_all()` と実装を共有しています。

- **例外は基底クラス `NewRepoError` を継承した専用クラスで表現**
  `DependencyNotFoundError` / `GitHubAuthError` / `DirectoryExistsError` /
  `CommandExecutionError` の4種類に分け、`cli.py` 側では
  `NewRepoError` を一箇所で捕捉するだけで、
  仕様に挙げられた全エラーケースに対して分かりやすい日本語メッセージを
  表示できるようにしています。

- **GitHub リポジトリ作成には `gh repo create --source=. --remote=origin` を使用**
  ローカルに既に git リポジトリ（コミット済み）がある状態から、
  GitHub 上へのリポジトリ作成とリモート `origin` の設定を
  1コマンドで行える `gh` の機能を利用することで、
  「リモート設定」のためだけの実装を増やさずシンプルに済ませています。
  push は結果を分かりやすくする（「GitHub リポジトリ作成の失敗」と
  「push の失敗」を明確に区別できるようにする）ため、
  `git push -u origin HEAD` として別コマンドに分けています。

- **`shell.py` で subprocess 呼び出しを一元化**
  すべての外部コマンド実行を `shell.run()` に集約することで、
  テスト時に `monkeypatch` で差し替えやすくし、
  将来的なロギングやタイムアウト設定の追加も1箇所の変更で済むようにしています。

- **`gh auth status` による事前チェック**
  実際の作成処理（ディレクトリ作成など）に入る前に
  `git` / `gh` の存在確認と GitHub CLI の認証状態を確認することで、
  「ディレクトリだけ作られて途中で失敗する」といった
  中途半端な状態を極力避けています。

### スコープ外（今回は実装していないもの）

要件に基づき、以下は MVP の対象外としています。将来的に追加する場合も、
上記の通り `local_repo.py` / `github_repo.py` にステップを追加し、
`cli.py` から呼び出すだけで対応できる構造にしてあります。

- テンプレート機能（Cookiecutter / Copier 連携含む）
- GitHub Actions の生成
- `.gitignore` の生成
- LICENSE の生成
- 設定ファイル対応
- Organization 対応（個人アカウント配下に作成）
- リポジトリ名とローカルディレクトリ名の別名指定
