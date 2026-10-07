"""發布工具 tools/release_notes.py 的測試(docker-deployment「CI 測試與建置分流」)。"""

import subprocess
import sys

from tools.release_notes import ROOT, check, load, markdown

RELEASES = [
    {"version": "v0.10.0", "date": "2026-10-08",
     "items": [{"kind": "new", "text": "對局加入音效"}, {"kind": "fix", "text": "魔本網格對齊"}]},
    {"version": "v0.9.3", "date": "2026-10-06", "items": [{"kind": "change", "text": "圖片顯示速度優化"}]},
    {"version": "v0.9.2", "date": "2026-10-06", "title": "公開上線", "items": []},
]
LABELS = {"release.kind.new": "新功能", "release.kind.fix": "修正", "release.kind.change": "調整"}


def test_check_passes_for_latest():
    assert check("v0.10.0", RELEASES) is None


def test_check_fails_when_missing():
    error = check("v0.10.1", RELEASES)
    assert "缺少 v0.10.1" in error and "v0.10.0" in error


def test_check_fails_when_tag_is_not_latest():
    assert "不是最新一版" in check("v0.9.3", RELEASES)


def test_check_fails_when_empty():
    assert "缺少 v0.1.0" in check("v0.1.0", [])


def test_markdown_lists_items_with_labels():
    assert markdown("v0.10.0", RELEASES, LABELS) == "- [新功能] 對局加入音效\n- [修正] 魔本網格對齊\n"


def test_markdown_title_only_release():
    assert markdown("v0.9.2", RELEASES, LABELS) == "## 公開上線\n"


def run(*args):
    return subprocess.run([sys.executable, "tools/release_notes.py", *args], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8")


def test_cli_uses_repository_data():
    latest = load()[0]["version"]
    assert run("check", latest).returncode == 0
    missing = run("check", "v999.0.0")
    assert missing.returncode == 1 and "v999.0.0" in missing.stderr
    out = run("markdown", latest)
    assert out.returncode == 0 and out.stdout.strip()
    assert run("markdown", "v999.0.0").returncode == 1
    assert run("bogus").returncode == 2


def test_deploy_checks_notes_before_build_and_releases_after_push():
    """deploy.yml:建置前檢查更新內容,推送映像檔後才建立 GitHub Release(實際效果於發布時確認)。"""
    text = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    steps = ["tools/release_notes.py check", "docker/build-push-action", "tools/release_notes.py markdown",
             "gh release create"]
    positions = [text.index(s) for s in steps]
    assert positions == sorted(positions)
    assert "contents: write" in text and "packages: write" in text
