"""第三彈第 1 批的瀏覽器測試(battle-ui「以對手的魔物保護」「MP 減少被擋下的記錄」)。
需要 playwright 與 Chromium。以本機測試模式操作。

Run: python -m pytest tests/test_level3_ui.py -q
"""
import pytest

from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture
from tests.test_choice_ui import pick_in_zoom, sent, set_pending, start
from tests.test_showdown_ui import ENERGY, GUARD, RECORD
from tests.test_spotlight_ui import open_page
from tests.test_timing_ui import send, start_as


def debug_edit(page, js_body):
    """讀出 debug-state,以 js_body 修改 data(可用變數 data),再寫回。"""
    page.evaluate(f"""async () => {{
      const base = `/api/rooms/${{SESSION.code}}`;
      const headers = {{'X-Player-Token': Object.values(SESSION.tokens)[0], 'Content-Type': 'application/json'}};
      const data = await api(`${{base}}/debug-state`, {{headers}});
      {js_body}
      await api(`${{base}}/debug-state`, {{method: 'POST', headers, body: JSON.stringify(data)}});
    }}""")


def test_protect_option_on_opponent_board(page):
    p = start(page)
    opp_uid = page.evaluate("(p) => S.players[1 - p].slots[0].uid", p)
    opp_top = page.evaluate("(p) => S.players[1 - p].slots[0].top", p)
    set_pending(page, {"kind": "protect", "player": p, "source": None,
                       "options": [{"value": None, "label": "no_protect"},
                                   {"value": opp_uid, "card": opp_top, "zone": "slot", "player": 1 - p, "slot": opp_uid}]})
    card = page.locator(f'[data-zone-kind="mamodo"][data-slot-uid="{opp_uid}"]')
    assert "pickable" in card.get_attribute("class")                        # 對手場上的魔物發光可選
    card.click()
    pick_in_zoom(page)
    assert sent(page) == [{"type": "choose", "player": p, "value": opp_uid}]


@pytest.fixture
def anim_page(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, motion="no-preference", prefs={"spotlight": "off"})
    yield page
    context.close()
    assert not errors


def test_opponent_mamodo_guards_own_book(anim_page):
    page = anim_page
    tp, _ = start_as(page, "all")
    dp = 1 - tp
    # 防禦方:第 2 頁放ゾボロン、第 6 頁放ヒゲ;先放出ゾボロン,再以 M-041 從魔書裝上ヒゲ
    debug_edit(page, f"data.players[{dp}].book[1] = 'M-041'; data.players[{dp}].book[5] = 'P-027';"
                     f"data.players[{dp}].mp = 5;")
    page.evaluate(RECORD)
    page.evaluate(ENERGY)
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "pass"})
    page.wait_for_function(f"S.action_player === {dp}")
    send(page, dp, {"type": "play_card", "page": 2})
    page.wait_for_function(f"S.players[{dp}].slots.some((s) => s.top === 'M-041')")
    send(page, tp, {"type": "pass"})
    page.wait_for_function(f"S.action_player === {dp}")
    zoboron = page.evaluate(f"S.players[{dp}].slots.find((s) => s.top === 'M-041').uid")
    send(page, dp, {"type": "use_field_ability", "zone": "mamodo", "slot_uid": zoboron})
    page.wait_for_function(f"S.players[{dp}].slots.some((s) => s.partner === 'P-027') && S.action_player === {tp}")
    send(page, tp, {"type": "declare_attack", "page": 3})
    page.wait_for_function("S.battle_in")
    send(page, dp, {"type": "battle_in_response", "allow": True})
    page.wait_for_function("S.battle && S.battle.step === 'defense'")
    send(page, dp, {"type": "no_defense"})
    page.wait_for_function("S.battle && S.battle.step === 'effects'")
    send(page, tp, {"type": "pass"})
    page.wait_for_function(f"S.battle && S.battle.effect_turn === {dp}")
    send(page, dp, {"type": "use_field_ability", "zone": "partner", "slot_uid": zoboron})
    page.wait_for_function(f"S.battle && S.battle.effect_turn === {tp}")    # 唯一的對手魔物:自動選擇
    send(page, tp, {"type": "pass"})
    page.wait_for_function(f"S.battle && S.battle.effect_turn === {dp}")
    send(page, dp, {"type": "pass"})
    page.wait_for_function("S.pending && S.pending.kind === 'protect'", timeout=8000)
    attacker = page.evaluate(f"S.players[{tp}].slots[0].uid")
    page.evaluate(GUARD)
    send(page, dp, {"type": "choose", "value": attacker})
    page.wait_for_function("window.__energy.some(e => e.impact)", timeout=5000)
    assert page.evaluate("window.__guard")[0] == {"add": f"book-{dp}"}       # 移到受方魔書前
    impact = next(e for e in page.evaluate("window.__energy") if e.get("impact"))
    cover = page.evaluate(f"""(() => {{
        const r = document.querySelector('.player-zone[data-player="{dp}"] .book-cover').getBoundingClientRect();
        return {{x: r.left + r.width / 2, y: r.top + r.height / 2}};
    }})()""")
    assert abs(impact["x"] - cover["x"]) < 40 and abs(impact["y"] - cover["y"]) < 60
    page.wait_for_function(f"S.players[{tp}].slots[0].injured")               # 對手的魔物負傷
    names = page.evaluate(f"[pname({dp}), pname({tp}), cname(S.players[{tp}].slots[0].top)]")
    page.wait_for_function("!document.querySelector('.fx-guard-wrap')", timeout=5000)
    log = page.locator("#log").inner_text()
    assert f"{names[0]} 以{names[1]}的《{names[2]}》保護魔書" in log


def test_mp_reduction_prevented_log(page):
    start(page)
    line = page.evaluate("logLine({type: 'mp_reduction_prevented', player: 0, source: 'E-018'})")
    assert "MP 不會因對手的效果減少" in line and page.evaluate("cname('E-018')") in line


def test_event_cost_from_snapshot(page):
    # 對手場上有 M-040:快照的事件卡費用含 +1,卡面與「使用」都依它判斷(battle-ui「事件卡的費用加成與公開的翻開頁」)
    p = start(page)
    page.evaluate("""(p) => {
        const ps = S.players[p];
        const pg = ps.open_pages[1].page;
        S = {...S, phase: 'battle', action_player: p, players: S.players.map((x, i) => i !== p ? x : {...x, mp: 2,
             open_pages: x.open_pages.map((e) => e.page === pg ? {...e, card: 'E-032', cost: 3} : e)})};
        render();
        zoom('E-032', {kind: 'page', p, page: pg});
    }""", p)
    assert "費用 3" in page.locator("#zoom-card .cmeta").text_content()
    use = page.locator("#zoom-actions button", has_text="使用")
    assert use.is_disabled() and "MP < 3" in page.locator("#zoom-actions").inner_text()


def test_revealed_opponent_pages_show_faces(page):
    # P-024:快照含對手翻開頁的卡號時以卡面顯示,放大檢視沒有行動按鈕
    p = start(page)
    opp = 1 - p
    page.evaluate("""([p, opp]) => {
        SESSION = {...SESSION, viewer: p};
        S = {...S, players: S.players.map((x, i) => i !== opp ? x : {...x,
             open_pages: x.open_pages.map((e) => ({page: e.page, card: 'S-001', cost: 1}))})};
        render();
    }""", [p, opp])
    faces = page.locator(f'.player-zone[data-player="{opp}"] .book-pages [data-card="S-001"]')
    assert faces.count() == 2
    faces.first.click()
    assert page.locator("#zoom-overlay").is_visible() and page.locator("#zoom-actions button").count() == 0
