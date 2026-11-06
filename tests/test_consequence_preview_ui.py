"""後果預告的畫面(battle-ui「保護的後果提示」「翻頁按鈕的落敗提示」)。需要 playwright 與 Chromium。

保護決策與翻頁落敗的資料以注入快照模擬(判定本身由 tests/test_consequence_preview.py 驗證)。

Run: python -m pytest tests/test_consequence_preview_ui.py -q
"""
from tests.test_book_browse_ui import nav, start_local
from tests.test_choice_ui import sent, set_pending, start, two_same_mamodo

WARNING = "保護後這隻魔物會被棄掉"


def protect_with_outcomes(page, reason):
    """自己場上兩隻同名魔物都能保護:第 1 隻沒有標示,第 2 隻標示會離場(reason)。"""
    p = start(page)
    uids = two_same_mamodo(page, p)
    top = page.evaluate("(p) => S.players[p].slots[0].top", p)
    options = [{"value": None, "label": "no_protect"},
               {"value": uids[0], "card": top, "zone": "slot", "player": p, "slot": uids[0]},
               {"value": uids[1], "card": top, "zone": "slot", "player": p, "slot": uids[1],
                "leaves": True, "leave_reason": reason}]
    set_pending(page, {"kind": "protect", "player": p, "source": None, "options": options})
    return p, uids


def slot_el(page, uid):
    return page.locator(f'[data-zone-kind="mamodo"][data-slot-uid="{uid}"]')


def test_menu_warns_above_pick_and_still_allows_it(page):
    p, uids = protect_with_outcomes(page, "P-012")
    slot_el(page, uids[1]).click()
    warning = page.locator("#card-menu .card-menu-warning")
    assert warning.text_content() == f"⚠ {WARNING}(雪莉 P-012)"
    pick = page.locator("#card-menu button", has_text="選擇")
    assert pick.is_enabled()
    # 警告在「選擇」上方
    assert warning.bounding_box()["y"] < pick.bounding_box()["y"]
    pick.click()
    assert sent(page) == [{"type": "choose", "player": p, "value": uids[1]}]


def test_injured_reason_text(page):
    p, uids = protect_with_outcomes(page, "injured")
    slot_el(page, uids[1]).click()
    assert page.locator("#card-menu .card-menu-warning").text_content() == f"⚠ {WARNING}(已負傷)"


def test_unmarked_option_has_no_warning(page):
    p, uids = protect_with_outcomes(page, "P-012")
    slot_el(page, uids[1]).click()
    slot_el(page, uids[0]).click()                                        # 改選另一隻
    assert page.locator("#card-menu button", has_text="選擇").count() == 1
    assert page.locator("#card-menu .card-menu-warning").count() == 0


def test_zoom_and_detail_panel_show_warning(page):
    p, uids = protect_with_outcomes(page, "P-012")
    slot_el(page, uids[1]).hover()                                        # 寬螢幕:詳情面板
    assert WARNING in page.locator("#detail-panel .detail-warning").text_content()
    slot_el(page, uids[0]).hover()
    assert page.locator("#detail-panel .detail-warning").count() == 0
    slot_el(page, uids[1]).click()
    page.locator("#card-menu button", has_text="詳情").click()           # 放大檢視
    assert WARNING in page.locator("#zoom-actions .zoom-warning").text_content()


def flip_button(page, text):
    return page.locator("#action-bar button", has_text=text)


def test_flip_button_notes_end_of_turn_loss(page):
    tp = start_local(page)
    page.evaluate(f"""() => {{
        S = {{...S, players: S.players.map((x, i) => i === {tp} ? {{...x, flip_end_loses: [false, false, true, true]}} : x)}};
        render();
    }}""")
    assert "落敗" not in flip_button(page, "不翻頁").text_content()
    nav(page, tp, "next").click()
    assert "落敗" not in flip_button(page, "翻 1 張").text_content()
    nav(page, tp, "next").click()
    btn = flip_button(page, "翻 2 張")
    assert "flip-loses" in btn.get_attribute("class")
    assert btn.locator(".btn-note").text_content() == "⚠ 翻頁後,本回合結束時將因無頁可翻而落敗"
