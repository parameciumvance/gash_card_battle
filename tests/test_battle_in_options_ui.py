"""進入戰鬥確認的用語與提示(battle-ui「進入戰鬥確認的用語與提示」「行動選項附註」)。需要 playwright 與 Chromium。

以本機房實際進行:回合玩家以第 3 頁的戰術宣告攻擊,自己(非回合玩家)回應。瀏覽器測試預設關閉自動 pass,
不會替測試回應防禦。

Run: python -m pytest tests/test_battle_in_options_ui.py -q
"""
from tests.test_timing_ui import send, start_as
from tests.test_turn_dial_ui import button, note_of


def to_battle_in(page):
    tp, me = start_as(page, "other")
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "declare_attack", "page": 3})
    page.wait_for_function("S.battle_in")
    return tp, me


def test_button_and_hint(page):
    to_battle_in(page)
    assert button(page, "同意進入戰鬥").locator(".btn-label").first.text_content() == "同意進入戰鬥"
    assert note_of(page, "同意進入戰鬥").startswith("接著宣告防禦或不防禦")
    labels = page.locator("#action-bar button .btn-label").all_text_contents() + \
        page.locator("#action-bar button:not(:has(.btn-label))").all_text_contents()
    assert not any("不防禦" in label for label in labels)                  # 不提供「進入戰鬥,不防禦」
    hint = page.locator("#battle-stage").text_content()                  # 提示在對決舞台
    assert "進入戰鬥確認" in hint and "同意進入戰鬥" in hint and "確認無效" in hint
    assert "迎戰" not in hint and "迎戰" not in page.locator("#action-bar").text_content()


def test_battle_in_then_choose_defense(page):
    tp, me = to_battle_in(page)
    page.locator("#action-bar button", has=page.locator(".btn-label", has_text="同意進入戰鬥")).first.click()
    page.wait_for_function("S.battle && S.battle.step === 'defense'")
    page.wait_for_timeout(1500)
    assert page.evaluate("S.battle.step") == "defense"                   # 照常詢問,沒有被自動回應
    assert page.locator("#action-bar button", has_text="不防禦").count() == 1


def test_japanese_terms(browser, server):  # noqa: F811
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale="ja")
    context.add_init_script("localStorage.setItem('gash-lang', 'ja'); localStorage.setItem('gash-spotlight', 'off')")
    page = context.new_page()
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    to_battle_in(page)
    labels = page.locator("#action-bar button .btn-label").all_text_contents() + \
        page.locator("#action-bar button:not(:has(.btn-label))").all_text_contents()
    assert "バトル・インを認める" in labels
    context.close()
