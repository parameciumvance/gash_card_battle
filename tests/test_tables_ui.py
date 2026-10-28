"""牌桌頁的瀏覽器測試(battle-ui「牌桌頁」「入座的衝突確認」「對局結束後的再戰與離開」「首頁的模式入口」)。
需要 playwright 與 Chromium。牌桌狀態以 API 準備;對局以 API 讓雙方一直翻頁到魔書耗盡來結束。"""
import json
from urllib.request import Request, urlopen

import pytest


def api(server, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Player-Token"] = token
    req = Request(server + path, data=json.dumps(body).encode() if body is not None else None,
                  headers=headers, method="POST" if body is not None else "GET")
    with urlopen(req) as res:
        return json.loads(res.read())


def tables(server):
    return api(server, "/api/tables")["tables"]


def open_page(browser, server, name):
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale="zh-TW")
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")
    page = context.new_page()
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    page.evaluate(f"localStorage.setItem('gash-nick', '{name}'); renderLanding()")
    return context, page


def free_table(server):
    """回傳一張空桌的桌號(各測試共用同一個伺服器)。"""
    for tb in tables(server):
        if tb["state"] == "empty":
            return tb["number"]
    pytest.skip("沒有空桌")


def to_tables(page):
    page.click("#entry-tables")
    page.wait_for_selector("#tables-grid .table-card")


def card(page, number):
    return page.locator(f'#tables-grid .table-card[data-table="{number}"]')


def finish_game(server, code, tokens):
    """雙方輪流:開始階段翻 3 張、雙方 pass,直到有一方魔書耗盡。"""
    for _ in range(60):
        st = api(server, f"/api/rooms/{code}/state", token=tokens[0])
        s = st["state"]
        if s["phase"] == "game_over":
            return
        tp = s["turn_player"]
        if s["phase"] == "start":
            api(server, f"/api/rooms/{code}/commands", {"command": {"type": "flip_pages", "count": 3}}, tokens[tp])
            continue
        if s.get("pending"):
            api(server, f"/api/rooms/{code}/commands", {"command": {"type": "choose", "value": None}},
                tokens[s["pending"]["player"]])
            continue
        api(server, f"/api/rooms/{code}/commands", {"command": {"type": "pass"}}, tokens[s["action_player"]])
    raise AssertionError("對局沒有結束")


# ---------------------------------------------------------------- 首頁與牌桌頁

def test_landing_entry_order(page):
    ids = page.locator("#landing-cards .entry").evaluate_all("els => els.map((e) => e.id)")
    assert ids[:3] == ["entry-npc", "entry-tables", "entry-friend"]
    assert page.locator("#entry-tables .entry-title").text_content() == "牌桌"


def test_tables_page_shows_states(browser, server):
    n = free_table(server)
    host = api(server, f"/api/tables/{n}/sit", {"name": "小明", "expect": "empty", "timer_seconds": 60})
    context, page = open_page(browser, server, "我")
    try:
        to_tables(page)
        assert page.locator("#tables-grid .table-card").count() == 5
        info = card(page, n).inner_text()
        assert "等待對手" in info and "小明" in info and "60 秒" in info
        assert card(page, n).locator("button").inner_text() == "對戰"
    finally:
        api(server, f"/api/tables/{n}/leave", {}, host["player_token"])
        context.close()


def test_open_then_leave(browser, server):
    n = free_table(server)
    context, page = open_page(browser, server, "我")
    try:
        to_tables(page)
        card(page, n).locator("button").click()
        page.wait_for_selector("#waiting:not(.hidden)")
        assert page.locator("#waiting-leave").is_visible()
        assert page.locator("#share-join-row").is_hidden()                   # 牌桌房不能用房號加入
        assert tables(server)[n - 1]["state"] == "waiting"
        page.click("#waiting-leave")
        page.wait_for_selector("#tables:not(.hidden)")
        assert tables(server)[n - 1]["state"] == "empty"
    finally:
        context.close()


def test_conflict_confirm(browser, server):
    n = free_table(server)
    context, page = open_page(browser, server, "我")
    try:
        to_tables(page)                                                         # 畫面上這桌是空的
        host = api(server, f"/api/tables/{n}/sit", {"name": "小明", "expect": "empty", "timer_seconds": 60})
        page.select_option("#timer-tables", "120")
        card(page, n).locator("button").click()                                # 以為是空桌
        page.wait_for_selector("#tables-confirm:not(.hidden)")
        text = page.locator("#tables-confirm-text").inner_text()
        assert "小明" in text and "60 秒" in text
        page.click("#tables-confirm-join")
        page.wait_for_function("S && S.phase && SESSION && SESSION.viewer === 1")
        assert page.evaluate("R.timer_seconds") == 60
    finally:
        context.close()


