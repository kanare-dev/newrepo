"""外部コマンド実行用の薄いラッパー。

すべての ``git`` / ``gh`` 呼び出しはこの関数を経由させることで、
テスト時のモックや将来的なロギング追加を行いやすくしている。
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """コマンドを実行し、結果を返す。

    ``check=False`` で実行するため、呼び出し側で ``returncode`` を見て
    エラーハンドリングを行うこと（例外は送出しない）。
    """
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
