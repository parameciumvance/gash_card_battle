"""戰鬥開始確認的選項(battle-ui「戰鬥開始確認的選項」「行動選項附註」)。需要 playwright 與 Chromium。

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


def test_two_buttons_and_hint(page):
    to_battle_in(page)
    assert button(page, "進入戰鬥").locator(".btn-label").first.text_content() == "進入戰鬥"
    assert note_of(page, "進入戰鬥").startswith("接著宣告防禦或不防禦")
    assert page.locator("#action-bar button", has_text="進入戰鬥,不防禦").count() == 1
    hint = page.locator("#battle-stage").text_content()                  # 提示在對決舞台
    assert "進入戰鬥" in hint and "中斷確認" in hint
    assert "迎戰" not in hint and "迎戰" not in page.locator("#action-bar").text_content()


def test_battle_in_no_defense_answers_defense_step(page):
    tp, me = to_battle_in(page)
    page.locator("#action-bar button", has_text="進入戰鬥,不防禦").click()
    # 宣告時效果處理完、輪到自己防禦時自動送出不防禦,不再詢問
    page.wait_for_function("!S.battle || S.battle.step !== 'defense'", timeout=10000)
    assert page.evaluate("S.battle ? S.battle.defense_declared || S.battle.step : 'over'") != "defense"
    assert page.evaluate("PRESET_NO_DEFENSE") is None                    # 用過即清除,不沿用到下一場


def test_battle_in_then_choose_defense(page):
    tp, me = to_battle_in(page)
    page.locator("#action-bar button", has=page.locator(".btn-label", has_text="進入戰鬥")).first.click()
    page.wait_for_function("S.battle && S.battle.step === 'defense'")
    page.wait_for_timeout(1500)
    assert page.evaluate("S.battle.step") == "defense"                   # 照常詢問,沒有被自動回應
    assert page.locator("#action-bar button", has_text="不防禦").count() == 1


def test_preset_cleared_when_check_voided(page):
    to_battle_in(page)
    page.evaluate("""() => {
        PRESET_NO_DEFENSE = {player: 1 - S.battle_in.attacker, turn_no: S.turn_no, attacker: S.battle_in.attacker};
        S = {...S, battle_in: null, battle: null}; render();                  // 確認被中斷
    }""")
    assert page.evaluate("PRESET_NO_DEFENSE") is None


def test_japanese_terms(browser, server):  # noqa: F811
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale="ja")
    context.add_init_script("localStorage.setItem('gash-lang', 'ja'); localStorage.setItem('gash-spotlight', 'off')")
    page = context.new_page()
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    to_battle_in(page)
    labels = page.locator("#action-bar button .btn-label").all_text_contents() + \
        page.locator("#action-bar button:not(:has(.btn-label))").all_text_contents()
    assert "バトル・イン" in labels and "バトル・イン(防御しない)" in labels
    context.close()
