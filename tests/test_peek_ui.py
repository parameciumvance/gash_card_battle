"""檢視對手頁面的瀏覽器測試(battle-ui「檢視對手頁面的顯示」;E-014 / M-018)。
需要 playwright 與 Chromium。以本機測試模式操作(全視角收到含卡片清單的檢視事件)。

Run: python -m pytest tests/test_peek_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)


def start_local(page):
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")


def set_books(page, own, opp, mp=10):
    """以金手指改回合玩家(own)與對手(opp)的魔本頁:{頁碼: 卡號}。"""
    page.evaluate("""async ([own, opp, mp]) => {
      const base = `/api/rooms/${SESSION.code}`;
      const headers = {'X-Player-Token': Object.values(SESSION.tokens)[0], 'Content-Type': 'application/json'};
      const data = await api(`${base}/debug-state`, {headers});
      const tp = S.turn_player;
      for (const [p, c] of Object.entries(own)) data.players[tp].book[p - 1] = c;
      for (const [p, c] of Object.entries(opp)) data.players[1 - tp].book[p - 1] = c;
      data.players[tp].mp = mp;
      await api(`${base}/debug-state`, {method: 'POST', headers, body: JSON.stringify(data)});
    }""", [{str(k): v for k, v in own.items()}, {str(k): v for k, v in opp.items()}, mp])


def send_tp(page, command):
    page.evaluate("c => send({...c, player: S.turn_player})", command)


def peek_dialog(page):
    page.wait_for_function("INFO && INFO.kind === 'peek' && !document.getElementById('info-overlay').classList.contains('hidden')")
    return {
        "pages": page.locator("#info-body .peek-page-no").all_text_contents(),
        "cards": page.locator("#info-body .card .cnum").all_text_contents(),
        "button": page.locator("#info-close").text_content(),
    }


def test_e014_shows_peeked_pages_and_closes(page):
    start_local(page)
    # 對手翻開第 2、3 頁;E-014 翻 1 張後翻開第 4、5 頁
    set_books(page, {2: "E-014"}, {4: "E-003", 5: "S-008"})
    send_tp(page, {"type": "flip_pages", "count": 0})
    send_tp(page, {"type": "use_book_card", "page": 2})
    dialog = peek_dialog(page)
    assert dialog["pages"] == ["第 4 頁", "第 5 頁"]
    assert dialog["cards"] == ["E-003", "S-008"]
    assert dialog["button"] == "確定"
    assert page.evaluate("S.pending") is None          # 檢視不是決策,引擎沒有待決策
    page.locator("#info-close").click()
    assert page.evaluate("INFO === null && document.getElementById('info-overlay').classList.contains('hidden')")


def test_m018_shows_peeked_pages(page):
    start_local(page)
    set_books(page, {2: "M-018"}, {2: "E-003", 3: "E-003"})
    send_tp(page, {"type": "flip_pages", "count": 0})
    send_tp(page, {"type": "play_card", "page": 2})
    page.wait_for_function("S.players[S.turn_player].slots.some(s => s.top === 'M-018')")
    page.evaluate("send({type: 'pass', player: 1 - S.turn_player})")   # 放卡後行動權在對手
    page.wait_for_function("S.action_player === S.turn_player")
    page.evaluate("""() => {
      const slot = S.players[S.turn_player].slots.find(s => s.top === 'M-018');
      return send({type: 'use_field_ability', player: S.turn_player, zone: 'mamodo', slot_uid: slot.uid});
    }""")
    dialog = peek_dialog(page)
    assert dialog["pages"] == ["第 2 頁", "第 3 頁"]
    assert dialog["cards"] == ["E-003", "E-003"]


def test_peek_not_shown_again_after_reload(page):
    start_local(page)
    set_books(page, {2: "E-014"}, {})
    send_tp(page, {"type": "flip_pages", "count": 0})
    send_tp(page, {"type": "use_book_card", "page": 2})
    peek_dialog(page)
    page.reload()
    page.wait_for_function("S && S.phase === 'battle' && logSeq > 0")
    page.wait_for_timeout(500)
    assert page.evaluate("INFO === null")
    assert page.locator("#info-overlay").is_hidden()


def test_peek_without_cards_not_shown(page):
    # 被檢視方 / 觀戰者收到的事件沒有 cards:只寫記錄,不跳出對話框
    start_local(page)
    send_tp(page, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    page.evaluate("""() => applyPayload({actor: 1, events: [
      {seq: logSeq + 100, type: 'pages_peeked', player: 0, viewer: 1}]})""")
    page.wait_for_timeout(500)
    assert page.evaluate("INFO === null")


def test_m018_button_disabled_on_opponent_turn(page):
    start_local(page)
    set_books(page, {2: "M-018"}, {})
    send_tp(page, {"type": "flip_pages", "count": 0})
    send_tp(page, {"type": "play_card", "page": 2})
    page.wait_for_function("S.players[S.turn_player].slots.some(s => s.top === 'M-018')")
    owner = page.evaluate("S.turn_player")
    # 放卡後行動權在對手:對手 pass、回合玩家 pass → 對手的回合;對手翻頁後 pass,行動權到 M-018 的持有者
    page.evaluate("p => send({type: 'pass', player: 1 - p})", owner)
    page.evaluate("p => send({type: 'pass', player: p})", owner)
    page.wait_for_function(f"S.turn_player === {1 - owner} && S.phase === 'start'")
    page.evaluate("p => send({type: 'flip_pages', player: 1 - p, count: 0})", owner)
    page.evaluate("p => send({type: 'pass', player: 1 - p})", owner)
    page.wait_for_function(f"S.phase === 'battle' && S.action_player === {owner}")
    page.evaluate("""p => {
      const slot = S.players[p].slots.find(s => s.top === 'M-018');
      zoom('M-018', {kind: 'slot', p, uid: slot.uid});
    }""", owner)
    button = page.locator("#zoom-actions button", has_text="MP")
    assert button.is_disabled()
    assert "自己的回合" in page.locator("#zoom-actions").inner_text()
