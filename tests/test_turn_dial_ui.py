"""行動欄附註與回合轉盤的瀏覽器測試(battle-ui「行動選項附註」「回合與時機指示」)。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_turn_dial_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture
from tests.test_timing_ui import send, start_as, zone_of


def button(page, label):
    return page.locator("#action-bar button", has=page.locator(".btn-label", has_text=label))


def note_of(page, label):
    return button(page, label).locator(".btn-note").text_content()


GIVE_MAMODO = """async (p) => {
    const headers = {'X-Player-Token': SESSION.tokens[p], 'Content-Type': 'application/json'};
    const base = `/api/rooms/${SESSION.code}`;
    const d = await api(`${base}/debug-state`, {headers});
    d.players[p].book[1] = 'M-004';                                   // 第 2 頁:可放出的魔物
    await api(`${base}/debug-state`, {method: 'POST', headers, body: JSON.stringify(d)});
    applyPayload(await api(`${base}/state`, {headers}));
}"""


def to_effects(page, tp, me):
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "declare_attack", "page": 3})
    page.wait_for_function("S.battle_in")
    send(page, me, {"type": "battle_in_response", "allow": True})
    page.wait_for_function("S.battle && S.battle.step === 'defense'")
    send(page, me, {"type": "no_defense"})
    page.wait_for_function("S.battle && S.battle.step === 'effects'")


# ---------------------------------------------------------------- 行動欄附註

def test_pass_note_own_and_opponent_turn(page):
    tp, me = start_as(page, "turn")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    assert note_of(page, "Pass") == "不進行自己回合行動"
    tp, me = start_as(page, "other")
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "pass"})
    page.wait_for_function(f"S.action_player === {me}")
    assert note_of(page, "Pass") == "不進行對手回合行動"


def test_allow_battle_note_and_no_defense_plain(page):
    tp, me = start_as(page, "other")
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "declare_attack", "page": 3})
    page.wait_for_function("S.battle_in")
    assert note_of(page, "迎戰") == "或選擇非戰鬥行動而不迎戰"
    assert button(page, "迎戰").locator(".btn-label").text_content() == "迎戰"
    send(page, me, {"type": "battle_in_response", "allow": True})
    page.wait_for_function("S.battle && S.battle.step === 'defense'")
    no_def = page.locator("#action-bar button", has_text="不防禦")
    assert no_def.count() == 1 and no_def.locator(".btn-note").count() == 0


def test_battle_effect_pass_note(page):
    tp, me = start_as(page, "all")
    to_effects(page, tp, 1 - tp)
    assert note_of(page, "Pass") == "不使用戰鬥中效果"


# ---------------------------------------------------------------- 回合轉盤

def dial(page):
    return page.evaluate("""() => {
        const c = document.getElementById('turn-cluster');
        const d = document.getElementById('turn-dial');
        const p = document.getElementById('acting-pointer');
        return {angle: Number(d.dataset.angle), hidden: c.classList.contains('hidden') || !c.offsetParent,
                center: d.querySelector('.dial-center').textContent,
                note: document.getElementById('dial-note').offsetParent ? document.getElementById('dial-note').textContent : '',
                acting_up: p.classList.contains('up')};
    }""")


def assert_in_action_bar(page):
    pos = page.evaluate("""() => {
        const b = document.getElementById('action-bar').getBoundingClientRect();
        const d = document.getElementById('turn-dial').getBoundingClientRect();
        const m = document.getElementById('action-main').getBoundingClientRect();
        return {inside: d.top >= b.top && d.bottom <= b.bottom, left: d.right <= m.left};
    }""")
    assert pos["inside"] and pos["left"]                                 # 行動欄內、在行動選項的左邊


def base_angle(page, player):
    return 180 if page.evaluate(f"topPlayerIndex() === {player}") else 0


def test_dial_points_to_turn_player_and_no_badge(page):
    tp, me = start_as(page, "other")
    d = dial(page)
    assert d and not d["hidden"] and d["angle"] % 360 == base_angle(page, tp)
    assert d["center"] == "開始階段" and d["acting_up"] == page.evaluate(f"topPlayerIndex() === {tp}")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    assert dial(page)["center"] == "非戰鬥"
    assert page.locator("#action-bar .summary").count() == 0              # 摘要文字由轉盤取代
    assert page.evaluate("document.getElementById('turn-cluster').getAttribute('aria-label')") == \
        page.evaluate(f"`等待 ${{pname({tp})}} 行動(對手的回合・非戰鬥中)`")
    assert page.locator(".pz-head .turn-marker").count() == 0
    assert page.locator(f"{zone_of(page, tp)} .pz-head").text_content().find("回合玩家") == -1
    assert_in_action_bar(page)


def test_dial_tilts_on_pass_and_returns_on_action(page):
    tp, me = start_as(page, "all")
    send(page, tp, {"type": "flip_pages", "count": 0})
    base = base_angle(page, tp)
    assert dial(page)["note"] == ""
    send(page, tp, {"type": "pass"})
    page.wait_for_function("S.consecutive_passes === 1")
    d = dial(page)
    assert d["acting_up"] == page.evaluate(f"topPlayerIndex() === {1 - tp}")   # 行動玩家箭頭指向對手
    name = page.evaluate(f"pname({1 - tp})")
    assert d["angle"] % 360 == (base + 45) % 360 and d["note"] == f"已 pass 一次,再 pass 就換 {name} 的回合"
    other = 1 - tp
    page.evaluate(GIVE_MAMODO, other)
    send(page, other, {"type": "play_card", "page": 2})                 # 對手行動 → 轉回
    page.wait_for_function("S.consecutive_passes === 0")
    d = dial(page)
    assert d["angle"] % 360 == base and d["note"] == ""


def test_dial_turns_clockwise_to_opponent(page):
    tp, me = start_as(page, "all")
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "pass"})
    page.wait_for_function("S.consecutive_passes === 1")
    tilted = dial(page)["angle"]
    send(page, 1 - tp, {"type": "pass"})
    page.wait_for_function(f"S.turn_player === {1 - tp}")
    after = dial(page)["angle"]
    assert after > tilted and after - tilted == 135                     # 順時鐘繼續轉到對面
    assert after % 360 == base_angle(page, 1 - tp)


def test_dial_battle_pass_no_tilt_and_docked(page):
    tp, me = start_as(page, "all")
    to_effects(page, tp, 1 - tp)
    base = base_angle(page, tp)
    send(page, tp, {"type": "pass"})
    page.wait_for_function("S.battle && S.battle.effect_turn !== null")
    d = dial(page)
    assert d["angle"] % 360 == base and d["center"] == "戰鬥中" and d["note"] == ""
    assert_in_action_bar(page)


def test_spectator_sees_dial_and_hidden_after_game_over(page):
    tp, _ = start_as(page, "all")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.evaluate("SESSION = {...SESSION, viewer: 'spectator'}; render();")
    assert not dial(page)["hidden"]
    page.evaluate("S = {...S, phase: 'game_over', winner: 0, end_reason: 'book_out'}; render();")
    assert dial(page)["hidden"]


def test_dial_note_names_next_turn_by_viewer(page):
    tp, me = start_as(page, "turn")
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "pass"})                                     # 自己的回合 pass
    page.wait_for_function("S.consecutive_passes === 1")
    assert dial(page)["note"] == "已 pass 一次,再 pass 就換對手的回合"
    tp, me = start_as(page, "other")
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "pass"})                                     # 對手的回合、對手 pass
    page.wait_for_function("S.consecutive_passes === 1")
    assert dial(page)["note"] == "已 pass 一次,再 pass 就換你的回合"


FITS = """() => {
    const el = document.querySelector('#turn-dial .dial-center');
    return {text: el.textContent, fits: el.scrollWidth <= el.clientWidth && el.scrollHeight <= el.clientHeight};
}"""


def test_dial_text_fits_in_each_language(page):
    tp, _ = start_as(page, "all")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    for lang, nonbattle, battle in (("en", "No BATTLE", "BATTLE"), ("ja", "非バトル", "バトル中")):
        page.evaluate(f"setLang('{lang}')")
        page.wait_for_function(f"document.querySelector('#turn-dial .dial-center').textContent === '{nonbattle}'")
        assert page.evaluate(FITS)["fits"]
    send(page, tp, {"type": "declare_attack", "page": 3})
    page.wait_for_function("S.battle_in")
    r = page.evaluate(FITS)
    assert r["text"] == "バトル中" and r["fits"]
    page.evaluate("setLang('en')")
    page.wait_for_function("document.querySelector('#turn-dial .dial-center').textContent === 'BATTLE'")
    assert page.evaluate(FITS)["fits"]
