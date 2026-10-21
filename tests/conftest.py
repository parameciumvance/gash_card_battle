"""共用的瀏覽器測試 fixture(test-speed):伺服器整個測試期間只啟動一次(session scope);Chromium 每個測試檔
啟動一次(module scope:Playwright 的同步 API 在主執行緒留著事件迴圈,開整個 session 會讓之後用 asyncio 的
測試失敗),每個測試仍各自開新的 browser context(localStorage、路由互不影響)。"""
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[1]


def pytest_collection_modifyitems(config, items):
    """用到 browser fixture 的測試自動標 browser(開發中可用 -m "not slow and not browser" 只跑引擎與 API)。"""
    for item in items:
        if "browser" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.browser)


@pytest.fixture(scope="session")
def server():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "gash.api.app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                with urlopen(base + "/api/meta", timeout=1):
                    break
            except OSError:
                if process.poll() is not None:
                    pytest.fail("Browser test server exited")
                time.sleep(.05)
        else:
            pytest.fail("Browser test server did not start")
        yield base
    finally:
        process.terminate()
        process.wait(timeout=10)


# 首頁會跳出最新一版的更新內容(battle-ui「更新內容」),遮罩會擋住操作。每個 context 預設把
# repo 中最新一版記為已確認(只在尚未記錄時寫入,不覆蓋測試自己設的值);更新內容的測試另以 route 換成更新的版本
LATEST_RELEASE = json.loads((ROOT / "frontend/i18n/releases.zh-TW.json").read_text(encoding="utf-8"))["releases"][0]["version"]
SEEN_RELEASE_SCRIPT = (f"if (localStorage.getItem('gash-release-seen') === null) "
                       f"localStorage.setItem('gash-release-seen', '{LATEST_RELEASE}');")


class _Browser:
    """Chromium 包一層:new_context 自動加上 SEEN_RELEASE_SCRIPT,其餘照原物件。"""

    def __init__(self, instance):
        self._instance = instance

    def new_context(self, **kwargs):
        context = self._instance.new_context(**kwargs)
        context.add_init_script(SEEN_RELEASE_SCRIPT)
        return context

    def __getattr__(self, name):
        return getattr(self._instance, name)


@pytest.fixture(scope="module")
def browser():
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as runtime:
        try:
            instance = runtime.chromium.launch()
        except pw.Error as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield _Browser(instance)
        instance.close()


@pytest.fixture
def page(browser, server):
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale="zh-TW")
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")  # 聚焦遮罩會擋住操作;聚焦測試另開
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0 && document.querySelector('#cheat-toggle').textContent")
    yield page
    context.close()
    assert not errors
