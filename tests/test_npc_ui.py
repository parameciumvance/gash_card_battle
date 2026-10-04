"""NPC 對戰的瀏覽器測試(battle-ui「首頁入口」「NPC 對戰畫面」「金手指面板」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_npc_ui.py -q
"""
import pytest

from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

NPC_WAIT_MS = 20000   # 伺服器端 NPC 送出前會稍候,等待要留足時間


def room_posts(page):
    posts = []
    page.on("request", lambda r: posts.append(r.post_data_json)
            if r.method == "POST" and r.url.endswith("/api/rooms") else None)
    return posts


def open_npc_setup(page):
    """從首頁進入 NPC 對戰設定頁(已在設定頁時不動)。"""
    if not page.locator("#setup-npc").is_visible():
        page.locator("#entry-npc").click()


def start_npc(page):
    open_npc_setup(page)
    page.locator("#npc-start").click()
    page.wait_for_function("SESSION && SESSION.mode === 'npc' && S && R && R.npc")


def test_start_npc_battle_with_chosen_deck_and_level(page):
    posts = room_posts(page)
    open_npc_setup(page)
    assert page.locator("#deck-npc-opp").input_value() == "npc:random"        # 缺省隨機
    assert page.locator("#npc-level").input_value() == "normal"               # 缺省一般
    page.select_option("#deck-npc-opp", "preset:level2")
    page.select_option("#npc-level", "dummy")
    start_npc(page)
    assert posts[-1]["mode"] == "npc"
    assert posts[-1]["npc_deck"] == {"preset": "level2"} and "npc_decks" not in posts[-1]
    assert posts[-1]["npc_level"] == "dummy"
    assert page.locator("#layout").is_visible()
    assert page.evaluate("pname(1)") == "NPC(木人樁)"
    assert page.locator("#cheat-toggle").is_visible()                         # NPC 房開放金手指
    # 自己在下方;NPC 翻開頁只有頁碼
    assert page.evaluate("document.getElementById('zone-bottom').dataset.player") == "0"
    assert page.evaluate("S.players[1].open_pages.every(p => !('card' in p))")
    assert page.locator("#countdown").text_content() == ""


def test_random_npc_deck_sends_presets_and_valid_saved_decks(page):
    posts = room_posts(page)
    page.evaluate("""async () => {
        DeckStore.create('mine', await fetchPresetPages('level2'));
        DeckStore.create('broken', Array(32).fill('M-001'));
        renderLanding();
    }""")
    open_npc_setup(page)
    assert page.locator("#deck-npc-opp").input_value() == "npc:random"
    start_npc(page)
    candidates = posts[-1]["npc_decks"]
    presets = page.evaluate("PRESETS.map(p => ({preset: p.id}))")
    mine = page.evaluate("DeckStore.list().find(d => d.name === 'mine').pages")
    assert candidates == presets + [{"pages": mine}]                          # 不合法牌組不列入
    assert "npc_deck" not in posts[-1]


def test_npc_actions_reach_the_board(page):
    start_npc(page)
    page.wait_for_function("R.awaited_player === 0", timeout=NPC_WAIT_MS)
    if page.evaluate("S.phase") == "start":
        page.evaluate("send({type: 'flip_pages', player: 0, count: 0})")
        page.wait_for_function("R.awaited_player === 0 && S.phase === 'battle'", timeout=NPC_WAIT_MS)
    before = page.evaluate("S.event_count")
    page.evaluate("send({type: 'pass', player: 0})")
    page.wait_for_function(f"S.event_count > {before} + 1 && R.awaited_player === 0", timeout=NPC_WAIT_MS)
    assert "NPC(一般)" in page.locator("#log").text_content()                # NPC 的行動以 NPC 名稱記錄


def test_cheat_panel_in_npc_room_loads_npc_book(page):
    open_npc_setup(page)
    page.select_option("#npc-level", "dummy")
    start_npc(page)
    page.locator("#cheat-toggle").click()
    page.wait_for_function("CHEAT && CHEAT.players && !CHEAT.busy")
    assert page.evaluate("CHEAT.players.length") == 2
    assert page.evaluate("CHEAT.players[1].book.length") == 32
    assert page.locator("#cheat-players button").nth(1).text_content() == "NPC(木人樁)"


def test_game_end_names_the_npc_deck(page):
    start_npc(page)
    page.evaluate("DeckStore.create('mine', Array(32).fill('M-002'))")
    for deck, expected in (("{preset: 'level2'}", "PRESETS.find(p => p.id === 'level2').name"),
                           ("{pages: Array(32).fill('M-002')}", "'mine'"),
                           ("{pages: Array(32).fill('M-003')}", "t('ui.npc.custom_deck')")):
        text = page.evaluate(f"""() => {{
            R = {{...R, npc: {{...R.npc, deck: {deck}}}}};
            S = {{...S, phase: 'game_over', winner: 0, end_reason: 'book_out'}};
            renderTopbar();
            return document.getElementById('acting-info').textContent;
        }}""")
        assert page.evaluate(f"t('ui.npc.deck_reveal', {{deck: {expected}}})") in text
