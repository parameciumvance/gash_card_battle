"""決策在原位置選擇的瀏覽器測試(battle-ui「操作與決策互動」「選書對話框」)。需要 playwright 與 Chromium。

以本機模式開局後,在前端狀態放入 pending(與引擎送出的選項格式相同),攔截 send 檢查送出的指令。

Run: python -m pytest tests/test_choice_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(聚焦預設關閉)

PROMPT = "#action-bar .choice-prompt"


def start(page):
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase && S.players[0].book && S.players[1].book")
    page.evaluate("Anim.idle()")                                # 開局的動畫與重繪先結束,才不會蓋掉測試放入的 pending
    page.evaluate("""() => {
        window.SENT = [];
        send = (cmd) => { SENT.push(cmd); return Promise.resolve(); };
    }""")
    return page.evaluate("S.turn_player")


def set_pending(page, pending):
    page.evaluate("(pd) => { S = {...S, pending: pd}; render(); }", pending)


def sent(page):
    return page.evaluate("SENT")


def pick_in_zoom(page):
    button = page.locator("#zoom-actions button", has_text="選擇")
    assert button.count() == 1
    button.click()


def two_same_mamodo(page, p):
    """自己場上放兩隻同名魔物,回傳兩個 uid。"""
    return page.evaluate("""(p) => {
        const ps = S.players[p];
        const copy = {...ps.slots[0], uid: 999};
        S = {...S, players: S.players.map((x, i) => i === p ? {...x, slots: [x.slots[0], copy]} : x)};
        return S.players[p].slots.map(s => s.uid);
    }""", p)


def slot_options(p, uids, card):
    return [{"value": u, "card": card, "zone": "slot", "player": p, "slot": u} for u in uids]


# ---------------------------------------------------------------- 不蓋住畫面的決策提示

def test_prompt_in_action_bar_without_covering_dialog(page):
    p = start(page)
    uids = page.evaluate("(p) => S.players[p].slots.map(s => s.uid)", p)
    top = page.evaluate("(p) => S.players[p].slots[0].top", p)
    set_pending(page, {"kind": "pick_own_mamodo", "player": p, "source": "E-009",
                       "options": slot_options(p, uids, top)})
    assert not page.locator("#dialog-overlay").is_visible()
    prompt = page.locator(PROMPT)
    assert prompt.is_visible()
    assert prompt.locator(".choice-title").inner_text().endswith("選擇自己的魔物")
    source = prompt.locator(".choice-source").inner_text()
    assert page.evaluate("cname('E-009')") in source
    assert page.evaluate("TEXT['E-009'].effect").split()[0] in source
    set_pending(page, {"kind": "pick_own_mamodo", "player": p, "source": None,
                       "options": slot_options(p, uids, top)})
    assert page.locator(f"{PROMPT} .choice-source").count() == 0


def test_label_options_are_buttons(page):
    p = start(page)
    set_pending(page, {"kind": "coin_confirm", "player": p, "source": "S-027",
                       "options": [{"value": None, "label": "keep"}, {"value": 0, "label": "reflip"},
                                   {"value": 1, "label": "reflip"}],
                       "info": {"results": ["heads", "tails"]}})
    notes = page.locator(f"{PROMPT} .choice-notes").inner_text()
    assert "第 1 枚:正面" in notes and "第 2 枚:反面" in notes
    buttons = page.locator(f"{PROMPT} .choice-options button")
    assert "重擲第 2 枚(反面)" in buttons.all_text_contents()
    buttons.filter(has_text="保留結果").click()
    assert sent(page) == [{"type": "choose", "player": p, "value": None}]


# ---------------------------------------------------------------- 場上目標

def test_same_name_mamodo_picked_on_board(page):
    p = start(page)
    uids = two_same_mamodo(page, p)
    top = page.evaluate("(p) => S.players[p].slots[0].top", p)
    set_pending(page, {"kind": "pick_own_mamodo", "player": p, "source": None,
                       "options": slot_options(p, uids, top)})
    for uid in uids:
        card = page.locator(f'[data-zone-kind="mamodo"][data-slot-uid="{uid}"]')
        assert "pickable" in card.get_attribute("class")
    page.locator('[data-zone-kind="mamodo"][data-slot-uid="999"]').click()
    pick_in_zoom(page)
    assert sent(page) == [{"type": "choose", "player": p, "value": 999}]


def test_protect_targets_on_board_and_no_protect_button(page):
    p = start(page)
    uids = two_same_mamodo(page, p)
    top = page.evaluate("(p) => S.players[p].slots[0].top", p)
    set_pending(page, {"kind": "protect", "player": p, "source": None,
                       "options": [{"value": None, "label": "no_protect"}] + slot_options(p, uids[1:], top)})
    assert "pickable" not in (page.locator(f'[data-zone-kind="mamodo"][data-slot-uid="{uids[0]}"]').get_attribute("class") or "")
    page.locator(f'[data-zone-kind="mamodo"][data-slot-uid="{uids[0]}"]').click()                 # 非目標:可查閱,沒有選擇
    assert page.locator("#zoom-overlay").is_visible()
    assert page.locator("#zoom-actions button", has_text="選擇").count() == 0
    page.evaluate("closeZoom()")
    page.locator(f"{PROMPT} .choice-options button", has_text="不保護").click()
    assert sent(page) == [{"type": "choose", "player": p, "value": None}]


def test_partner_target_marked_on_partner(page):
    p = start(page)
    uid = page.evaluate("""(p) => {
        S = {...S, players: S.players.map((x, i) => i === p
            ? {...x, slots: [{...x.slots[0], partner: 'P-001'}]} : x)};
        return S.players[p].slots[0].uid;
    }""", p)
    set_pending(page, {"kind": "pick_opponent_partner", "player": 1 - p, "source": None,
                       "options": [{"value": uid, "card": "P-001", "zone": "slot", "player": p, "slot": uid},
                                   {"value": 5, "card": "P-001", "zone": "slot", "player": p, "slot": 5}]})
    partner = page.locator(".partner-cell .card.pickable")
    assert partner.count() == 1
    assert "pickable" not in (page.locator(f'[data-zone-kind="mamodo"][data-slot-uid="{uid}"]').get_attribute("class") or "")
    partner.click()
    pick_in_zoom(page)
    assert sent(page) == [{"type": "choose", "player": 1 - p, "value": uid}]


# ---------------------------------------------------------------- 魔本網格

def test_book_grid_marks_pages_and_distinguishes_copies(page):
    p = start(page)
    page.evaluate("""(p) => {
        const book = [...S.players[p].book]; book[3] = 'P-011'; book[9] = 'P-011';
        S = {...S, players: S.players.map((x, i) => i === p ? {...x, book} : x)};
    }""", p)
    set_pending(page, {"kind": "pick_partner_in_own_book", "player": p, "source": "M-021",
                       "options": [{"value": pg, "page": pg, "card": "P-011", "zone": "book", "player": p}
                                   for pg in (4, 10)]})
    assert not page.locator("#book-review-overlay").is_visible()      # 不自動開啟
    page.locator(f"{PROMPT} button", has_text="開啟魔本").click()
    grid = page.locator("#book-review-overlay")
    assert grid.is_visible()
    picks = grid.locator(".review-cell.pickable")
    assert [c.locator(".review-pno").inner_text() for c in picks.all()] == ["第 4 頁", "第 10 頁"]
    assert grid.locator(".review-cell").count() == 32
    picks.nth(1).locator(".card").click()
    pick_in_zoom(page)
    assert sent(page) == [{"type": "choose", "player": p, "value": 10}]
    assert not page.locator("#book-review-overlay").is_visible()        # 選完回到場面


def test_book_grid_can_close_and_reopen(page):
    p = start(page)
    set_pending(page, {"kind": "pick_own_empty_page", "player": p, "source": None,
                       "options": [{"value": pg, "page": pg, "zone": "book", "player": p} for pg in (5, 6)]})
    page.locator(f"{PROMPT} button", has_text="開啟魔本").click()
    page.locator("#book-review-close").click()
    assert not page.locator("#book-review-overlay").is_visible()
    assert page.locator(PROMPT).is_visible()                           # 決策仍在
    page.locator(f"{PROMPT} button", has_text="開啟魔本").click()
    assert page.locator("#book-review-overlay .review-cell.pickable").count() == 2


def test_opponent_book_shows_only_option_faces(page):
    p = start(page)
    q = 1 - p
    page.evaluate("""([p, q]) => {
        SESSION = {...SESSION, viewer: p};
        S = {...S, players: S.players.map((x, i) => i === q ? {...x, book: undefined} : x)};
    }""", [p, q])
    set_pending(page, {"kind": "pick_opponent_book_card", "player": p, "source": "E-016",
                       "options": [{"value": 7, "page": 7, "card": "S-001", "zone": "book", "player": q}]})
    opp_name = page.evaluate("(q) => pname(q)", q)
    page.locator(f"{PROMPT} button", has_text=f"開啟{opp_name}的魔本").click()
    grid = page.locator("#book-review-overlay")
    assert grid.locator(".review-cell").count() == 32
    pick = grid.locator(".review-cell.pickable")
    assert pick.count() == 1 and pick.locator(".review-pno").inner_text() == "第 7 頁"
    assert pick.locator(".card").get_attribute("data-card") == "S-001"
    assert grid.locator(".review-cell .card[data-card]").count() == 1   # 其他頁只有頁碼與卡背
    pick.locator(".card").click()
    pick_in_zoom(page)
    assert sent(page) == [{"type": "choose", "player": p, "value": 7}]


def test_open_page_target_on_board(page):
    p = start(page)
    entry = page.evaluate("(p) => S.players[p].open_pages.find(e => e.card)", p)
    set_pending(page, {"kind": "pick_own_open_page", "player": p, "source": None,
                       "options": [{"value": entry["page"], "page": entry["page"], "card": entry["card"],
                                    "zone": "book", "player": p}]})
    board_page = page.locator(f'.book-cover[data-book="{p}"] .card[data-page="{entry["page"]}"]')
    assert "pickable" in board_page.get_attribute("class")
    board_page.click()
    pick_in_zoom(page)
    assert sent(page) == [{"type": "choose", "player": p, "value": entry["page"]}]


# ---------------------------------------------------------------- 棄牌區

def test_discard_pick(page):
    p = start(page)
    page.evaluate("""(p) => {
        S = {...S, players: S.players.map((x, i) => i === p ? {...x, discard: ['S-029', 'P-011']} : x)};
    }""", p)
    set_pending(page, {"kind": "pick_partner_in_discard", "player": p, "source": None,
                       "options": [{"value": 1, "card": "P-011", "zone": "discard", "player": p, "index": 1}]})
    page.locator(f"{PROMPT} button", has_text="開啟棄牌區").click()
    cards = page.locator("#dialog-options .card")
    assert cards.count() == 2
    assert "pickable" in cards.nth(1).get_attribute("class")
    assert "pickable" not in (cards.nth(0).get_attribute("class") or "")
    cards.nth(1).click()
    pick_in_zoom(page)
    assert sent(page) == [{"type": "choose", "player": p, "value": 1}]


# ---------------------------------------------------------------- 決策期間查閱、非決策者、退回

def test_can_review_book_during_choice(page):
    p = start(page)
    uids = page.evaluate("(p) => S.players[p].slots.map(s => s.uid)", p)
    top = page.evaluate("(p) => S.players[p].slots[0].top", p)
    set_pending(page, {"kind": "pick_own_mamodo", "player": p, "source": None,
                       "options": slot_options(p, uids, top)})
    page.evaluate("(p) => showBookReview(p)", p)
    assert page.locator("#book-review-overlay").is_visible()
    assert page.locator("#book-review-overlay .review-cell.pickable").count() == 0   # 純查閱
    assert sent(page) == []


def test_non_decider_sees_no_pick(page):
    p = start(page)
    uids = page.evaluate("(p) => S.players[p].slots.map(s => s.uid)", p)
    top = page.evaluate("(p) => S.players[p].slots[0].top", p)
    page.evaluate("(p) => { SESSION = {...SESSION, viewer: 1 - p}; }", p)
    set_pending(page, {"kind": "pick_own_mamodo", "player": p, "source": None,
                       "options": slot_options(p, uids, top)})
    assert page.locator(PROMPT).count() == 0
    assert page.locator(".pickable").count() == 0
    page.locator(f'[data-zone-kind="mamodo"][data-slot-uid="{uids[0]}"]').click()
    assert page.locator("#zoom-actions button", has_text="選擇").count() == 0


def test_unmapped_card_option_listed_in_prompt(page):
    p = start(page)
    set_pending(page, {"kind": "pick_own_mamodo", "player": p, "source": None,
                       "options": [{"value": 42, "card": "M-001"}, {"value": 43, "card": "M-002"}]})
    cards = page.locator(f"{PROMPT} .choice-cards .card")
    assert cards.count() == 2
    cards.nth(1).click()
    assert sent(page) == [{"type": "choose", "player": p, "value": 43}]
