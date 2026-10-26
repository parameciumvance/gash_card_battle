"""從使用者維護的公開 Google Drive 資料夾批次下載卡圖至 frontend/assets/cards/{卡號}.webp。

- 卡圖來源是 FOLDER_ID 的資料夾,圖檔名為 {卡號}.webp;補圖、換圖都在資料夾操作。
- 以公開資料夾的 embeddedfolderview 頁面取得「檔名 → 檔案 ID」,不需要 API 金鑰;解析不到任何檔案時報錯結束。
- 下載到的已是 WebP 就原樣存檔;不是 WebP 時轉成 WebP(q80,保留透明)。
- 已存在 .webp 的卡自動跳過(支援中斷續抓);舊的 .jpg 不算,會重新下載。
- 資料夾中沒有的卡與下載失敗不中斷,結束時輸出失敗清單至 frontend/assets/cards/_failed.txt。
- 卡圖缺失不影響遊戲(前端以文字卡面呈現)。

用法: python tools/download_images.py
"""

from __future__ import annotations

import html
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "data/cards.json"
OUT_DIR = ROOT / "frontend/assets/cards"
FAILED = OUT_DIR / "_failed.txt"

FOLDER_ID = "1cXx4gpa41HiycU4hIN74xbp1Aj3hiE-k"   # 卡圖資料夾(使用者維護,公開分享)
UA = {"User-Agent": "Mozilla/5.0 (deck-image-fetcher)"}
WEBP_QUALITY = 80  # 卡面文字放大檢視仍清楚,每張約 80KB
_ENTRY = re.compile(r'id="entry-([\w-]+)".*?class="flip-entry-title">([^<]*)<', re.S)


def fetch_folder_page() -> str:
    url = f"https://drive.google.com/embeddedfolderview?id={FOLDER_ID}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as res:
        return res.read().decode("utf-8")


def parse_folder(page: str) -> dict[str, str]:
    """資料夾頁面 → {檔名: 檔案 ID};同名時以第一筆為準。"""
    files: dict[str, str] = {}
    for file_id, title in _ENTRY.findall(page):
        files.setdefault(html.unescape(title).strip(), file_id)
    return files


def fetch(file_id: str) -> bytes | None:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as res:
        data = res.read()
    if data[:6] in (b"<!DOCT", b"<html>", b"<html "):
        return None  # 拿到攔截頁而非圖檔
    return data


def is_webp(data: bytes) -> bool:
    return data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def to_webp(data: bytes) -> bytes:
    """原圖轉成 WebP,尺寸不變、保留透明通道(卡片圓角)。"""
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
    return buf.getvalue()


def main() -> None:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    folder = parse_folder(fetch_folder_page())
    if not folder:
        sys.exit(f"卡圖資料夾 {FOLDER_ID} 的頁面解析不到任何檔案(資料夾不公開或頁面格式改變)")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = skip = fail = 0
    failures: list[str] = []
    for card in cards:
        number = card["number"]
        dest = OUT_DIR / f"{number}.webp"
        if dest.exists():
            skip += 1
            continue
        file_id = folder.get(dest.name)
        if not file_id:
            failures.append(f"{number}\tnot-in-folder")
            fail += 1
            continue
        try:
            data = fetch(file_id)
            if not data:
                raise RuntimeError("interstitial page")
            webp = data if is_webp(data) else to_webp(data)
            dest.write_bytes(webp)
            ok += 1
            print(f"✓ {number} ({len(webp) // 1024} KB)")
            time.sleep(0.4)  # 避免限流
        except Exception as exc:  # noqa: BLE001 — 記錄後繼續
            failures.append(f"{number}\t{exc}")
            fail += 1
            print(f"✗ {number}: {exc}", file=sys.stderr)
    if failures:
        FAILED.write_text("\n".join(failures), encoding="utf-8")
    print(f"完成: 下載 {ok}、已存在 {skip}、失敗 {fail}"
          + (f"(清單見 {FAILED})" if failures else ""))


if __name__ == "__main__":
    main()
