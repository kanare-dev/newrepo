"""github_repo モジュールのユニットテスト（主に URL 変換ロジック）。"""

from __future__ import annotations

import pytest

from newrepo.exceptions import CommandExecutionError
from newrepo.github_repo import _renamed_url


@pytest.mark.parametrize(
    ("old_url", "new_name", "expected"),
    [
        (
            "https://github.com/kanare-dev/newrepo.git",
            "renamed-repo",
            "https://github.com/kanare-dev/renamed-repo.git",
        ),
        (
            "git@github.com:kanare-dev/newrepo.git",
            "renamed-repo",
            "git@github.com:kanare-dev/renamed-repo.git",
        ),
        (
            "https://github.com/kanare-dev/newrepo",
            "renamed-repo",
            "https://github.com/kanare-dev/renamed-repo",
        ),
    ],
)
def test_renamed_url(old_url: str, new_name: str, expected: str) -> None:
    assert _renamed_url(old_url, new_name) == expected


def test_renamed_url_raises_on_unrecognized_format() -> None:
    with pytest.raises(CommandExecutionError):
        _renamed_url("not-a-valid-url", "renamed-repo")
