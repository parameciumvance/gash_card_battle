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
    assert any(f"《{event}》的事件卡" in t for t in texts)
    assert any(f"《{spell}》的攻擊" in t for t in texts)
