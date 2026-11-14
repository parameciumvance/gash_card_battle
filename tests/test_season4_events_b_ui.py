"""有戰鬥圖示的事件卡(E-053)的使用按鈕(game-engine「戰鬥中使用魔書的事件卡」,season4-events-b)。"""
from tests.test_cheat_editor import pw  # noqa: F401


def setup_e053(page, in_battle):
    """非回合玩家 p 的今のページ有 E-053;in_battle 時停在「効果の使用」輪到 p,否則為非戰鬥中輪到 p。"""
    page.evaluate("startLocal()")
    return page.evaluate("""(inBattle) => {
      const p = 1 - S.turn_player;
      S.phase = 'battle'; S.battle_in = null; S.pending = null;
      S.action_player = p;
      S.battle = inBattle ? {step: 'effects', effect_turn: p, attacker: S.turn_player} : null;
      S.players[p].open_pages = [{page: 2, card: 'E-053', cost: 0, condition_ok: true}];
      S.players[p].events_exhausted = false;
      render();
      zoom('E-053', {kind: 'page', p, page: 2});
      return p;
    }""", in_battle)


def test_e053_usable_in_battle_effects(page):
    p = setup_e053(page, True)
    buttons = page.locator("#zoom-actions button")
    assert buttons.all_text_contents() == ["使用"]
    assert buttons.first.is_enabled()
    state = page.evaluate("S")
    page.route("**/commands", lambda route: route.fulfill(json={"state": state}))
    with page.expect_request(lambda r: r.url.endswith('/commands')) as sent:
        buttons.first.click()
    assert sent.value.post_data_json["command"] == {"type": "use_book_card", "player": p, "page": 2}


def test_e053_disabled_outside_battle(page):
    setup_e053(page, False)
    button = page.locator("#zoom-actions button")
    assert button.all_text_contents() == ["使用"]
    assert button.first.is_disabled()
    assert page.locator("#zoom-actions .zoom-reason").inner_text() == page.evaluate("t('ui.why.battle_only')")
