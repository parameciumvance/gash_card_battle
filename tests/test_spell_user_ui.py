"""戰術使用魔物、任意頁戰術與搭檔裝備對象的瀏覽器測試(battle-ui「選擇戰術的使用魔物」
「從魔書任意頁使用戰術」「選擇搭檔卡的裝備對象」)。需要 playwright 與 Chromium。以本機測試模式操作。

Run: python -m pytest tests/test_spell_user_ui.py -q
"""


def start_local(page):
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    return page.evaluate("S.turn_player")


def set_book(page, player, pages, mp=10):
    page.evaluate("""async ([player, pages, mp]) => {
      const base = `/api/rooms/${SESSION.code}`;
      const headers = {'X-Player-Token': Object.values(SESSION.tokens)[0], 'Content-Type': 'application/json'};
      const data = await api(`${base}/debug-state`, {headers});
      for (const [p, c] of Object.entries(pages)) data.players[player].book[p - 1] = c;
      data.players[player].mp = mp;
      await api(`${base}/debug-state`, {method: 'POST', headers, body: JSON.stringify(data)});
    }""", [player, {str(k): v for k, v in pages.items()}, mp])


def send(page, command):
    page.evaluate("c => send(c)", command)


def with_zeon(page):
    """先攻方翻開的第 2 頁放 M-029 ゼオン並放出,第 3 頁為「ザケル」(S-001);回到先攻方的行動權。"""
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "M-029", pos + 1: "S-001"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    send(page, {"type": "play_card", "player": tp, "page": pos})
    page.wait_for_function(f"S.players[{tp}].slots.some((s) => s.top === 'M-029')")
    send(page, {"type": "pass", "player": 1 - tp})
    page.wait_for_function(f"S.action_player === {tp}")
    slots = page.evaluate(f"S.players[{tp}].slots.map((s) => [s.top, s.uid])")
    return tp, pos + 1, dict(slots)


def open_page_zoom(page, tp, pg):
    page.evaluate(f"zoom(S.players[{tp}].open_pages.find((e) => e.page === {pg}).card, {{kind: 'page', p: {tp}, page: {pg}}})")


def dialog_open(page):
    return page.evaluate("!document.getElementById('dialog-overlay').classList.contains('hidden')")


def stub_send(page):
    """攔下送出的指令(只驗證前端選擇的結果)。"""
    page.evaluate("() => { window.__sent = []; send = (c) => { window.__sent.push(c); return Promise.resolve(); }; }")


def sent(page):
    return page.evaluate("window.__sent")


def slot_card(page, uid):
    return page.locator(f'[data-slot-uid="{uid}"][data-zone-kind="mamodo"]')


def pickable_uids(page):
    return sorted(page.evaluate("""[...document.querySelectorAll('[data-zone-kind="mamodo"].pickable')]
      .map((el) => Number(el.dataset.slotUid))"""))


def pick_on_field(page, uid):
    """場上選擇:點發光的魔物,在卡片行動選單按「選擇」。"""
    slot_card(page, uid).click()
    page.locator("#card-menu button", has_text="選擇").click()


# ---------------------------------------------------------------- 攻擊 / 防禦的使用魔物

def test_two_users_pick_zeon(page):
    tp, pg, slots = with_zeon(page)
    open_page_zoom(page, tp, pg)
    page.locator("#zoom-actions button", has_text="攻擊").click()
    assert not dialog_open(page)                                              # 在場上選,不用對話框
    assert pickable_uids(page) == sorted([slots["M-001"], slots["M-029"]])
    assert page.locator("#action-bar .choice-prompt").count() == 1
    slot_card(page, slots["M-029"]).click()
    assert "費用" in page.locator("#card-menu").inner_text()
    page.locator("#card-menu button", has_text="選擇").click()
    page.wait_for_function("S.battle_in")
    assert page.evaluate("S.battle_in.slot") == slots["M-029"]


