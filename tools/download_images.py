"""從 data/cards.json 的 Google Drive 連結批次下載卡圖至 frontend/assets/cards/{卡號}.webp。

- 原圖是帶透明圓角的 PNG,下載後轉成 WebP(q80,保留透明)再存檔。
- 已存在 .webp 的卡自動跳過(支援中斷續抓);舊的 .jpg 不算,會重新下載。
- 失敗不中斷,結束時輸出失敗清單至 frontend/assets/cards/_failed.txt。
- 卡圖缺失不影響遊戲(前端以文字卡面呈現)。

用法: python tools/download_images.py [--retry-failed]
"""

from __future__ import annotations

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

UA = {"User-Agent": "Mozilla/5.0 (deck-image-fetcher)"}
WEBP_QUALITY = 80  # 卡面文字放大檢視仍清楚,每張約 80KB


def drive_id(url: str) -> str | None:
    m = re.search(r"/file/d/([^/]+)", url or "")
    return m.group(1) if m else None


def fetch(file_id: str) -> bytes | None:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as res:
        data = res.read()
    if data[:6] in (b"<!DOCT", b"<html>", b"<html "):
        return None  # 拿到攔截頁而非圖檔
    return data


def to_webp(data: bytes) -> bytes:
    """原圖轉成 WebP,尺寸不變、保留透明通道(卡片圓角)。"""
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).save(buf, "WEBP", quality=WEBP_QUALITY, method=6)
    return buf.getvalue()


def main() -> None:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = skip = fail = 0
    failures: list[str] = []
    for card in cards:
        number = card["number"]
        dest = OUT_DIR / f"{number}.webp"
        if dest.exists():
            skip += 1
            continue
        file_id = drive_id(card.get("image_url") or "")
        if not file_id:
            failures.append(f"{number}\tno-url")
            fail += 1
            continue
        try:
            data = fetch(file_id)
            if not data:
                raise RuntimeError("interstitial page")
            webp = to_webp(data)
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
