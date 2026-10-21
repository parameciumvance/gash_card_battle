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


def test_extra_cost_buttons(page):
    # battle-ui「追加費用與效果選擇的選項文字」:S-067 的追加費用以行動欄按鈕呈現
    p = start(page)
    opts = [{"value": v, "label": "extra_cost", "amount": v, "power": v * 1000, "damage": v // 2} for v in (0, 2, 4)]
    set_pending(page, {"kind": "spell_extra_cost", "player": p, "source": "S-067", "options": opts})
    buttons = page.locator("#action-bar .choice-prompt .choice-options button")
    assert buttons.all_text_contents() == ["不追加", "追加 2(魔力 +2000、傷害 +1)", "追加 4(魔力 +4000、傷害 +2)"]
    buttons.nth(2).click()
    assert sent(page) == [{"type": "choose", "player": p, "value": 4}]


def test_any_page_spell_buttons_per_page(page):
    # M-037:範圍內有多張可用的戰術時,每一頁各一個按鈕(標出頁碼),按下開該頁的放大檢視
    p = start(page)
    page.evaluate("""(p) => {
        const users = [{slot_uid: S.players[p].slots[0].uid, cost: 2}];
        S = {...S, phase: 'battle', turn_player: p, action_player: p, battle: null, battle_in: null,
             players: S.players.map((x, i) => i !== p ? x : {...x, mp: 10, any_page_spells: [
               {page: 5, card: 'S-065', cost: 2, users}, {page: 7, card: 'S-066', cost: 2, users}]})};
        render();
    }""", p)
    buttons = page.locator("#action-bar button", has_text="從魔書使用")
    assert buttons.count() == 2
    assert "第 7 頁" in buttons.nth(1).text_content()
    buttons.nth(1).click()
    assert page.locator("#zoom-overlay").is_visible()
    assert page.evaluate("ZOOM.ctx.kind === 'any_page' && ZOOM.ctx.page") == 7


def test_s098_target_shown_in_log_and_effects(page):
    start(page)
    line = page.evaluate("logLine({type: 'standby_set', kind: 'spell_reuse', owner: 0, source: 'S-098', card: 'S-002', page: 4})")
    assert page.evaluate("cname('S-002')") in line and "第 4 頁" in line
    text = page.evaluate("effectText({type: 'standby', kind: 'spell_reuse', source: 'S-098', owner: 0, card: 'S-002', page: 4})")
    assert page.evaluate("cname('S-002')") in text and "第 4 頁" in text


def test_protect_prompt_shows_damage(page):
    # battle-ui「保護決策顯示傷害」
    p = start(page)
    uid = page.evaluate("(p) => S.players[p].slots[0].uid", p)
    top = page.evaluate("(p) => S.players[p].slots[0].top", p)
    def prompt(info):
        set_pending(page, {"kind": "protect", "player": p, "source": None, "info": {"damage": info},
                           "options": [{"value": None, "label": "no_protect"}]})
        return page.locator("#action-bar .choice-prompt").inner_text()
    text = prompt({"kind": "book", "player": p, "amount": 3, "slot": None, "injured": False, "lethal": False})
    assert "將受到 3 點傷害" in text and "耗盡" not in text
    text = prompt({"kind": "book", "player": p, "amount": 3, "slot": None, "injured": False, "lethal": True})
    assert "將受到 3 點傷害" in text and "耗盡" in text
    text = prompt({"kind": "slot", "player": p, "amount": 1, "slot": uid, "injured": True, "lethal": False})
    assert page.evaluate("(n) => cname(n)", top) in text and "棄牌區" in text


def test_cheat_panel_shows_current_pages(page):
    # battle-ui「金手指面板的目前頁提示」
    start(page)
    page.evaluate("openCheat()")
    page.wait_for_function("CHEAT && CHEAT.players")
    pos = page.evaluate("[S.players[0].pos, S.players[1].pos]")
    summary = page.locator("#cheat-current").inner_text()
    assert f"第 {pos[0]}、{pos[0] + 1} 頁" in summary and f"第 {pos[1]}、{pos[1] + 1} 頁" in summary
    grid = page.locator("#cheat-book-grid")
    assert grid.locator(".cheat-open").count() == 2
    assert grid.locator(".cheat-gone").count() >= 1                           # 第 1 頁的魔物已放出


def test_first_player_log(page):
    start(page)
    assert page.evaluate("logLine({type: 'first_player_set', player: 0, reason: 'local'})") == \
        f"自由調查時間:{page.evaluate('pname(0)')} 先攻"


# ---------------------------------------------------------------- 第 4 批(battle-ui「第 4 批的行動與選項」「第 4 批的記錄與作用中效果」)

def test_action_discard_buttons(page):
    p = start(page)
    labels = page.evaluate("""(p) => {
        const uid = S.players[p].slots[0].uid;
        S = {...S, phase: 'battle', turn_player: p, action_player: p, battle: null, battle_in: null, pending: null,
             players: S.players.map((x, i) => i !== p ? x : {...x, slots: x.slots.map((s, j) => j !== 0 ? s :
               {...s, stack: ['M-045', 'M-046'], top: 'M-046', action_discard: true, partner: 'P-020',
                partner_ability: null, partner_action_discard: true})})};
        render();
        return [zoomActions({kind: 'slot', p, uid}).buttons.map((b) => b.label),
                zoomActions({kind: 'partner', p, uid}).buttons.map((b) => b.label)];
    }""", p)
    assert "以 1 個行動棄掉" in labels[0] and "以 1 個行動棄掉" in labels[1]
    page.evaluate("(p) => zoomActions({kind: 'slot', p, uid: S.players[p].slots[0].uid}).buttons"
                  ".find((b) => b.label === '以 1 個行動棄掉').onclick()", p)
    assert sent(page)[-1] == {"type": "use_action_effect", "player": p, "zone": "mamodo",
                              "slot_uid": page.evaluate("(p) => S.players[p].slots[0].uid", p)}


def test_mamodo_defense_button(page):
    p = start(page)
    label = page.evaluate("""(p) => {
        S = {...S, phase: 'battle', pending: null, battle_in: null,
             battle: {attacker: 1 - p, step: 'defense', attack_undefendable: false},
             players: S.players.map((x, i) => i !== p ? x : {...x, mp: 3, slots: x.slots.map((s, j) => j !== 0 ? s :
               {...s, mamodo_defense: {mp_cost: 1, power: 6500}})})};
        render();
        return zoomActions({kind: 'slot', p, uid: S.players[p].slots[0].uid}).buttons.map((b) => b.label);
    }""", p)
    assert "直接防禦(魔力6500)" in label


def test_set_heads_and_jammer_labels(page):
    start(page)
    assert page.evaluate("choiceLabel({value: 'heads:1', label: 'set_heads', coin: 1})") == "把第 2 枚改成正面"
    text = page.evaluate("choiceLabel({value: true, label: 'jammer_use', card: 'E-018', cost: 0, discard: true})")
    assert "棄掉" in text and page.evaluate("cname('E-018')") in text


def test_batch4_log_lines(page):
    start(page)
    name, card = page.evaluate("[pname(0), cname('M-034')]")
    assert page.evaluate("logLine({type: 'coin_set', player: 0, card: 'M-034', index: 0})") == \
        f"{name} 以《{card}》把第 1 枚硬幣改成正面"
    assert "1 個行動" in page.evaluate("logLine({type: 'action_effect_used', player: 0, card: 'M-046'})")
    assert "魔物效果防禦" in page.evaluate(
        "logLine({type: 'defense_declared', player: 0, spell: null, mamodo: 'M-039', slot: 1})")
    assert "不會因自己的效果增加" in page.evaluate("logLine({type: 'mp_gain_prevented', player: 0, source: 'E-032'})")


def test_batch4_effect_texts(page):
    start(page)
    uid = page.evaluate("S.players[0].slots[0].uid")
    text = page.evaluate(f"""effectText({{type: 'modifier', kind: 'power_set', source: 'M-035', owner: 0,
        target_player: 0, target_slot: {uid}, copy_card: 'M-051', duration: 'turn'}})""")
    assert page.evaluate("cname('M-051')") in text and "魔力等於" in text
    assert "魔力為 0" in page.evaluate(f"""effectText({{type: 'modifier', kind: 'power_set', source: 'P-011',
        owner: 1, target_player: 0, target_slot: {uid}, value: 0, duration: 'turn'}})""")
    block = {"type": "static", "kind": "block_family", "source": "P-031", "owner": 1, "target_player": 0,
             "target_slot": None, "mamodo": "ウマゴン", "card": "E-014"}
    assert page.evaluate("cname('E-014')") in page.evaluate("(e) => effectText(e)", block)
    assert page.evaluate("(e) => effectWhen(e)", block) == "在場上期間"


# ---------------------------------------------------------------- 第 5 批(battle-ui「結束階段效果順序的選擇」「第 5 批的記錄與作用中效果」)

def test_end_phase_order_buttons(page):
    p = start(page)
    opts = [{"value": 0, "label": "end_phase_effect", "card": "E-041", "kind": "end_phase_turn_opponent"},
            {"value": 1, "label": "end_phase_effect", "card": "E-042", "kind": "end_phase_discard"}]
    set_pending(page, {"kind": "end_phase_order", "player": p, "source": None, "options": opts})
    buttons = page.locator("#action-bar .choice-prompt .choice-options button")
    names = page.evaluate("[cname('E-041'), cname('E-042')]")
    assert buttons.all_text_contents() == [f"先解決《{names[0]}》", f"先解決《{names[1]}》"]
    buttons.nth(1).click()
    assert sent(page) == [{"type": "choose", "player": p, "value": 1}]


def test_batch5_texts(page):
    start(page)
    assert "第 4 頁與第 10 頁" in page.evaluate(
        "logLine({type: 'opponent_pages_swapped', player: 1, viewer: 0, pages: [4, 10], source: 'E-037'})")
    assert page.evaluate("effectText({type: 'modifier', kind: 'restriction', flag: 'no_attack', source: 'E-039',"
                         " owner: 0, target_player: 0, target_slot: null, duration: 'turn'})").endswith("不能攻擊")
    assert "2 隻" in page.evaluate("effectText({type: 'standby', kind: 'end_phase_discard', source: 'E-042',"
                                   " owner: 0, count: 2, expires: 'turn'})")


# ---------------------------------------------------------------- 已使用的效果按鈕停用(battle-ui「已使用的效果按鈕停用」)

def test_used_effect_buttons_disabled(page):
    p = start(page)
    result = page.evaluate("""(p) => {
        S = {...S, phase: 'battle', turn_player: p, action_player: p, battle: null, battle_in: null, pending: null,
             players: S.players.map((x, i) => i !== p ? x : {...x, mp: 10, slots: x.slots.map((s, j) => j !== 0 ? s :
               {...s, ability: {mode: 'mp', mp_cost: 1, timing: 'nonbattle', own_turn: false, per_game: false},
                ability_used: 'turn', mamodo_attack: {mp_cost: 1, power: 5000, damage: 2},
                mamodo_attack_used: 'turn'})})};
        render();
        return zoomActions({kind: 'slot', p, uid: S.players[p].slots[0].uid}).buttons
          .map((b) => [b.disabled, b.reason]);
    }""", p)
    assert result == [[True, "本回合已使用"], [True, "本回合已使用"]]
    reason = page.evaluate("""(p) => {
        S.players[p].slots[0].ability_used = 'game';
        return zoomActions({kind: 'slot', p, uid: S.players[p].slots[0].uid}).buttons[0].reason;
    }""", p)
    assert reason == "一場遊戲限 1 次,已使用"
