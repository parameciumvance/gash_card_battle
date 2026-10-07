"""前端資源每次確認更新、卡圖回應標頭(battle-api「前端資源每次確認更新」「卡圖回應標頭」)。"""
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from starlette.routing import Mount

from gash.api.app import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]
WEEK = "public, max-age=604800"


def write_card_art(assets: Path, number="S-001"):
    (assets / "cards").mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(buf, "WEBP")
    (assets / "cards" / f"{number}.webp").write_bytes(buf.getvalue())


@pytest.fixture
def art_dir(tmp_path, monkeypatch):
    """/static/assets/ 暫時改由暫存目錄提供,內含一張 S-001.webp;不依賴本機有沒有下載卡圖。"""
    mount = next(r for r in app.routes if isinstance(r, Mount) and r.path == "/static/assets")
    monkeypatch.setattr(mount.app, "all_directories", [tmp_path])
    write_card_art(tmp_path)
    return tmp_path


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


def test_api_not_marked():
    assert "cache-control" not in client.get("/api/meta").headers


def test_card_art_cached_for_a_week(art_dir):
    res = client.get("/static/assets/cards/S-001.webp")
    assert res.status_code == 200
    assert res.headers["cache-control"] == WEEK
    again = client.get("/static/assets/cards/S-001.webp", headers={"If-None-Match": res.headers["etag"]})
    assert again.status_code == 304
    assert again.headers["cache-control"] == WEEK


def test_missing_card_art_not_cached(art_dir):
    res = client.get("/static/assets/cards/ZZ-999.webp")
    assert res.status_code == 404
    assert "max-age" not in res.headers.get("cache-control", "")


# 模擬 python:3.12-slim:沒有 /etc/mime.types,.webp 只在非嚴格的 common_types
WEBP_WITHOUT_SYSTEM_MIME = r'''
import mimetypes
mimetypes.knownfiles = []
mimetypes.init()
mimetypes._db.types_map[True].pop(".webp", None)
from fastapi.testclient import TestClient
assert mimetypes.guess_type("x.webp")[0] is None, "模擬失敗"
from gash.api.app import app
print(TestClient(app).get("/static/assets/cards/S-001.webp").headers["content-type"])
'''


def test_webp_content_type_without_system_mime(tmp_path):
    write_card_art(tmp_path)
    out = subprocess.run([sys.executable, "-c", WEBP_WITHOUT_SYSTEM_MIME], cwd=ROOT, capture_output=True,
                         text=True, timeout=60, env={**os.environ, "GASH_ASSETS_DIR": str(tmp_path)})
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "image/webp"
