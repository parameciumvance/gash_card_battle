"""意見回報的瀏覽器與靜態測試(battle-ui「意見回報」「首頁入口」)。瀏覽器測試需要 playwright 與 Chromium。

Run: python -m pytest tests/test_feedback_ui.py -q
"""
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(聚焦預設關閉)
from tests.test_npc_ui import open_npc_setup, start_npc
from tests.test_spotlight_ui import open_page

ROOT = Path(__file__).resolve().parents[1]
FORM = "https://docs.google.com/forms/d/e/TEST/viewform"
ENTRY = "entry.42"


def set_form(page, url=FORM, entry=ENTRY):
    page.evaluate(f"FEEDBACK.formUrl = '{url}'; FEEDBACK.contextEntry = '{entry}'")


def form_context(page):
    """表單連結預填的環境資訊。"""
    href = page.locator("#info-body a.feedback-form").get_attribute("href")
    assert href.startswith(FORM + "?")
    query = parse_qs(urlsplit(href).query)
    assert query["usp"] == ["pp_url"]
    return query[ENTRY][0]


def test_landing_entry_opens_feedback(page):
    set_form(page)
    page.locator("#entry-feedback").click()
    assert page.locator("#info-overlay").is_visible()
    assert page.locator("#info-title").text_content() == "意見回報"
    form = page.locator("#info-body a.feedback-form")
    github = page.locator("#info-body a.feedback-github")
    assert form.get_attribute("target") == "_blank" and github.get_attribute("target") == "_blank"
    assert "noopener" in github.get_attribute("rel")
    assert github.get_attribute("href").endswith("/issues/new/choose")
    assert "GitHub 帳號" in page.locator("#info-body .feedback-channel", has=page.locator("a.feedback-github")).text_content()
    ctx = form_context(page)
    assert ctx.startswith("lang=zh-TW;") and "ua=" in ctx and "mode=" not in ctx
    assert page.locator("#info-body .feedback-context").text_content() == ctx
    page.locator("#info-close").click()
    assert not page.locator("#info-overlay").is_visible()
    assert page.locator("#landing").is_visible()


def test_without_form_only_github(page):
    set_form(page, url="", entry="")
    page.locator("#feedback-toggle").click()
    assert page.locator("#info-body a.feedback-form").count() == 0
    assert page.locator("#info-body a.feedback-github").count() == 1
    assert page.locator("#info-body .feedback-context").text_content().startswith("lang=zh-TW;")


def test_copy_context(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server)
    context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.locator("#feedback-toggle").click()
    page.locator("#info-body .feedback-copy").click()
    page.wait_for_function("navigator.clipboard.readText().then(t => t.startsWith('lang='))")
    assert page.evaluate("navigator.clipboard.readText()") == \
        page.locator("#info-body .feedback-context").text_content()
    context.close()
    assert not errors


def test_in_game_context_and_play_continues(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, prefs={"spotlight": "off"})
    set_form(page)
    open_npc_setup(page)
    page.fill("#name-npc", "小美")
    page.select_option("#npc-level", "dummy")
    start_npc(page)
    page.wait_for_function("R.awaited_player === 0", timeout=20000)
    page.locator("#feedback-toggle").click()
    ctx = form_context(page)
    head, ua = ctx.split("; ua=")                                         # 瀏覽器字串本身含「; 」,放在最後
    fields = dict(part.split("=", 1) for part in head.split("; "))
    assert ua == page.evaluate("navigator.userAgent")
    assert fields["mode"] == "npc"
    assert fields["room"] == page.evaluate("SESSION.code")
    assert fields["turn"] == str(page.evaluate("S.turn_no"))
    assert fields["phase"] == page.evaluate("S.phase")
    token = page.evaluate("SESSION.tokens.me")
    assert token not in ctx and "小美" not in ctx

    before = page.evaluate("S.event_count")
    page.evaluate("""async () => {
        if (S.phase === 'start') await send({type: 'flip_pages', player: 0, count: 0});
        await send({type: 'pass', player: 0});
    }""")
    page.wait_for_function(f"S.event_count > {before} + 2", timeout=20000)   # NPC 照常回應並推送
    assert page.locator("#info-overlay").is_visible()
    page.locator("#info-close").click()
    assert not page.locator("#info-overlay").is_visible()
    context.close()
    assert not errors


# ---------------------------------------------------------------- GitHub Issue Forms

def test_issue_forms_have_environment_field():
    yaml = pytest.importorskip("yaml")
    folder = ROOT / ".github/ISSUE_TEMPLATE"
    forms = sorted(p.name for p in folder.glob("*.yml") if p.name != "config.yml")
    assert forms == ["bug.yml", "card-effect.yml", "suggestion.yml"]
    for name in forms:
        form = yaml.safe_load((folder / name).read_text(encoding="utf-8"))
        assert form["name"] and form["description"]
        ids = [item.get("id") for item in form["body"]]
        assert "environment" in ids, name
    config = yaml.safe_load((folder / "config.yml").read_text(encoding="utf-8"))
    assert config["blank_issues_enabled"] is True


def test_context_and_landing_show_version(page):
    ver = page.evaluate("META.version")
    assert ver
    assert page.locator("#landing-version").inner_text() == f"版本 {ver}"
    page.locator("#feedback-toggle").click()
    ctx = page.locator("#info-body .feedback-context").text_content()
    assert ctx.startswith(f"lang=zh-TW; ver={ver}; ")