def test_field_pick_cancel_and_unselectable(page):
    tp, pg, slots = with_zeon(page)
    # 前端複製第三隻(uid 901),快照標示它被封鎖:不發光,點開時「選擇」停用並顯示原因
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      slots: [...ps.slots, {{...ps.slots[0], uid: 901, column: ps.slots.length}}],
      open_pages: ps.open_pages.map((e) => e.page === {pg}
        ? {{...e, users: [...e.users, {{slot_uid: 901, cost: 1, locked: true}}]}} : e)}})}}; render()""")
    stub_send(page)
    open_page_zoom(page, tp, pg)
    page.locator("#zoom-actions button", has_text="攻擊").click()
    assert pickable_uids(page) == sorted([slots["M-001"], slots["M-029"]])
    slot_card(page, 901).click()
    assert page.locator("#card-menu button", has_text="選擇").is_disabled()
    assert "本回合不能使用戰術" in page.locator("#card-menu").inner_text()
    page.keyboard.press("Escape")
    page.locator("#action-bar .choice-prompt button", has_text="取消").click()
    assert pickable_uids(page) == [] and page.locator("#action-bar .choice-prompt").count() == 0
    assert sent(page) == []


def test_single_user_declares_directly(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "S-001"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    stub_send(page)
    open_page_zoom(page, tp, pos)
    page.locator("#zoom-actions button", has_text="攻擊").click()
    assert not dialog_open(page)
    gash = page.evaluate(f"S.players[{tp}].slots[0].uid")
    assert sent(page) == [{"type": "declare_attack", "player": tp, "page": pos, "slot_uid": gash}]


def test_usability_follows_snapshot_users(page):
    # 前端不自行判斷相容:快照說沒有可使用的魔物,攻擊就停用
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "S-001"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      open_pages: ps.open_pages.map((e) => e.page === {pos} ? {{...e, users: []}} : e)}})}}; render()""")
    open_page_zoom(page, tp, pos)
    button = page.locator("#zoom-actions button", has_text="攻擊")
    assert button.is_disabled()
    assert "沒有可使用此戰術的魔物" in page.locator("#zoom-actions").inner_text()


def test_locked_user_skipped(page):
    tp, pg, slots = with_zeon(page)
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      open_pages: ps.open_pages.map((e) => e.page === {pg}
        ? {{...e, users: e.users.map((u) => u.slot_uid === {slots['M-001']} ? {{...u, locked: true}} : u)}} : e)}})}}; render()""")
    stub_send(page)
    open_page_zoom(page, tp, pg)
    page.locator("#zoom-actions button", has_text="攻擊").click()
    assert not dialog_open(page)
    assert sent(page)[0]["slot_uid"] == slots["M-029"]


def test_nonbattle_picker_when_two_users(page):
    # 非戰鬥戰術(含指令戰術)與攻防相同:可選的兩隻以上就在場上選,費用相同也問
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "S-026"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    gash = page.evaluate(f"S.players[{tp}].slots[0].uid")
    def users(uids):
        page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
          open_pages: ps.open_pages.map((e) => e.page === {pos} ? {{...e, cost: 0,
            users: {uids}.map((u) => ({{slot_uid: u, cost: 0, locked: false}}))}} : e)}})}}; render()""")
    stub_send(page)
    users([gash])
    open_page_zoom(page, tp, pos)
    page.locator("#zoom-actions button", has_text="使用").click()
    assert page.locator("#action-bar .choice-prompt").count() == 0 and sent(page)[0]["slot_uid"] == gash
    page.evaluate("closeZoom(); window.__sent = []")
    users([gash, gash + 100])
    open_page_zoom(page, tp, pos)
    page.locator("#zoom-actions button", has_text="使用").click()
    assert page.locator("#action-bar .choice-prompt").count() == 1 and sent(page) == []


