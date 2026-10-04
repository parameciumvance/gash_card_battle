"""回合與時機指示的瀏覽器測試(battle-ui「回合與時機指示」、「對手行動聚焦展示」的回合開始橫幅)。
需要 playwright 與 Chromium。以本機測試模式操作,並把視角設為某一方,另一方的指令即為「對手」。

Run: python -m pytest tests/test_timing_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(聚焦預設關閉)
from tests.test_spotlight_ui import open_page


def start_as(page, me):
    """開本機房;me='turn' / 'other' 時把視角設為回合玩家 / 非回合玩家,'all' 維持全視角。回傳 (回合玩家, 自己)。"""
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    return page.evaluate(f"""() => {{
        const tp = S.turn_player;
        const me = '{me}' === 'turn' ? tp : '{me}' === 'other' ? 1 - tp : null;
        if (me !== null) {{ SESSION = {{...SESSION, viewer: me}}; render(); }}
        return [tp, me];
    }}""")


def send(page, player, command):
    page.evaluate("([p, c]) => send({...c, player: p})", [player, command])


def zone_of(page, player):
    return "#zone-top" if page.evaluate(f"topPlayerIndex() === {player}") else "#zone-bottom"


def test_turn_marker_and_acting_label_in_opponent_turn(page):
    tp, me = start_as(page, "other")
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "pass"})                                     # 對手的回合、輪到自己
    page.wait_for_function(f"S.action_player === {me}")
    assert page.locator(f"{zone_of(page, tp)} .pz-head .turn-marker").count() == 1
    assert page.locator(f"{zone_of(page, me)} .pz-head .turn-marker").count() == 0
    assert page.locator(f"{zone_of(page, me)} .pz-head .acting-label").count() == 1
    assert page.locator(f"{zone_of(page, tp)} .pz-head .acting-label").count() == 0
    assert page.locator("#action-bar .summary").text_content() == "輪到你(對手的回合・非戰鬥中)"
    assert "mine" in page.locator("#action-bar").get_attribute("class")
    assert page.locator("#timing-track .current").get_attribute("data-step") == "nonbattle"


def test_timing_track_marks_defense(page):
    tp, me = start_as(page, "other")
    send(page, tp, {"type": "flip_pages", "count": 0})
    assert page.locator("#timing-track .current").get_attribute("data-step") == "nonbattle"
    send(page, tp, {"type": "declare_attack", "page": 3})
    page.wait_for_function("S.battle_in")
    assert page.locator("#timing-track .current").get_attribute("data-step") == "battle_in"
    send(page, me, {"type": "battle_in_response", "allow": True})
    page.wait_for_function("S.battle && S.battle.step === 'defense'")
    assert page.locator("#timing-track .current").get_attribute("data-step") == "defense"
    assert page.evaluate("cname('S-001')") in page.locator("#stage-content").text_content()


def test_start_phase_marked_and_opponent_waiting_summary(page):
    tp, me = start_as(page, "other")
    assert page.locator("#timing-track .current").get_attribute("data-step") == "start"
    assert page.locator("#action-bar .summary").text_content() == \
        page.evaluate(f"`等待 ${{pname({tp})}} 行動(對手的回合・開始階段)`")
    assert "mine" not in (page.locator("#action-bar").get_attribute("class") or "")


def test_hint_details_toggle_is_remembered(page):
    tp, _ = start_as(page, "all")
    send(page, tp, {"type": "flip_pages", "count": 0})
    assert page.locator("#action-bar .hint-details").count() == 0         # 缺省收起
    page.locator("#action-bar .hint-toggle").click()
    details = page.locator("#action-bar .hint-details").text_content()
    assert "宣告攻擊" in details and "攻(A)" in details
    assert "防(D)" not in details                                        # 回合玩家不能用帶「防(D)」的事件卡與非戰鬥術
    page.reload()
    page.wait_for_function("S && S.phase === 'battle'")
    assert page.locator("#action-bar .hint-details").count() == 1        # 重新整理後仍展開
    send(page, tp, {"type": "pass"})                                     # 輪到非回合玩家
    page.wait_for_function(f"S.action_player === {1 - tp}")
    details = page.locator("#action-bar .hint-details").text_content()
    assert "防(D)" in details and "宣告攻擊" not in details


GLOW_SETUP = """async (me) => {
    const token = SESSION.tokens[me];
    const headers = {'X-Player-Token': token, 'Content-Type': 'application/json'};
    const base = `/api/rooms/${SESSION.code}`;
    const d = await api(`${base}/debug-state`, {headers});
    d.players[me].book[1] = 'S-002';                                  // 第 2 頁:費用 2 的攻擊術
    d.players[me].mp = 1;                                             // 第 3 頁 S-001 費用 1 付得起
    await api(`${base}/debug-state`, {method: 'POST', headers, body: JSON.stringify(d)});
    applyPayload(await api(`${base}/state`, {headers}));
}"""


def test_usable_cards_glow(page):
    tp, me = start_as(page, "turn")
    send(page, me, {"type": "flip_pages", "count": 0})
    page.evaluate(GLOW_SETUP, me)
    page.wait_for_function(f"S.players[{me}].open_pages.some(e => e.card === 'S-002')")
    mine = zone_of(page, me)
    assert page.locator(f'{mine} .book-pages [data-card="S-001"].usable').count() == 1
    assert page.locator(f'{mine} .book-pages [data-card="S-002"].usable').count() == 0
    send(page, me, {"type": "pass"})                                     # 輪到對手
    page.wait_for_function(f"S.action_player === {1 - me}")
    assert page.locator(f"{mine} .usable").count() == 0


def test_spectator_sees_indicators_but_no_glow(page):
    tp, _ = start_as(page, "all")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.evaluate("SESSION = {...SESSION, viewer: 'spectator'}; render();")
    assert page.locator("#board .usable").count() == 0
    assert page.locator(".pz-head .turn-marker").count() == 1
    assert page.locator(".pz-head .acting-label").count() == 1
    assert page.locator("#timing-track .current").count() == 1


def test_turn_banner_every_turn(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, prefs={"spotlight": "normal"})
    tp, me = start_as(page, "other")
    page.evaluate("""() => {
        window.__spots = [];
        new MutationObserver(() => {
            const el = document.getElementById('spotlight');
            if (!el.classList.contains('hidden')) window.__spots.push(el.textContent);
        }).observe(document.getElementById('spotlight'), {attributes: true});
    }""")
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "pass"})
    send(page, me, {"type": "pass"})                                     # 自己的 pass 結束對手的回合
    page.wait_for_function("window.__spots.some(t => t.includes('你的回合'))", timeout=15000)
    send(page, me, {"type": "flip_pages", "count": 0})
    send(page, me, {"type": "pass"})
    send(page, tp, {"type": "pass"})                                     # 對手的 pass 結束自己的回合
    name = page.evaluate(f"pname({tp})")
    page.wait_for_function(f"window.__spots.some(t => t.includes('{name}的回合'))", timeout=15000)
    assert not any("回合開始" in t or "—— 第" in t for t in page.evaluate("window.__spots"))
    context.close()
    assert not errors
