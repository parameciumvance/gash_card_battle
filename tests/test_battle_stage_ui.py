"""對決舞台的攻防卡面(battle-ui「對決舞台的攻防卡面」)。以本機測試模式(level1 預組)操作,
邊界情況(魔物效果攻擊、被無效)以前端改寫快照模擬。需要 playwright 與 Chromium。"""
from tests.test_battle_info_ui import cmd, start_local


def side(page, which):
    return page.locator(f"#stage-content .stage-side.{which}")


def side_cards(page, which):
    return side(page, which).locator(".stage-card").evaluate_all("els => els.map((e) => e.dataset.card)")


def declare_attack(page):
    """回合玩家以賈修(P1)與 P3 的 S-001 宣告攻擊,停在戰鬥開始確認。"""
    start_local(page)
    cmd(page, {"type": "flip_pages", "count": 0, "player": "tp"})
    cmd(page, {"type": "declare_attack", "page": 3, "player": "tp"})
    page.wait_for_function("S.battle_in")


def test_attack_cards_shown_from_battle_in(page):
    declare_attack(page)
    assert side_cards(page, "attack") == ["M-001", "S-001"]


def test_defense_side_waits_then_shows_cards(page):
    declare_attack(page)
    cmd(page, {"type": "battle_in_response", "allow": True, "player": "op"})
    page.wait_for_function("S.battle && S.battle.step === 'defense'")
    assert side_cards(page, "defense") == []
    assert "等待防禦宣告" in side(page, "defense").inner_text()
    cmd(page, {"type": "declare_defense", "page": 2, "player": "op"})          # P2 = S-025
    page.wait_for_function("S.battle && S.battle.defense_spell")
    assert side_cards(page, "defense") == ["M-001", "S-025"]


def test_no_defense(page):
    declare_attack(page)
    cmd(page, {"type": "battle_in_response", "allow": True, "player": "op"})
    cmd(page, {"type": "no_defense", "player": "op"})
    page.wait_for_function("S.battle && S.battle.step === 'effects'")
    assert side_cards(page, "defense") == []
    assert "不防禦" in side(page, "defense").inner_text()


def patch_battle(page, fields):
    page.evaluate("(f) => { S = {...S, battle: {...S.battle, ...f}}; render(); }", fields)


def to_effects(page):
    declare_attack(page)
    cmd(page, {"type": "battle_in_response", "allow": True, "player": "op"})
    cmd(page, {"type": "no_defense", "player": "op"})
    page.wait_for_function("S.battle && S.battle.step === 'effects'")


def test_mamodo_attack_shows_fixed_power_source(page):
    to_effects(page)
    patch_battle(page, {"attack_spell": None, "attacker_breakdown": [
        {"kind": "fixed", "source": "S-048", "amount": 5000}]})
    assert side_cards(page, "attack") == ["M-001", "S-048"]


def test_negated_attack_marked(page):
    to_effects(page)
    assert side(page, "attack").locator(".stage-negated").count() == 0
    patch_battle(page, {"attack_negated": True})
    assert side(page, "attack").locator(".stage-negated").inner_text() == "無效"


def test_stage_card_opens_display_only_zoom(page):
    to_effects(page)
    side(page, "attack").locator('.stage-card[data-card="S-001"]').click()
    assert page.locator("#zoom-card .card").is_visible()
    assert page.locator("#zoom-actions button").count() == 0
