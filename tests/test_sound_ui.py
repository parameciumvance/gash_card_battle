"""音效的瀏覽器測試(battle-ui「音效」「演出設定」)。
以 `Sfx.played` 驗證決定播放的音效,不量測實際聲音。需要 playwright 與 Chromium。
以本機測試模式操作,並把視角設為某一方,另一方的指令即為「對手」。

Run: python -m pytest tests/test_sound_ui.py -q
"""
import pytest

from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)
from tests.test_spotlight_ui import SPOT, open_page, send, start_as


@pytest.fixture
def quiet(browser, server):  # noqa: F811
    """聚焦關閉(音效改在盤面更新時播放),音效為缺省。"""
    context, page, errors = open_page(browser, server, prefs={"spotlight": "off"})
    yield page
    context.close()
    assert not errors


def played(page):
    return page.evaluate("Sfx.played.slice()")


def reset(page):
    page.evaluate("Anim.idle().then(() => { Sfx.played.length = 0; })")


def test_opponent_attack_cue_plays_with_spotlight(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, prefs={"spotlight": "normal"})
    opp = start_as(page, "defender")
    send(page, opp, {"type": "flip_pages", "count": 0})
    reset(page)
    send(page, opp, {"type": "declare_attack", "page": 3})                # S-001
    page.wait_for_selector(SPOT)
    assert played(page) == ["attack"]                                     # 聚焦出現時就響,盤面尚未更新
    assert page.locator("#battle-stage.open").count() == 0
    context.close()
    assert not errors


def test_own_card_play_cue(quiet):
    me = 1 - start_as(quiet, "turn")
    send(quiet, me, {"type": "flip_pages", "count": 1})                  # 翻開 P4=P-001
    quiet.wait_for_function("S.phase === 'battle'")
    reset(quiet)
    send(quiet, me, {"type": "play_card", "page": 4})
    quiet.wait_for_function(f"S.players[{me}].slots[0].partner === 'P-001'")
    quiet.evaluate("Anim.idle()")
    assert played(quiet) == ["card"]
    assert quiet.locator(SPOT).count() == 0


def test_only_the_most_important_cue_plays(quiet):
    opp = start_as(quiet, "defender")
    me = 1 - opp
    reset(quiet)
    quiet.evaluate(f"""Anim.apply([
        {{seq: 90001, type: 'pages_flipped', player: {me}, count: 2}},
        {{seq: 90002, type: 'damage_dealt', player: {me}, amount: 2}},
        {{seq: 90003, type: 'mp_changed', player: {me}, delta: 2, reason: 'damage'}},
    ], S, render, {opp})""")
    quiet.evaluate("Anim.idle()")
    assert played(quiet) == ["damage"]


def test_setup_and_cheat_batches_are_silent(quiet):
    start_as(quiet, "defender")
    reset(quiet)
    quiet.evaluate("Anim.apply([{seq: 90001, type: 'card_played', player: 0, card: 'M-001'}], S, render, null)")
    quiet.evaluate("Anim.idle()")
    assert played(quiet) == []


def test_your_turn_when_action_passes_to_me(quiet):
    opp = start_as(quiet, "turn")                                          # 對手是非回合玩家
    me = 1 - opp
    send(quiet, me, {"type": "flip_pages", "count": 0})
    send(quiet, me, {"type": "declare_attack", "page": 3})                 # 輪到對手回應迎戰
    quiet.wait_for_function(f"awaitedPlayer() === {opp}")
    quiet.evaluate("Anim.idle()")
    assert "your_turn" not in played(quiet)
    reset(quiet)
    send(quiet, opp, {"type": "battle_in_response", "allow": True})        # 對手迎戰 → 輪到對手宣告防禦
    send(quiet, opp, {"type": "no_defense"})                               # → 輪到自己(效果)
    quiet.wait_for_function(f"awaitedPlayer() === {me}")
    quiet.evaluate("Anim.idle()")
    assert played(quiet)[-1] == "your_turn"
    assert played(quiet).count("your_turn") == 1


def test_local_mode_has_no_your_turn(quiet):
    quiet.evaluate("startLocal()")
    quiet.wait_for_function("S && S.phase === 'start'")
    tp = quiet.evaluate("S.turn_player")
    send(quiet, tp, {"type": "flip_pages", "count": 0})
    send(quiet, tp, {"type": "declare_attack", "page": 3})
    quiet.wait_for_function(f"awaitedPlayer() === {1 - tp}")
    quiet.evaluate("Anim.idle()")
    assert "attack" in played(quiet)
    assert "your_turn" not in played(quiet)


@pytest.mark.parametrize("i_win", [True, False])
def test_win_and_lose_cues(quiet, i_win):
    opp = start_as(quiet, "defender")
    me = 1 - opp
    reset(quiet)
    winner = me if i_win else opp
    quiet.evaluate(f"""Anim.apply([{{seq: 90001, type: 'game_ended', winner: {winner}, reason: 'book'}}],
        S, render, {opp})""")
    quiet.evaluate("Anim.idle()")
    assert played(quiet) == ["win" if i_win else "lose"]


def test_sound_off_plays_nothing(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, prefs={"spotlight": "off", "sound": "off"})
    opp = start_as(page, "turn")
    me = 1 - opp
    send(page, me, {"type": "flip_pages", "count": 0})
    send(page, me, {"type": "declare_attack", "page": 3})
    send(page, opp, {"type": "battle_in_response", "allow": True})
    send(page, opp, {"type": "no_defense"})
    page.wait_for_function(f"awaitedPlayer() === {me}")
    page.evaluate("Anim.idle()")
    assert played(page) == []
    context.close()
    assert not errors


def test_sound_pref_defaults_on_and_is_remembered(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server)
    assert page.evaluate("pref('sound')") == "on"
    page.locator("#prefs-toggle").click()
    group = page.locator(".info-section", has_text="音效")
    assert group.locator("button[aria-pressed='true']").text_content() == "開"
    group.locator("button", has_text="關").click()
    assert page.evaluate("pref('sound')") == "off"
    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    assert page.evaluate("pref('sound')") == "off"
    context.close()
    assert not errors
