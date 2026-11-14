"""E-052 選擇被無效的效果的對話框(card-effects「第 4 賽季事件卡 E-052」,season4-e052)。"""
from tests.test_cheat_editor import pw  # noqa: F401


def test_pick_negated_effect_dialog(page):
    page.evaluate("startLocal()")
    page.evaluate("""() => {
      S.pending = {kind: 'pick_negated_effect', player: S.turn_player, source: 'E-052',
                   options: [{value: 7, label: 'negated_effect', card: 'E-009', kind: 'event'},
                             {value: 8, label: 'negated_effect', card: 'S-001', kind: 'attack'}]};
      render();
    }""")
    assert page.locator("#action-bar .choice-title").inner_text().endswith("選擇要當作沒使用過的效果")
    texts = page.locator("#action-bar button").all_text_contents()
    event, spell = page.evaluate("[cname('E-009'), cname('S-001')]")
    assert any(f"「{event}」的事件卡" in t for t in texts)
    assert any(f"「{spell}」的攻擊" in t for t in texts)


def test_effect_undone_log_lists_what_came_back(page):
    # 費用是棄牌時不寫「退回 0 MP」,改列回到原位的卡;有退回 MP 才寫 MP
    page.evaluate("startLocal()")
    card, m032 = page.evaluate("[cname('M-033'), cname('M-032')]")
    discard_only = page.evaluate(
        "logLine({type: 'effect_undone', player: 0, card: 'M-033', kind: 'ability', mp: 0, returned: ['M-033']})")
    assert "0 MP" not in discard_only and f"「{card}」 回到原位" in discard_only
    mp_only = page.evaluate(
        "logLine({type: 'effect_undone', player: 0, card: 'PR-002', kind: 'ability', mp: 3, returned: []})")
    assert "退回 3 MP" in mp_only and "回到原位" not in mp_only
    neither = page.evaluate(
        "logLine({type: 'effect_undone', player: 0, card: 'M-032', kind: 'jammer', mp: 0, returned: []})")
    assert "MP" not in neither and "回到原位" not in neither and m032 in neither