def test_book_card_used_log_by_type(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "S-026", pos + 1: "E-003"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    gash = page.evaluate(f"S.players[{tp}].slots[0].uid")
    send(page, {"type": "use_book_card", "player": tp, "page": pos, "slot_uid": gash})
    page.wait_for_function(f"S.players[S.turn_player].used_nonbattle_pages.includes({pos})")
    if page.evaluate("S.pending"):
        page.evaluate("send({type: 'choose', player: S.pending.player, value: S.pending.options[0].value})")
    names = page.evaluate("[cname('S-026'), cname('M-001'), cname('E-003')]")
    page.wait_for_function(f"document.getElementById('log').innerText.includes('使用戰術「{names[0]}」')")
    log = page.locator("#log").inner_text()
    assert f"以〔{names[1]}〕使用戰術「{names[0]}」" in log
    assert f"使用事件卡「{names[0]}」" not in log
    send(page, {"type": "pass", "player": 1 - tp})
    page.wait_for_function(f"S.action_player === {tp}")
    send(page, {"type": "use_book_card", "player": tp, "page": pos + 1})
    page.wait_for_function(f"document.getElementById('log').innerText.includes('使用事件卡「{names[2]}」')")



def test_opp_mp_reduction_restricted_log(page):
    # E-018 因直前回合條款減 0:記錄寫出原因(battle-ui「減少對手 MP 被限制為 0 的記錄」)
    start_local(page)
    line = page.evaluate("logLine({type: 'opp_mp_reduction_restricted', player: 0, source: 'E-018'})")
    text = line if isinstance(line, str) else page.evaluate("(l) => l.textContent ?? String(l)", line)
    name = page.evaluate("cname('E-018')")
    assert "上一個回合已使用減少對手 MP 的效果" in text and name in text and "MP 為 0" in text

def test_p001_disabled_on_opponent_turn(page):
    tp = start_local(page)
    op = 1 - tp
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "P-001"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    gash = page.evaluate(f"S.players[{tp}].slots[0].uid")
    send(page, {"type": "play_card", "player": tp, "page": pos, "slot_uid": gash})
    page.wait_for_function(f"S.players[{tp}].slots[0].partner === 'P-001'")
    send(page, {"type": "pass", "player": op})
    send(page, {"type": "pass", "player": tp})
    page.wait_for_function(f"S.turn_player === {op} && S.phase === 'start'")
    send(page, {"type": "flip_pages", "player": op, "count": 0})
    send(page, {"type": "pass", "player": op})
    page.wait_for_function(f"S.action_player === {tp}")
    page.evaluate(f"zoom('P-001', {{kind: 'partner', p: {tp}, uid: {gash}}})")
    button = page.locator("#zoom-actions button").first
    assert button.is_disabled()
    assert "只能在自己的回合使用" in page.locator("#zoom-actions").inner_text()


# ---------------------------------------------------------------- P-015 任意頁戰術

def test_any_page_spell_entry(page):
    tp, pg, slots = with_zeon(page)
    a, b = slots["M-001"], slots["M-029"]
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      book: ps.book.map((c, k) => k === 19 ? 'S-042' : c),
      any_page_spells: [{{page: 20, card: 'S-042', cost: 2, users: [
        {{slot_uid: {a}, cost: 2, locked: false}}, {{slot_uid: {b}, cost: 2, locked: false}}]}}]}})}}; render()""")
    stub_send(page)
    entry = page.locator("#action-bar button", has_text="從魔書使用")
    assert "ビライツ" in entry.text_content() or "畢雷茲" in entry.text_content()
    entry.click()
    page.wait_for_function("!document.getElementById('book-review-overlay').classList.contains('hidden')")
    cell = page.locator('#book-review-grid .review-cell[data-page="20"]')
    assert "pickable" in cell.get_attribute("class")
    cell.locator(".card").click()
    page.locator("#card-menu button", has_text="攻擊").click()
    assert page.locator("#book-review-overlay").is_hidden()                   # 網格關閉,回到場上選
    pick_on_field(page, b)
    assert sent(page) == [{"type": "declare_attack", "player": tp, "page": 20, "slot_uid": b}]


def test_any_page_spell_while_browsing(page):
    tp, pg, slots = with_zeon(page)
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      book: ps.book.map((c, k) => k === 19 ? 'S-042' : c),
      any_page_spells: [{{page: 20, card: 'S-042', cost: 2, users: [
        {{slot_uid: {slots['M-001']}, cost: 2, locked: false}}]}}]}})}}; render()""")
    stub_send(page)
    nxt = page.locator(f'.book-block[data-book-block="{tp}"] .book-next')
    while not page.locator(f'.book-block[data-book-block="{tp}"] .book-pages [data-page="20"]').count():
        nxt.click()
    card = page.locator(f'.book-block[data-book-block="{tp}"] .book-pages [data-page="20"]')
    assert "pickable" in card.get_attribute("class")
    card.click()
    page.locator("#card-menu button", has_text="攻擊").click()
    assert sent(page) == [{"type": "declare_attack", "player": tp, "page": 20, "slot_uid": slots["M-001"]}]


