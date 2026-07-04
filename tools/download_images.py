"""從 data/cards.json 的 Google Drive 連結批次下載卡圖至 frontend/assets/cards/{卡號}.jpg。

- 已存在的檔案自動跳過(支援中斷續抓)。
- 失敗不中斷,結束時輸出失敗清單至 frontend/assets/cards/_failed.txt。
- 卡圖缺失不影響遊戲(前端以文字卡面呈現)。

用法: python tools/download_images.py [--retry-failed]
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "data/cards.json"
OUT_DIR = ROOT / "frontend/assets/cards"
FAILED = OUT_DIR / "_failed.txt"

UA = {"User-Agent": "Mozilla/5.0 (deck-image-fetcher)"}


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


def main() -> None:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = skip = fail = 0
    failures: list[str] = []
    for card in cards:
        number = card["number"]
        dest = OUT_DIR / f"{number}.jpg"
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
            dest.write_bytes(data)
            ok += 1
            print(f"✓ {number} ({len(data) // 1024} KB)")
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
