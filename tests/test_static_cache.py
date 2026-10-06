"""前端資源每次確認更新(battle-api「前端資源每次確認更新」)。"""
import pytest
from fastapi.testclient import TestClient

from gash.api.app import app

client = TestClient(app)


@pytest.mark.parametrize("path", ["/", "/static/app.js", "/static/style.css",
                                  "/static/i18n/zh-TW.json", "/data/cards.json"])
def test_frontend_files_revalidate(path):
    res = client.get(path)
    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-cache"
    assert res.headers["etag"]


def test_unchanged_file_returns_304():
    etag = client.get("/static/app.js").headers["etag"]
    res = client.get("/static/app.js", headers={"If-None-Match": etag})
    assert res.status_code == 304
    assert res.content == b""
    assert res.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("path", ["/static/assets/cards/S-001.webp", "/api/meta"])
def test_card_art_and_api_not_marked(path):
    assert "no-cache" not in client.get(path).headers.get("cache-control", "")
