"""戰術使用魔物、任意頁戰術與搭檔裝備對象的瀏覽器測試(battle-ui「選擇戰術的使用魔物」
「從魔書任意頁使用戰術」「選擇搭檔卡的裝備對象」)。需要 playwright 與 Chromium。以本機測試模式操作。

Run: python -m pytest tests/test_spell_user_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)


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
    """場上選擇:點開發光的魔物,在放大檢視按「選擇」。"""
    slot_card(page, uid).click()
    page.locator("#zoom-actions button", has_text="選擇").click()


# ---------------------------------------------------------------- 攻擊 / 防禦的使用魔物

def test_two_users_pick_zeon(page):
    tp, pg, slots = with_zeon(page)
    open_page_zoom(page, tp, pg)
    page.locator("#zoom-actions button", has_text="攻擊").click()
    assert not dialog_open(page)                                              # 在場上選,不用對話框
    assert pickable_uids(page) == sorted([slots["M-001"], slots["M-029"]])
    assert page.locator("#action-bar .choice-prompt").count() == 1
    slot_card(page, slots["M-029"]).click()
    assert "費用" in page.locator("#zoom-actions").inner_text()
    page.locator("#zoom-actions button", has_text="選擇").click()
    page.wait_for_function("S.battle_in")
    assert page.evaluate("S.battle_in.slot") == slots["M-029"]


def test_field_pick_cancel_and_unselectable(page):
    tp, pg, slots = with_zeon(page)
    # 前端複製第三隻(uid 901),快照標示它被封鎖:不發光,點開時「選擇」停用並顯示原因
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      slots: [...ps.slots, {{...ps.slots[0], uid: 901}}],
      open_pages: ps.open_pages.map((e) => e.page === {pg}
        ? {{...e, users: [...e.users, {{slot_uid: 901, cost: 1, locked: true}}]}} : e)}})}}; render()""")
    stub_send(page)
    open_page_zoom(page, tp, pg)
    page.locator("#zoom-actions button", has_text="攻擊").click()
    assert pickable_uids(page) == sorted([slots["M-001"], slots["M-029"]])
    slot_card(page, 901).click()
    assert page.locator("#zoom-actions button", has_text="選擇").is_disabled()
    assert "本回合不能使用戰術" in page.locator("#zoom-actions").inner_text()
    page.evaluate("closeZoom()")
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


def test_nonbattle_picker_only_when_costs_differ(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "S-026"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    gash = page.evaluate(f"S.players[{tp}].slots[0].uid")
    def users(costs):
        page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
          open_pages: ps.open_pages.map((e) => e.page === {pos} ? {{...e, cost: 0,
            users: {costs}.map((c, k) => ({{slot_uid: {gash} + k * 100, cost: c, locked: false}}))}} : e)}})}}; render()""")
    stub_send(page)
    users([0, 0])
    open_page_zoom(page, tp, pos)
    page.locator("#zoom-actions button", has_text="使用").click()
    assert not dialog_open(page) and sent(page)[0]["slot_uid"] == gash
    page.evaluate("closeZoom(); window.__sent = []")
    users([0, 2])
    open_page_zoom(page, tp, pos)
    page.locator("#zoom-actions button", has_text="使用").click()
    assert page.locator("#action-bar .choice-prompt").count() == 1 and sent(page) == []   # 費用不同:在場上選


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
    page.locator("#zoom-actions button", has_text="攻擊").click()
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
    page.locator("#zoom-actions button", has_text="攻擊").click()
    assert sent(page) == [{"type": "declare_attack", "player": tp, "page": 20, "slot_uid": slots["M-001"]}]


# ---------------------------------------------------------------- 搭檔卡的裝備對象

def _two_gash(page, first_partner=None):
    """先攻方場上複製一隻賈修(只在前端),翻開的頁放 P-001(賈修的搭檔)。"""
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    set_book(page, tp, {pos: "P-001"})
    send(page, {"type": "flip_pages", "player": tp, "count": 0})
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i !== {tp} ? ps : {{...ps,
      slots: [{{...ps.slots[0], partner: {repr(first_partner) if first_partner else 'null'}}},
              {{...ps.slots[0], uid: 900, partner: null}}]}})}}; render()""")
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
