"""教學對局的瀏覽器測試(tutorial、battle-ui「首頁的模式入口」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_tutorial_ui.py -q
"""
import pytest

MENU = "#card-menu:not(.hidden)"


def start(page):
    page.locator("#entry-tutorial").click()
    page.wait_for_function("S && TUTORIAL && !document.getElementById('tutorial-panel').classList.contains('hidden')")


def step(page):
    return page.evaluate("TUTORIAL ? tutorialStep().id : null")


def settle(page, timeout=15000):
    """等到輪到玩家、沒有送出中的指令,動畫播完。"""
    page.wait_for_function("S && awaitedPlayer() === 0 && SENDING === 0", timeout=timeout)
    page.evaluate("Anim.idle()")
    page.wait_for_timeout(200)


def wait_step(page, n, timeout=15000):
    page.wait_for_function(f"TUTORIAL && tutorialStep().id === {n}", timeout=timeout)


def next_btn(page):
    page.locator("#tutorial-panel button", has_text="下一步").click()


def target(page):
    return page.locator(".tutorial-target").first


def card_action(page, label):
    """點發光的目標卡,在卡片選單按 label。"""
    target(page).click()
    page.wait_for_selector(MENU)
    buttons = page.locator("#card-menu button").all_inner_texts()
    assert any(label in b for b in buttons), (step(page), buttons)
    page.locator("#card-menu button", has_text=label).first.click()


def bar(page, label):
    page.locator("#action-bar button", has_text=label).first.click()


def sent_spy(page):
    page.evaluate("""() => { window.__sent = []; const orig = api;
      api = (path, opts) => { if (path.endsWith('/commands')) window.__sent.push(JSON.parse(opts.body).command);
        return orig(path, opts); }; }""")


# ---------------------------------------------------------------- 入口與基本行為

def test_entry_is_first_and_starts_tutorial(page):
    entries = page.locator("#landing-cards .entry").evaluate_all("(es) => es.map((e) => e.id)")
    assert entries[0] == "entry-tutorial" and entries[1] == "entry-npc"
    assert page.locator("#entry-tutorial .entry-title").inner_text() == "教學"
    assert not page.locator("#entry-tutorial .entry-badge").is_visible()
    start(page)
    assert step(page) == 1
    assert page.evaluate("[S.turn_player, SESSION.mode, myViewer()]") == [0, "tutorial", 0]
    assert page.locator("#tutorial-panel").inner_text().startswith("教學 1 / 17")
    assert page.locator("#forfeit").is_hidden()                                   # 教學不能棄權
    assert page.locator(".auto-pass-toggle").count() == 0                          # 沒有自動 pass
    assert page.evaluate("localStorage.getItem(`gash-room-${SESSION.code}`)") is None   # 不在返回清單


def test_locked_step_blocks_other_commands(page):
    start(page)
    next_btn(page)
    assert step(page) == 2 and "不翻頁" in target(page).inner_text()
    sent_spy(page)
    page.evaluate("send({type: 'flip_pages', player: 0, count: 1})")
    assert page.evaluate("window.__sent") == []                                   # 不送出
    assert page.locator("#toast").inner_text() == "這一步請按「不翻頁」"
    assert page.evaluate("S.phase") == "start"
    target(page).click()
    wait_step(page, 3)


def test_opponent_waits_for_next(page):
    start(page)
    next_btn(page)
    target(page).click()
    wait_step(page, 3)
    settle(page)
    card_action(page, "放出")
    wait_step(page, 4)
    page.wait_for_timeout(2500)                                                   # 對手的出手間隔過了也不動
    assert page.evaluate("awaitedPlayer()") == 1 and page.evaluate("S.action_player") == 1
    next_btn(page)
    page.wait_for_function("awaitedPlayer() === 0", timeout=10000)                 # 按下一步後對手 pass
    assert step(page) == 5