def to_defense(page):
    """先攻方以翻開的「ザケル」攻擊、後攻方同意進入戰鬥,停在後攻方宣告防禦的時機。回傳 (攻方, 守方)。"""
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos + 1: "S-001"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page.wait_for_function(f"S.phase === 'battle' && S.action_player === {tp}")
    send(page, {"type": "declare_attack", "player": tp, "page": pos + 1,
                "slot_uid": page.evaluate(f"S.players[{tp}].slots[0].uid")})
    page.wait_for_function("S.battle_in")
    send(page, {"type": "battle_in_response", "player": 1 - tp, "allow": True})
    page.wait_for_function("S.battle && S.battle.step === 'defense'")
    return tp, 1 - tp


def put_any_page(page, p, card, uid):
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {p} ? ps : {{...ps, mp: 10,
      book: ps.book.map((c, k) => k === 19 ? '{card}' : c),
      any_page_spells: [{{page: 20, card: '{card}', cost: 2, users: [{{slot_uid: {uid}, cost: 2, locked: false}}]}}]}})}};
      render()""")


def to_opponent_nonbattle(page):
    """先攻方 pass 一次,停在後攻方於對手回合非戰鬥中的行動權。回傳 (回合玩家, 非回合玩家)。"""
    tp = start_local(page)
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page.wait_for_function(f"S.phase === 'battle' && S.action_player === {tp}")
    send(page, {"type": "pass", "player": tp})
    page.wait_for_function(f"S.action_player === {1 - tp} && !S.pending")
    return tp, 1 - tp


def to_battle_in(page):
    """先攻方以翻開的「ザケル」攻擊,停在後攻方確認進入戰鬥(可插入一個行動)的時機。"""
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos + 1: "S-001"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page.wait_for_function(f"S.phase === 'battle' && S.action_player === {tp}")
    send(page, {"type": "declare_attack", "player": tp, "page": pos + 1,
                "slot_uid": page.evaluate(f"S.players[{tp}].slots[0].uid")})
    page.wait_for_function("S.battle_in && !S.pending")
    return tp, 1 - tp


def use_event_from_book(page, p):
    entry = page.locator("#action-bar button", has_text="從魔書使用")
    assert entry.count() == 1
    entry.click()
    page.wait_for_function("!document.getElementById('book-review-overlay').classList.contains('hidden')")
    page.locator('#book-review-grid .review-cell[data-page="20"] .card').click()
    page.locator("#card-menu button", has_text="使用").click()
    assert sent(page) == [{"type": "use_book_card", "player": p, "page": 20}]


def test_any_page_event_entry_on_opponent_nonbattle(page):
    # P-037 / Ex-037:防禦圖示的事件卡在對手回合的非戰鬥中也能從魔書使用(入口不只限回合玩家)
    _tp, op = to_opponent_nonbattle(page)
    put_any_page(page, op, "E-031", page.evaluate(f"S.players[{op}].slots[0].uid"))   # ナオミちゃんの助け:防
    stub_send(page)
    use_event_from_book(page, op)


def test_any_page_event_entry_on_battle_in(page):
    # 確認進入戰鬥時非回合玩家插入的行動,也能用其他頁的防禦圖示事件卡
    _tp, dp = to_battle_in(page)
    put_any_page(page, dp, "E-031", page.evaluate(f"S.players[{dp}].slots[0].uid"))
    stub_send(page)
    use_event_from_book(page, dp)


def test_nonbattle_spell_insert_on_battle_in(page):
    # 確認進入戰鬥時可插入攻防圖示的非戰鬥戰術(PR-009 ラウザルク):翻開的頁提供「使用」
    _tp, dp = to_battle_in(page)
    uid = page.evaluate(f"S.players[{dp}].slots[0].uid")
    pg = page.evaluate(f"S.players[{dp}].open_pages[0].page")
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {dp} ? ps : {{...ps, mp: 10,
      open_pages: ps.open_pages.map((e) => e.page !== {pg} ? e : {{...e, card: 'PR-009', cost: 3, condition_ok: true,
        users: [{{slot_uid: {uid}, cost: 3, locked: false}}]}})}})}}; render()""")
    stub_send(page)
    open_page_zoom(page, dp, pg)
    use = page.locator("#zoom-actions button", has_text="使用")
    assert use.is_enabled()
    use.click()
    assert sent(page) == [{"type": "use_book_card", "player": dp, "page": pg, "slot_uid": uid}]


