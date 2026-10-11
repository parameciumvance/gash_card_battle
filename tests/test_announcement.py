"""維護公告(battle-api「維護公告」):卡圖目錄下的 announcement.json,每次請求即時讀取。"""
import dataclasses
import json

import pytest
from fastapi.testclient import TestClient

from gash.api import app as app_module
from gash.api.app import app

client = TestClient(app)


@pytest.fixture
def assets(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "ASSETS", dataclasses.replace(app_module.ASSETS, dir=tmp_path))
    return tmp_path


def get():
    r = client.get("/api/announcement")
    assert r.status_code == 200
    return r.json()["announcement"]


def test_publish_and_withdraw(assets):
    assert get() is None
    (assets / "announcement.json").write_text(json.dumps({"id": "m1", "message": {"zh-TW": "今晚維護"}}),
                                              encoding="utf-8")
    assert get() == {"id": "m1", "message": {"zh-TW": "今晚維護"}, "until": None}
    (assets / "announcement.json").unlink()                                 # 撤下:不需重啟
    assert get() is None


def test_expired_announcement_hidden(assets):
    (assets / "announcement.json").write_text(json.dumps(
        {"id": "m1", "message": {"en": "x"}, "until": "2000-01-01T00:00:00+00:00"}), encoding="utf-8")
    assert get() is None
    (assets / "announcement.json").write_text(json.dumps(
        {"id": "m2", "message": {"en": "x"}, "until": "2999-01-01T00:00:00+08:00"}), encoding="utf-8")
    assert get()["id"] == "m2"


@pytest.mark.parametrize("content", ["{not json", json.dumps({"id": "m1"}), json.dumps({"message": {"en": "x"}}),
                                     json.dumps({"id": "m1", "message": {}}), json.dumps({"id": "m1", "message": "x"}),
                                     json.dumps({"id": "m1", "message": {"en": "x"}, "until": "soon"})])
def test_invalid_file_means_no_announcement(assets, content):
    (assets / "announcement.json").write_text(content, encoding="utf-8")
    assert get() is None
