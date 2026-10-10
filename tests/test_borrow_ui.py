"""E-010 借用效果入口與 E-021 效果選擇的瀏覽器測試(battle-ui「借用效果的使用入口」、card-effects E-021)。
需要 playwright 與 Chromium。以本機測試模式操作。

Run: python -m pytest tests/test_borrow_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)


def start_local(page):
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")


def send(page, command):
    """送出指令並等待盤面更新。"""
    page.evaluate("c => send(c)", command)


def set_book(page, player, page_no, card, mp=None):
    """以金手指把某玩家魔書的一頁換成指定卡(可同時設定 MP)。"""
    page.evaluate("""async ([player, pageNo, card, mp]) => {
      const base = `/api/rooms/${SESSION.code}`;
      const headers = {'X-Player-Token': Object.values(SESSION.tokens)[0], 'Content-Type': 'application/json'};
      const data = await api(`${base}/debug-state`, {headers});
      data.players[player].book[pageNo - 1] = card;
      if (mp !== null) data.players[player].mp = mp;
      await api(`${base}/debug-state`, {method: 'POST', headers, body: JSON.stringify(data)});
    }""", [player, page_no, card, mp])


def borrow_partner(page):
    """對手(非先攻方)在自己的回合裝上與起始魔物對應的搭檔;回到先攻方的回合使用 E-010 借用它。
    回傳 (借用者, 對手, 搭檔卡號)。"""
    tp, op = page.evaluate("[S.turn_player, 1 - S.turn_player]")
    partner = page.evaluate("""(op) => {
      const top = S.players[op].slots[0].top;
      return Object.values(CARDS).find((c) => c.type === 'partner'
        && c.related_mamodo === CARDS[top].related_mamodo && c.number !== 'P-006').number;
    }""", op)
    set_book(page, op, 2, partner)
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    send(page, {"type": "pass", "player": tp})
    send(page, {"type": "pass", "player": op})
    page.wait_for_function(f"S.turn_player === {op} && S.phase === 'start'")
    send(page, {"type": "flip_pages", "player": op, "count": 0})
    send(page, {"type": "play_card", "player": op, "page": 2})
    page.wait_for_function(f"S.players[{op}].slots[0].partner === '{partner}'")
    send(page, {"type": "pass", "player": tp})
    send(page, {"type": "pass", "player": op})
    page.wait_for_function(f"S.turn_player === {tp} && S.phase === 'start'")
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page_no = page.evaluate(f"S.players[{tp}].open_pages[0].page")       # 先攻方目前翻開的頁
    set_book(page, tp, page_no, "E-010", mp=10)
    send(page, {"type": "use_book_card", "player": tp, "page": page_no})
    send(page, {"type": "pass", "player": op})
    page.wait_for_function(f"S.action_player === {tp} && S.effects.some((e) => e.kind === 'borrow_partner')")
    return tp, op, partner


def borrow_button(page):
    return page.locator("#action-bar button", has_text="借用效果")


def test_borrowed_effect_from_action_bar(page):
    start_local(page)
    tp, op, partner = borrow_partner(page)
    name = page.evaluate(f"cname('{partner}')")
    assert borrow_button(page).text_content() == f"借用效果:{name}"
    borrow_button(page).click()
    page.wait_for_function("!document.getElementById('zoom-overlay').classList.contains('hidden')")
    assert page.locator("#zoom-card .cnum").text_content() == partner
    use = page.locator("#zoom-actions button", has_text="使用")
    assert use.is_enabled()
    use.click()
    page.wait_for_function("S.effects.some((e) => e.kind === 'borrow_partner' && e.used)")
    assert page.evaluate(f"S.players[{op}].slots[0].partner") == partner      # 對手的搭檔仍在場上
    assert borrow_button(page).count() == 0
    assert page.evaluate("effectText(S.effects.find((e) => e.kind === 'borrow_partner'))").endswith("(本回合已使用)")
    log = page.locator("#log").inner_text()
    assert "以《" in log and name in log                                     # 記錄顯示為使用者經 E-010 使用


def test_entry_remains_after_partner_left(page):
    start_local(page)
    tp, op, partner = borrow_partner(page)
    page.evaluate(f"S = {{...S, players: S.players.map((p, i) => i === {op} ? {{...p, slots: p.slots.map((s) => ({{...s, partner: null}}))}} : p)}}; render()")
    assert borrow_button(page).count() == 1
    borrow_button(page).click()
    assert page.locator("#zoom-actions button", has_text="使用").is_enabled()


def test_battle_timing_borrow_disabled_outside_battle(page):
    start_local(page)
    tp, op, partner = borrow_partner(page)
    page.evaluate("""() => {
      S = {...S, effects: S.effects.map((e) => e.kind === 'borrow_partner'
        ? {...e, card: 'P-003', ability: {...e.ability, timing: 'battle'}} : e)};
      render();
    }""")
    borrow_button(page).click()
    use = page.locator("#zoom-actions button", has_text="使用")
    assert use.is_disabled()
    assert "時機" in page.locator("#zoom-actions").inner_text()


def test_e021_effect_choice_labels(page):
    start_local(page)
    page.evaluate("""() => {
      S = {...S, pending: {kind: 'pick_effect', player: S.turn_player, source: 'E-021',
           options: [{value: 'heal', label: 'heal_injured'}, {value: 'mp', label: 'gain_mp_2'}]}};
      render();
    }""")
    assert "選擇要使用的效果" in page.locator("#action-bar .choice-title").text_content()
    buttons = page.locator("#action-bar .choice-options button").all_text_contents()
    assert buttons == ["回復自己的負傷魔物", "自己的 MP +2"]
