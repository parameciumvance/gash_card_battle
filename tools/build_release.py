"""發行打包:PyInstaller onedir → 單一 zip(不含卡圖)。

用法(於目標平台上執行;Windows 產物須在 Windows 建):
    python tools/build_release.py [--cloudflared PATH] [--skip-cloudflared]

- 前端與 data 以過濾後的暫存副本打入(排除 frontend/assets/cards/)
- cloudflared 取 --cloudflared 指定檔或 PATH 上既有檔;--skip-cloudflared 則不附
- 產出 dist/gash-card-battle-v{version}-{platform}.zip,解壓後 gash/ 點兩下 gash(.exe) 即玩
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
STAGE = ROOT / "build" / "release_stage"


def version() -> str:
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def stage_program_data() -> tuple[Path, Path]:
    """過濾後的 frontend(排除卡圖)與 data 暫存副本,供 --add-data 使用。"""
    if STAGE.exists():
        shutil.rmtree(STAGE)
    fe = STAGE / "frontend"
    shutil.copytree(ROOT / "frontend", fe,
                    ignore=shutil.ignore_patterns("cards"))
    assert not (fe / "assets" / "cards").exists(), "卡圖不得進入發行物"
    data = STAGE / "data"
    shutil.copytree(ROOT / "data", data, ignore=shutil.ignore_patterns("__pycache__"))
    return fe, data


def run_pyinstaller(fe: Path, data: Path) -> Path:
    sep = ";" if sys.platform == "win32" else ":"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onedir", "--console",
        "--name", "gash",
        "--paths", str(ROOT / "src"),
        "--add-data", f"{fe}{sep}frontend",
        "--add-data", f"{data}{sep}data",
        "--collect-submodules", "uvicorn",
        "--collect-submodules", "websockets",
        str(ROOT / "tools" / "launch_entry.py"),
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)
    return DIST / "gash"


def add_cloudflared(outdir: Path, explicit: str | None) -> bool:
    src = Path(explicit) if explicit else None
    if src is None:
        found = shutil.which("cloudflared.exe" if sys.platform == "win32" else "cloudflared")
        src = Path(found) if found else None
    if src is None or not src.is_file():
        print("!! 未找到 cloudflared:發行物將無外網邀請功能(啟動時降級為區網模式)")
        print("   官方下載:https://github.com/cloudflare/cloudflared/releases")
        return False
    dst = outdir / src.name
    shutil.copy2(src, dst)
    print(f"cloudflared: {src} → {dst}")
    return True


def make_zip(outdir: Path) -> Path:
    plat = {"win32": "win64", "darwin": "macos"}.get(sys.platform, "linux")
    if platform.machine().lower() in ("arm64", "aarch64"):
        plat += "-arm64"
    zpath = DIST / f"gash-card-battle-v{version()}-{plat}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(outdir.rglob("*")):
            zf.write(p, Path("gash") / p.relative_to(outdir))
    return zpath


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cloudflared", help="cloudflared 執行檔路徑(缺省找 PATH)")
    ap.add_argument("--skip-cloudflared", action="store_true", help="不附 cloudflared")
    args = ap.parse_args()

    fe, data = stage_program_data()
    outdir = run_pyinstaller(fe, data)
    if not args.skip_cloudflared:
        add_cloudflared(outdir, args.cloudflared)
    zpath = make_zip(outdir)
    size_mb = zpath.stat().st_size / 1024 / 1024
    print(f"\n完成:{zpath}({size_mb:.0f} MB)")
    print("驗證:解壓至新資料夾 → 執行 gash(.exe) → 瀏覽器自動開啟即成功")


if __name__ == "__main__":
    main()
