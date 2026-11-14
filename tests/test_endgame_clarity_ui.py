"""終局的顯示(battle-ui「魔書耗盡的進度顯示」「勝負原因文字」「最後一對頁警示」「結算面板」)。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_endgame_clarity_ui.py -q
"""
from tests.test_npc_ui import room_posts, start_npc
from tests.test_timing_ui import send, start_as, zone_of
from tests.test_turn_dial_ui import button, note_of

RESULT = "#info-overlay:not(.hidden)"


def end_game(page, winner, reason="book_out", players=None):
    """把快照改成對局結束(players: {玩家: 欄位})並跑一次終局處理;NPC 牌組設為 level2 預組。"""
    page.evaluate("""([winner, reason, players]) => {
        wsWanted = false;                       // NPC 的推送不再蓋掉改過的快照
        if (ws) ws.close();
        if (R && R.npc) R = {...R, npc: {...R.npc, deck: {preset: 'level2'}}};   // 伺服器在終局才公開 NPC 牌組
        const ps = S.players.map((p, i) => ({...p, ...(players[i] || {})}));
        S = {...S, phase: 'game_over', winner, end_reason: reason, players: ps};
        render();
        maybeShowResult();
    }""", [winner, reason, {str(k): v for k, v in (players or {}).items()}])


def result_text(page):
    page.wait_for_selector(RESULT)
    return page.locator("#info-overlay").text_content()


# ---------------------------------------------------------------- 魔書耗盡、原因文字

def test_book_shows_exhausted(page):
    tp, me = start_as(page, "turn")
    end_game(page, 1 - tp, players={tp: {"pos": 34}})
    book = page.locator(f"{zone_of(page, tp)} .book-cover")                    # 顯示在魔書書皮上
    assert book.locator(".book-exhausted").text_content() == "魔書耗盡" and "34" not in book.text_content()
    assert page.locator(f"{zone_of(page, 1 - tp)} .book-exhausted").count() == 0



def test_reason_names_the_loser(page):
    tp, me = start_as(page, "turn")
    end_game(page, 1 - tp, players={tp: {"pos": 34}})
    loser = page.evaluate(f"pname({tp})")
    reason = f"{loser}的魔書無法再翻頁"
    assert reason in page.locator("#stage-result").text_content()
    assert "對手魔書" not in page.locator("#stage-result").text_content()
    assert reason in result_text(page)


def test_log_reason_names_the_loser(page):
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    text = page.evaluate("logLine({type: 'game_ended', winner: 0, reason: 'no_mamodo'})")
    assert text == page.evaluate("t('log.game_ended', {player: pname(0), reason: t('ui.reason.no_mamodo', {player: pname(1)})})")
    assert page.evaluate("pname(1)") + "無法再放出魔物" in text


# ---------------------------------------------------------------- 最後一對頁警示

WARN = "#action-bar .end-flip-warning"


def set_last_page(page, player, passes=0):
    page.evaluate("""([p, passes]) => {
        const ps = S.players.map((x, i) => i === p ? {...x, end_flip_loses: true} : x);
        S = {...S, players: ps, consecutive_passes: passes, action_player: passes ? p : S.action_player};
        render();
    }""", [player, passes])


def test_last_page_warning_on_own_turn(page):
    tp, me = start_as(page, "turn")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    assert page.locator(WARN).count() == 0
    set_last_page(page, tp)
    assert "本回合結束時將因無頁可翻而落敗" in page.locator(WARN).text_content()
    assert note_of(page, "Pass") == "不進行自己回合行動"       # 還不會結束回合


def test_pass_note_when_pass_ends_turn(page):
    tp, me = start_as(page, "turn")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    set_last_page(page, tp, passes=1)
    assert note_of(page, "Pass") == "本回合將結束,你會因無頁可翻而落敗"


def test_no_warning_for_opponents_last_page(page):
    tp, me = start_as(page, "other")
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "pass"})
    page.wait_for_function(f"S.action_player === {me}")
    set_last_page(page, tp)
    page.evaluate(f"S = {{...S, action_player: {me}, consecutive_passes: 1}}; render();")
    assert page.locator(WARN).count() == 0
    assert note_of(page, "Pass") == "不進行對手回合行動"
    page.evaluate("SESSION = {...SESSION, viewer: 'spectator'}; render();")
    assert page.locator(WARN).count() == 0


