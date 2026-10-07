"""資源目錄解析單點:程式資源(frontend/、data/)取 repo 佈局,卡圖目錄另外決定。

卡圖目錄:環境變數 GASH_ASSETS_DIR(VPS 容器掛載的 volume)→ repo frontend/assets/。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_ASSETS = "GASH_ASSETS_DIR"


def app_root() -> Path:
    """含 frontend/ 與 data/ 的程式資源根目錄。"""
    return Path(__file__).resolve().parents[2]  # repo 根(src/gash/paths.py → repo)


def frontend_dir() -> Path:
    return app_root() / "frontend"


def data_dir() -> Path:
    return app_root() / "data"


@dataclass(frozen=True)
class AssetsInfo:
    dir: Path            # 卡圖資源目錄(assets/,其下應有 cards/)
    installed: bool      # 目錄下是否有 cards/


def resolve_assets(env: dict | None = None) -> AssetsInfo:
    """環境變數一律優先(即使不存在也不改用 repo 目錄);空的 assets/ 不算已安裝。"""
    env = os.environ if env is None else env
    override = env.get(ENV_ASSETS)
    p = Path(override) if override else frontend_dir() / "assets"
    return AssetsInfo(dir=p, installed=(p / "cards").is_dir())
