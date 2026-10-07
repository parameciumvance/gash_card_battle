"""GET /api/meta 與卡圖靜態路由外部化。"""

import dataclasses

from fastapi.testclient import TestClient

from gash.api import app as app_module
from gash.api.app import app
from gash.engine.cards import card_db
from tests.test_static_cache import art_dir  # noqa: F401  暫存卡圖目錄

client = TestClient(app)


def test_meta_dev_mode():
    res = client.get("/api/meta")
    assert res.status_code == 200
    m = res.json()
    assert "tunnel_url" not in m
    a = m["assets"]
    assert isinstance(a["installed"], bool)
    assert a["expected"] == len(card_db())
    # 卡圖不在版控內,本機是否齊全取決於開發者自己下載了多少張
    assert a["count"] <= a["expected"]
    assert a["install_dir"] == str(app_module.ASSETS.dir)


def test_card_art_served_from_assets_mount(art_dir):  # noqa: F811
    res = client.get("/static/assets/cards/S-001.webp")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/")


def test_missing_art_is_404_not_error():
    res = client.get("/static/assets/cards/ZZ-999.webp")
    assert res.status_code == 404


def test_meta_counts_only_webp(tmp_path, monkeypatch):
    cards = tmp_path / "cards"
    cards.mkdir()
    for num in ("S-001", "S-002"):
        (cards / f"{num}.jpg").write_bytes(b"old")
    monkeypatch.setattr(app_module, "ASSETS", dataclasses.replace(app_module.ASSETS, dir=tmp_path))
    assert client.get("/api/meta").json()["assets"]["count"] == 0   # 舊格式不計入
    (cards / "S-001.webp").write_bytes(b"new")
    assert client.get("/api/meta").json()["assets"]["count"] == 1