# ---------------------------------------------------------------- 結算面板

def test_npc_defeat_panel_and_rematch(page):
    posts = room_posts(page)
    start_npc(page)
    first = page.evaluate("SESSION.code")
    end_game(page, 1, players={0: {"pos": 34}})
    text = result_text(page)
    assert "落敗" in text
    assert page.evaluate("t('ui.reason.book_out', {player: pname(0)})") in text
    assert page.evaluate("t('ui.result.turns', {n: S.turn_no})") in text
    assert page.evaluate("t('ui.npc.deck_reveal', {deck: npcDeckName(R.npc.deck)})") in text
    rows = page.locator("#info-overlay .result-player").all_text_contents()
    assert len(rows) == 2 and "剩餘 0 頁" in rows[0]
    buttons = page.locator("#info-overlay .result-actions button").all_text_contents()
    assert buttons == ["再戰", "返回首頁"]
    page.locator("#info-overlay .result-actions button", has_text="再戰").click()
    page.wait_for_function(f"SESSION && SESSION.code !== '{first}' && S && S.phase !== 'game_over'")
    assert posts[-1] == posts[0]                                  # 同樣的設定
    assert not page.locator(RESULT).count()


def test_win_panel_and_back_home(page):
    start_npc(page)
    end_game(page, 0, reason="no_mamodo")
    assert "勝利" in result_text(page)
    page.locator("#info-overlay .result-actions button", has_text="返回首頁").click()
    page.wait_for_function("!SESSION")
    assert page.locator("#landing").is_visible()


def test_close_and_reopen_panel(page):
    tp, me = start_as(page, "turn")
    end_game(page, tp)
    page.wait_for_selector(RESULT)
    page.locator("#info-close").click()
    assert not page.locator(RESULT).count()
    reopen = page.locator("#stage-result .result-reopen")
    assert reopen.is_visible()
    reopen.click()
    page.wait_for_selector(RESULT)
    page.evaluate("render(); maybeShowResult()")                  # 同一局不再自動跳出第二次
    page.locator("#info-close").click()
    page.evaluate("render(); maybeShowResult()")
    assert not page.locator(RESULT).count()


def test_local_panel_rematch(page):
    posts = room_posts(page)
    tp, _ = start_as(page, "all")
    first = page.evaluate("SESSION.code")
    end_game(page, tp)
    text = result_text(page)
    assert page.evaluate(f"t('ui.winner', {{player: pname({tp})}})") in text
    buttons = page.locator("#info-overlay .result-actions button").all_text_contents()
    assert buttons == ["再來一場", "返回首頁"]
    page.locator("#info-overlay .result-actions button", has_text="再來一場").click()
    page.wait_for_function(f"SESSION && SESSION.code !== '{first}' && S && S.phase === 'start'")
    assert posts[-1] == posts[0]


def test_no_rematch_without_setup(page):
    tp, _ = start_as(page, "all")
    page.evaluate("LAST_SETUP = null")                            # 重新整理後接回:沒有開局設定
    end_game(page, tp)
    page.wait_for_selector(RESULT)
    assert page.locator("#info-overlay .result-actions button").all_text_contents() == ["返回首頁"]


def test_spectator_panel(page):
    tp, _ = start_as(page, "all")
    page.evaluate("SESSION = {...SESSION, viewer: 'spectator'}")
    end_game(page, tp)
    text = result_text(page)
    assert page.evaluate(f"t('ui.winner', {{player: pname({tp})}})") in text
    assert "勝利" not in text and "落敗" not in text
    assert page.locator("#info-overlay .result-actions button").all_text_contents() == ["返回首頁"]


def test_no_end_choice_left_in_action_bar(page):
    tp, _ = start_as(page, "all")
    end_game(page, tp)
    assert page.locator("#action-bar .table-choice").count() == 0
    assert button(page, "Pass").count() == 0