def test_spectate_playing_table(browser, server):
    n = free_table(server)
    host = api(server, f"/api/tables/{n}/sit", {"name": "a", "expect": "empty", "timer_seconds": 30})
    api(server, f"/api/tables/{n}/sit", {"name": "b", "expect": "waiting"})
    context, page = open_page(browser, server, "我")
    try:
        to_tables(page)
        card(page, n).locator("button").click()
        page.wait_for_function("SESSION && SESSION.mode === 'spectate' && S")
        assert page.evaluate("SESSION.code") == host["code"]
    finally:
        context.close()


# ---------------------------------------------------------------- 結束後的再戰 / 離開

def seat_two(browser, server):
    n = free_table(server)
    ca, a = open_page(browser, server, "甲")
    cb, b = open_page(browser, server, "乙")
    to_tables(a)
    card(a, n).locator("button").click()
    a.wait_for_selector("#waiting:not(.hidden)")
    to_tables(b)
    card(b, n).locator("button").click()
    for p in (a, b):
        p.wait_for_function("S && S.phase && R && R.started")
    code = a.evaluate("SESSION.code")
    finish_game(server, code, [a.evaluate("SESSION.tokens.me"), b.evaluate("SESSION.tokens.me")])
    for p in (a, b):
        p.wait_for_function("S && S.phase === 'game_over'")
        p.wait_for_selector(".table-choice")
    return n, code, (ca, a), (cb, b)


def test_both_rematch(browser, server):
    n, code, (ca, a), (cb, b) = seat_two(browser, server)
    try:
        a.click('.table-choice button[data-choice="rematch"]')
        a.wait_for_selector(".table-choice-wait")
        b.click('.table-choice button[data-choice="rematch"]')
        for p in (a, b):
            p.wait_for_function(f"SESSION && SESSION.code !== '{code}' && S && S.phase !== 'game_over'")
        assert a.evaluate("SESSION.code") == b.evaluate("SESSION.code")
        assert tables(server)[n - 1]["state"] == "playing"
    finally:
        ca.close(); cb.close()


def test_opponent_leaves_and_i_host(browser, server):
    n, code, (ca, a), (cb, b) = seat_two(browser, server)
    try:
        b.click('.table-choice button[data-choice="leave"]')
        b.wait_for_selector("#tables:not(.hidden)")
        a.click('.table-choice button[data-choice="rematch"]')
        a.wait_for_selector("#waiting:not(.hidden)")
        assert a.evaluate("SESSION.viewer") == 0 and a.evaluate("SESSION.code") != code
        tb = tables(server)[n - 1]
        assert tb["state"] == "waiting" and tb["names"][0] == "甲"
        a.click("#waiting-leave")
    finally:
        ca.close(); cb.close()


# ---------------------------------------------------------------- 賽季(battle-ui「牌桌頁的賽季」)

def test_table_season_shown_and_mismatched_deck_cannot_join(browser, server):
    n = free_table(server)
    host = api(server, f"/api/tables/{n}/sit", {"name": "小明", "expect": "empty", "timer_seconds": 60, "season": 1})
    context, page = open_page(browser, server, "我")
    try:
        to_tables(page)
        assert "第1季" in card(page, n).inner_text()
        page.select_option("#deck-tables", "preset:zeon")                     # 牌桌頁的牌組選單不依賽季禁用
        button = card(page, n).locator("button")
        assert button.is_disabled()
        assert card(page, n).locator(".table-note").inner_text() == "所選魔書不能用於第 1 賽季"
        page.select_option("#deck-tables", "preset:level1")
        assert not button.is_disabled() and card(page, n).locator(".table-note").count() == 0
    finally:
        api(server, f"/api/tables/{n}/leave", {}, host["player_token"])
        context.close()


def test_open_table_season_limits_sit_and_is_sent(browser, server):
    n = free_table(server)
    context, page = open_page(browser, server, "我")
    try:
        to_tables(page)
        page.select_option("#season-tables", "1")
        page.select_option("#deck-tables", "preset:level2")
        assert card(page, n).locator("button").is_disabled()
        page.select_option("#deck-tables", "preset:level1")
        card(page, n).locator("button").click()
        page.wait_for_selector("#waiting:not(.hidden)")
        assert tables(server)[n - 1]["season"] == 1
        page.click("#waiting-leave")
        page.wait_for_selector("#tables:not(.hidden)")
    finally:
        context.close()


def test_conflict_confirm_shows_season(browser, server):
    n = free_table(server)
    context, page = open_page(browser, server, "我")
    try:
        to_tables(page)
        host = api(server, f"/api/tables/{n}/sit", {"name": "小明", "expect": "empty", "timer_seconds": 60, "season": 2})
        card(page, n).locator("button").click()
        page.wait_for_selector("#tables-confirm:not(.hidden)")
        assert "第 2 賽季" in page.locator("#tables-confirm-text").inner_text()
        page.click("#tables-confirm-cancel")
        api(server, f"/api/tables/{n}/leave", {}, host["player_token"])
    finally:
        context.close()
