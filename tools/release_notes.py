"""更新內容的發布工具(docker-deployment「CI 測試與建置分流」、battle-ui「更新內容」)。

讀 `frontend/i18n/releases.zh-TW.json`(繁中為主要來源),供 CI 在推送版本 tag 時使用:

- `check <tag>`:最新一版(第一個)的版本號必須等於 tag,否則以非零結束並說明缺少的版本。
  要求「最新一版 = tag」而非「存在該版」:新版本一定寫在最前面,tag 打錯成舊版號時也會擋下。
- `markdown <tag>`:輸出該版的 GitHub Release 內容。

只用標準函式庫,CI 不必安裝專案依賴。

用法: python tools/release_notes.py check v0.10.0
      python tools/release_notes.py markdown v0.10.0 > notes.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "frontend/i18n/releases.zh-TW.json"
DICT = ROOT / "frontend/i18n/zh-TW.json"


def load(path: Path = SOURCE) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["releases"]


def check(tag: str, releases: list[dict]) -> str | None:
    """沒問題時回傳 None,否則回傳錯誤說明。"""
    if not releases:
        return f"更新內容是空的,缺少 {tag}"
    latest = releases[0]["version"]
    if latest == tag:
        return None
    if any(r["version"] == tag for r in releases):
        return f"{tag} 不是最新一版(最新一版是 {latest});新版本要寫在 releases 的最前面"
    return f"更新內容缺少 {tag}(最新一版是 {latest}):請在 {SOURCE.relative_to(ROOT)} 等語言檔最前面加入 {tag}"


def markdown(tag: str, releases: list[dict], labels: dict[str, str]) -> str:
    release = next(r for r in releases if r["version"] == tag)
    lines = []
    if release.get("title"):
        lines += [f"## {release['title']}", ""]
    for item in release["items"]:
        kind = labels.get(f"release.kind.{item['kind']}", item["kind"])
        lines.append(f"- [{kind}] {item['text']}")
    return "\n".join(lines).strip() + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in ("check", "markdown"):
        print(__doc__, file=sys.stderr)
        return 2
    command, tag = argv[1], argv[2]
    releases = load()
    error = check(tag, releases)
    if error:
        print(f"::error::{error}" if command == "check" else error, file=sys.stderr)
        return 1
    if command == "markdown":
        labels = json.loads(DICT.read_text(encoding="utf-8"))
        sys.stdout.write(markdown(tag, releases, labels))
    else:
        print(f"{tag}:更新內容已就緒")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
