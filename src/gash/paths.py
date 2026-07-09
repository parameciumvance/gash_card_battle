"""資源目錄解析單點:程式資源(frontend/、data/)與卡圖資源分開決定。

程式資源隨發行包走(PyInstaller 凍結時在 _internal),卡圖為選配外部資源,
依 GASH_ASSETS_DIR → exe 旁 assets/ → 使用者資料夾 → repo frontend/assets/ 搜尋。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

ENV_ASSETS = "GASH_ASSETS_DIR"
APP_DIRNAME = "gash-card-battle"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_root() -> Path:
    """含 frontend/ 與 data/ 的程式資源根目錄。"""
    if is_frozen():
        return Path(sys._MEIPASS)  # onedir 下即 _internal/
    return Path(__file__).resolve().parents[2]  # repo 根(src/gash/paths.py → repo)


def frontend_dir() -> Path:
    return app_root() / "frontend"


def data_dir() -> Path:
    return app_root() / "data"


def exe_dir() -> Path:
    return Path(sys.executable).resolve().parent


def user_assets_dir() -> Path:
    """跨版本共用的卡圖建議安裝位置。"""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_DIRNAME / "assets"


@dataclass(frozen=True)
class AssetsInfo:
    dir: Path            # 卡圖資源目錄(assets/,其下應有 cards/)
    installed: bool      # 目錄是否存在
    install_dir: Path    # 建議安裝位置(未安裝時給提示用)


def _has_cards(p: Path) -> bool:
    """「已安裝」= 目錄下有 cards/(空資料夾不算,避免自動建立的安裝點搶走解析)。"""
    return (p / "cards").is_dir()


def resolve_assets(env: dict | None = None) -> AssetsInfo:
    """依序取第一個有卡圖的目錄;環境變數一律優先(即使不存在也不再往下找)。"""
    env = os.environ if env is None else env
    override = env.get(ENV_ASSETS)
    if override:
        p = Path(override)
        return AssetsInfo(dir=p, installed=_has_cards(p), install_dir=p)

    candidates = []
    if is_frozen():
        candidates.append(exe_dir() / "assets")
    candidates.append(user_assets_dir())
    if not is_frozen():
        candidates.append(frontend_dir() / "assets")

    for p in candidates:
        if _has_cards(p):
            return AssetsInfo(dir=p, installed=True, install_dir=user_assets_dir())
    return AssetsInfo(dir=user_assets_dir(), installed=False, install_dir=user_assets_dir())