def test_borrowed_effect_entry_on_battle_in(page):
    # E-010 借用的搭檔效果在確認進入戰鬥時也能插入:行動欄除了「同意進入戰鬥」還有借用效果
    _tp, dp = to_battle_in(page)
    page.evaluate(f"""S = {{...S, effects: [...(S.effects || []), {{type: 'standby', kind: 'borrow_partner',
        source: 'E-010', owner: {dp}, card: 'Ex-007', used: false,
        ability: {{mp_cost: 0, timing: 'nonbattle', own_turn: false, mode: 'discard'}}}}],
      players: S.players.map((ps, i) => i !== {dp} ? ps : {{...ps, borrowed_block: null}})}}; render()""")
    stub_send(page)
    entry = page.locator("#action-bar button", has_text="借用效果")
    assert entry.count() == 1
    entry.click()
    use = page.locator("#zoom-actions button", has_text="使用")
    assert use.is_enabled()
    use.click()
    assert sent(page) == [{"type": "use_borrowed_effect", "player": dp}]


def test_any_page_no_entry_when_nothing_usable(page):
    # 對手回合非戰鬥中,其他頁只有攻擊用的戰術(只能停用):不顯示入口
    _tp, op = to_opponent_nonbattle(page)
    put_any_page(page, op, "S-042", page.evaluate(f"S.players[{op}].slots[0].uid"))
    assert page.locator("#action-bar button", has_text="從魔書使用").count() == 0


def test_any_page_spell_entry_on_defense(page):
    # 對手回合用 P-015 後,防禦時機也能從魔書使用其他頁的ビライツ(使用者回報:原本行動欄沒有入口)
    _tp, dp = to_defense(page)
    uid = page.evaluate(f"S.players[{dp}].slots[0].uid")
    put_any_page(page, dp, "S-042", uid)                                     # ビライツ:攻防兩用
    stub_send(page)
    entry = page.locator("#action-bar button", has_text="從魔書使用")
    assert entry.count() == 1
    entry.click()
    page.wait_for_function("!document.getElementById('book-review-overlay').classList.contains('hidden')")
    page.locator('#book-review-grid .review-cell[data-page="20"] .card').click()
    page.locator("#card-menu button", has_text="防禦").click()
    assert sent(page) == [{"type": "declare_defense", "player": dp, "page": 20, "slot_uid": uid}]


def test_any_page_attack_only_spell_no_entry_on_defense(page):
    _tp, dp = to_defense(page)
    put_any_page(page, dp, "S-023", page.evaluate(f"S.players[{dp}].slots[0].uid"))   # サイス:只有攻擊圖示
    assert page.locator("#action-bar button", has_text="從魔書使用").count() == 0


# ---------------------------------------------------------------- 搭檔卡的裝備對象

