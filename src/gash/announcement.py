"""維護公告檔的規則(battle-api「維護公告」):伺服器讀檔與 tools/vps.py 發布前的驗證共用,兩邊判定一致。

- parse_announcement:伺服器會不會顯示這則公告;不顯示時丟出 AnnouncementError,reason 為
  json(不是 JSON 物件)/ id / message / until(無法解析)/ expired(已過 until)。
- announcement_warnings:只給發布前提醒用(缺語言、佔位文字、與 zh-TW 相同、until 沒有時區),不影響伺服器。
"""

from __future__ import annotations

import json
import unicodedata
from datetime import datetime, timedelta, timezone

from .paths import frontend_dir

FALLBACK_LANG = "zh-TW"
TAIPEI = timezone(timedelta(hours=8))


class AnnouncementError(ValueError):
    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def parse_announcement(text: str, now: datetime | None = None) -> dict:
    """公告檔內容 → {"id", "message", "until"};伺服器不會顯示時丟出 AnnouncementError。"""
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise AnnouncementError("json", str(exc)) from None
    if not isinstance(data, dict):
        raise AnnouncementError("json", "不是 JSON 物件")
    ann_id, message, until = data.get("id"), data.get("message"), data.get("until")
    if not isinstance(ann_id, str) or not ann_id:
        raise AnnouncementError("id")
    if not isinstance(message, dict) or not message or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in message.items()):
        raise AnnouncementError("message")
    if until is not None:
        end = until_datetime(until)
        if end <= (now or datetime.now(timezone.utc)):
            raise AnnouncementError("expired", until)
    return {"id": ann_id, "message": message, "until": until}


def until_datetime(until) -> datetime:
    """until 的時間;沒有時區視為 UTC(與伺服器相同)。"""
    if not isinstance(until, str):
        raise AnnouncementError("until", repr(until))
    try:
        end = datetime.fromisoformat(until)
    except ValueError:
        raise AnnouncementError("until", until) from None
    return end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end


def languages() -> list[str]:
    """介面支援的語言代碼(frontend/i18n/languages.json)。"""
    data = json.loads((frontend_dir() / "i18n/languages.json").read_text(encoding="utf-8"))
    return [lang["code"] for lang in data]


def _looks_like_placeholder(text: str) -> bool:
    """沒有任何文字字元(如 "..."、"123"、空字串)。"""
    return not any(unicodedata.category(ch).startswith("L") for ch in text)


def announcement_warnings(ann: dict, langs: list[str] | None = None) -> list[str]:
    """parse_announcement 通過的公告中可能是人為錯誤的地方(繁中說明)。"""
    langs = languages() if langs is None else langs
    message = ann["message"]
    warnings = []
    for lang in langs:
        if lang not in message:
            fallback = FALLBACK_LANG if FALLBACK_LANG in message else "其他語言"
            warnings.append(f"缺少 {lang}:該語言的玩家會看到 {fallback} 的訊息")
    for lang, text in message.items():
        if _looks_like_placeholder(text.strip()):
            warnings.append(f"{lang} 像佔位文字:{text!r}")
        elif lang != FALLBACK_LANG and text == message.get(FALLBACK_LANG):
            warnings.append(f"{lang} 與 {FALLBACK_LANG} 相同,可能忘了翻譯")
    until = ann.get("until")
    if until is not None and datetime.fromisoformat(until).tzinfo is None:
        local = until_datetime(until).astimezone(TAIPEI).strftime("%Y-%m-%d %H:%M")
        warnings.append(f"until 沒有時區,伺服器當作 UTC,即台灣時間 {local}")
    return warnings
