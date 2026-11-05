"""維護公告檔的共用規則(src/gash/announcement.py):伺服器的判定與發布前的提醒。"""
import json
from datetime import datetime, timezone

import pytest

from gash.announcement import AnnouncementError, announcement_warnings, languages, parse_announcement

NOW = datetime(2026, 11, 5, tzinfo=timezone.utc)
LANGS = ["zh-TW", "zh-CN", "en", "ja"]
GOOD = {"id": "m1", "until": "2026-12-01T22:30:00+08:00",
        "message": {"zh-TW": "今晚維護", "zh-CN": "今晚维护", "en": "Maintenance tonight", "ja": "今夜メンテナンス"}}


def parse(data, now=NOW):
    return parse_announcement(data if isinstance(data, str) else json.dumps(data), now)


def reason(data):
    with pytest.raises(AnnouncementError) as exc:
        parse(data)
    return exc.value.reason


def test_valid_announcement():
    assert parse(GOOD) == GOOD
    assert parse({"id": "m1", "message": {"en": "x"}})["until"] is None


@pytest.mark.parametrize("data, code", [
    ("{not json", "json"), ("[1, 2]", "json"),
    ({"message": {"en": "x"}}, "id"), ({"id": "", "message": {"en": "x"}}, "id"), ({"id": 3, "message": {"en": "x"}}, "id"),
    ({"id": "m1"}, "message"), ({"id": "m1", "message": {}}, "message"), ({"id": "m1", "message": "x"}, "message"),
    ({"id": "m1", "message": {"en": 1}}, "message"),
    ({"id": "m1", "message": {"en": "x"}, "until": "soon"}, "until"),
    ({"id": "m1", "message": {"en": "x"}, "until": 5}, "until"),
    ({"id": "m1", "message": {"en": "x"}, "until": "2026-11-04T00:00:00+08:00"}, "expired"),
    ({"id": "m1", "message": {"en": "x"}, "until": "2026-11-04T23:00:00"}, "expired"),   # 沒有時區視為 UTC
])
def test_rejections(data, code):
    assert reason(data) == code


def test_languages_follow_ui():
    assert languages() == LANGS


def test_good_announcement_has_no_warnings():
    assert announcement_warnings(parse(GOOD), LANGS) == []


def test_oct12_placeholders():
    """10/12 實際發出的公告:zh-CN 為 "123"、en / ja 為 "..."。"""
    ann = parse({"id": "2026-10-12-maint", "message": {"zh-TW": "10/12 22:00–22:30 維護,進行中的對局會中斷",
                                                       "zh-CN": "123", "en": "...", "ja": "..."}}, NOW)
    warnings = announcement_warnings(ann, LANGS)
    assert sorted(w.split(" ")[0] for w in warnings) == ["en", "ja", "zh-CN"]
    assert all("佔位文字" in w for w in warnings)


def test_missing_language_and_copy_of_zh_tw():
    ann = parse({"id": "m1", "message": {"zh-TW": "今晚維護", "zh-CN": "今晚维护", "en": "今晚維護"}})
    warnings = announcement_warnings(ann, LANGS)
    assert warnings == ["缺少 ja:該語言的玩家會看到 zh-TW 的訊息", "en 與 zh-TW 相同,可能忘了翻譯"]


def test_until_without_timezone():
    ann = parse({**GOOD, "until": "2026-12-01T22:30:00"})
    assert announcement_warnings(ann, LANGS) == ["until 沒有時區,伺服器當作 UTC,即台灣時間 2026-12-02 06:30"]