def test_leave_closes_room(page):
    start(page)
    code = page.evaluate("SESSION.code")
    page.locator("#tutorial-panel .tutorial-leave").click()
    page.wait_for_function("!SESSION && !document.getElementById('landing').classList.contains('hidden')")
    status = page.evaluate(f"fetch('/api/rooms/{code}/state').then((r) => r.status)")
    assert status == 404
    assert page.locator("#tutorial-panel").is_hidden()


# ---------------------------------------------------------------- 走完全程

def play_through(page, protect_label):
    start(page)
    next_btn(page)                                                                # 1 介紹
    target(page).click()                                                          # 2 不翻頁
    wait_step(page, 3)
    settle(page)
    card_action(page, "放出")                                                     # 3 高嶺清人
    wait_step(page, 4)
    next_btn(page)                                                                # 4 對手 pass
    settle(page)
    card_action(page, "棄掉此卡→效果")                                            # 5 搭檔效果
    wait_step(page, 6)
    settle(page)
    card_action(page, "攻擊")                                                     # 6 薩喀爾
    settle(page)
    assert page.evaluate("S.battle && S.battle.step") == "effects"
    bar(page, "Pass")
    wait_step(page, 7)
    settle(page)
    bar(page, "Pass")                                                             # 7 連續 pass
    wait_step(page, 8)
    settle(page)
    assert page.evaluate("!!S.battle_in")
    card_action(page, "放出")                                                     # 8 插入:放出蒂歐
    wait_step(page, 9)
    settle(page)
    bar(page, "同意進入戰鬥")                                                     # 9
    wait_step(page, 10)
    settle(page)
    card_action(page, "防禦")                                                     # 10 仙希爾
    settle(page)
    bar(page, "Pass")
    wait_step(page, 11)
    settle(page)
    bar(page, "同意進入戰鬥")                                                     # 11 第二次攻擊
    settle(page)
    bar(page, "不防禦")
    settle(page)
    bar(page, "Pass")
    settle(page)
    assert page.evaluate("S.pending && S.pending.kind") == "protect"
    protect_label(page)
    wait_step(page, 12)
    settle(page)
    bar(page, "Pass")                                                             # 12
    wait_step(page, 13)
    settle(page)
    target(page).click()                                                          # 13 › 選翻 1 張
    bar(page, "翻 1 張")
    wait_step(page, 14)
    settle(page)
    card_action(page, "使用")                                                     # 14 鰤魚
    wait_step(page, 15)
    settle(page)
    card_action(page, "攻擊")                                                     # 15 薩喀爾
    wait_step(page, 16)
    settle(page)
    card_action(page, "效果(MP 1)")                                              # 16 賈修的效果
    settle(page)
    bar(page, "Pass")
    wait_step(page, 17)


@pytest.mark.slow
@pytest.mark.parametrize("protect", ["none", "mamodo"])
def test_play_through(page, protect):
    def choose(page):
        if protect == "none":
            page.evaluate("send({type: 'choose', player: 0, value: null})")
        else:
            uid = page.evaluate("S.players[0].slots.find((s) => s.top === 'Ex-005').uid")
            page.evaluate(f"send({{type: 'choose', player: 0, value: {uid}}})")
    play_through(page, choose)
    log = page.locator("#log").inner_text()
    assert "7000" in log and "6000" in log                                        # 回合 3 的魔力勝負
    panel = page.locator("#tutorial-panel")
    assert "教學完成" in panel.inner_text()
    assert page.evaluate("localStorage.getItem('gash-tutorial-done')") == "1"
    panel.locator("button", has_text="開始 NPC 對戰").click()
    page.wait_for_function("!SESSION && !document.getElementById('setup').classList.contains('hidden')")
    page.locator("#setup-back").click()
    assert page.locator("#entry-tutorial .entry-badge").is_visible()
    assert page.locator("#entry-tutorial .entry-badge").inner_text() == "已完成"
