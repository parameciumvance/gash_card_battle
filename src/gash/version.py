"""版本號:部署時的 git tag 名稱(battle-api「執行環境中繼資訊」)。

取得順序:環境變數 GASH_VERSION(Docker 映像檔,CI 以 tag 名稱傳入)→ data/version.txt
(單機版,打包時寫入)→ git describe(開發環境)→ "dev"。行程內只取一次。
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache

from .paths import app_root, data_dir

ENV_VERSION = "GASH_VERSION"


@lru_cache(maxsize=1)
def app_version() -> str:
    env = os.environ.get(ENV_VERSION, "").strip()
    if env:
        return env
    try:
        text = (data_dir() / "version.txt").read_text(encoding="utf-8").strip()
        if text:
            return text
    except OSError:
        pass
    try:
        out = subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], cwd=app_root(),
                             capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "dev"