def _two_gash(page, first_partner=None):
    """先攻方場上複製一隻賈修(只在前端),翻開的頁放 P-001(賈修的搭檔);快照的 targets 照著改。"""
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "P-001"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page.wait_for_function(f"S.players[{tp}].open_pages.some((e) => e.card === 'P-001')")
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      slots: [{{...ps.slots[0], partner: {repr(first_partner) if first_partner else 'null'}}},
              {{...ps.slots[0], uid: 900, partner: null, column: 1}}],
      open_pages: ps.open_pages.map((e) => e.page !== {pos} ? e : {{...e, play_block: null,
        targets: {'[900]' if first_partner else '[ps.slots[0].uid, 900]'}}})}})}}; render()""")
    stub_send(page)
    return tp, pos


def test_partner_target_picker(page):
    tp, pos = _two_gash(page)
    open_page_zoom(page, tp, pos)
    page.locator("#zoom-actions button", has_text="放出").click()
    assert not dialog_open(page)
    first = page.evaluate(f"S.players[{tp}].slots[0].uid")
    assert pickable_uids(page) == sorted([first, 900])                        # 兩隻同名魔物以位置區分
    pick_on_field(page, 900)
    assert sent(page) == [{"type": "play_card", "player": tp, "page": pos, "slot_uid": 900}]


def test_partner_goes_to_free_mamodo_directly(page):
    tp, pos = _two_gash(page, first_partner="P-010")
    open_page_zoom(page, tp, pos)
    page.locator("#zoom-actions button", has_text="放出").click()
    assert not dialog_open(page)
    assert sent(page) == [{"type": "play_card", "player": tp, "page": pos, "slot_uid": 900}]


def test_partner_follows_snapshot_targets_with_m047(page):
    # M-047 疊在賈修上:卡面 related_mamodo 是「金色のガッシュベル」,快照的 targets 仍含這隻
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "M-047", pos + 1: "P-001"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    send(page, {"type": "play_card", "player": tp, "page": pos})               # 疊在先攻方的賈修上
    page.wait_for_function(f"S.players[{tp}].slots[0].top === 'M-047'")
    send(page, {"type": "pass", "player": 1 - tp})
    page.wait_for_function(f"S.action_player === {tp}")
    pos += 1
    uid = page.evaluate(f"S.players[{tp}].slots[0].uid")
    open_page_zoom(page, tp, pos)
    button = page.locator("#zoom-actions button", has_text="放出")
    assert button.is_enabled()
    button.click()
    page.wait_for_function(f"S.players[{tp}].slots[0].partner === 'P-001'")
    assert page.evaluate(f"S.players[{tp}].slots[0].uid") == uid


# ---------------------------------------------------------------- 不能放出的魔物卡停用

def test_spell_only_mamodo_play_disabled(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "M-046"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page.wait_for_function(f"S.players[{tp}].open_pages.some((e) => e.card === 'M-046')")
    open_page_zoom(page, tp, pos)
    assert page.locator("#zoom-actions button", has_text="放出").is_disabled()
    assert "此卡只能經由指定戰術卡疊放" in page.locator("#zoom-actions").inner_text()


def test_field_full_play_disabled(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "M-004"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page.wait_for_function(f"S.players[{tp}].open_pages.some((e) => e.card === 'M-004')")
    open_page_zoom(page, tp, pos)
    assert page.locator("#zoom-actions button", has_text="放出").is_enabled()
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      open_pages: ps.open_pages.map((e) => e.page === {pos} ? {{...e, play_block: 'field_full'}} : e)}})}}; render()""")
    open_page_zoom(page, tp, pos)
    assert page.locator("#zoom-actions button", has_text="放出").is_disabled()
    assert "場上魔物已達 3 隻" in page.locator("#zoom-actions").inner_text()


# ---------------------------------------------------------------- 不符合使用條件的卡停用

def test_condition_not_met_disables_use(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "E-021", pos + 1: "S-048"})                     # E-021 需要場上 2 隻魔物
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page.wait_for_function(f"S.players[{tp}].open_pages.some((e) => e.card === 'E-021')")
    open_page_zoom(page, tp, pos)
    assert page.locator("#zoom-actions button", has_text="使用").is_disabled()
    assert "不符合使用條件" in page.locator("#zoom-actions").inner_text()
    # S-048:讓快照的使用者可用(賈修不是バルトロ,這裡只驗證 condition_ok 的停用)
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      open_pages: ps.open_pages.map((e) => e.page === {pos + 1}
        ? {{...e, users: [{{slot_uid: ps.slots[0].uid, cost: 1, locked: false}}]}} : e)}})}}; render()""")
    open_page_zoom(page, tp, pos + 1)
    assert page.locator("#zoom-actions button", has_text="使用").is_disabled()
    assert "不符合使用條件" in page.locator("#zoom-actions").inner_text()
