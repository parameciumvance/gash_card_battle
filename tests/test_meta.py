"""GET /api/meta 與卡圖靜態路由外部化。"""

from fastapi.testclient import TestClient

from gash.api import app as app_module
from gash.api.app import app
from gash.engine.cards import card_db

client = TestClient(app)


def test_meta_dev_mode():
    res = client.get("/api/meta")
    assert res.status_code == 200
    m = res.json()
    assert m["tunnel_url"] is None
    a = m["assets"]
    assert a["installed"] is True
    assert a["expected"] == len(card_db())
    # S-042 是新卡,沒有舊卡圖可沿用,repo 內卡圖少這 1 張是已知情況
    assert a["count"] == a["expected"] - 1
    assert a["install_dir"]


def test_meta_reports_tunnel_url():
    app_module.launch_info["tunnel_url"] = "https://example.trycloudflare.com"
    try:
        assert client.get("/api/meta").json()["tunnel_url"] == "https://example.trycloudflare.com"
    finally:
        app_module.launch_info["tunnel_url"] = None


def test_card_art_served_from_assets_mount():
    # 開發模式等價:既有卡圖 URL 照常回應
    res = client.get("/static/assets/cards/S-001.jpg")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/")


def test_missing_art_is_404_not_error():
    res = client.get("/static/assets/cards/ZZ-999.jpg")
    assert res.status_code == 404
