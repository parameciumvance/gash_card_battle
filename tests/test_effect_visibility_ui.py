"""效果資訊醒目顯示的瀏覽器測試(battle-ui「魔力與費用的分色」「放大檢視的數值明細」「常駐效果失效的標示」
「效果來源卡聚焦」「效果被擋下的記錄與聚焦」「傷害被防止的記錄寫出來源」)。以本機測試模式操作,快照欄位以前端改寫模擬。"""
import pytest
from tests.test_spell_user_ui import open_page_zoom, start_local


def patch_slot(page, tp, fields):
    """把先攻方第一隻魔物的快照欄位改寫(只在前端)後重繪。"""
    page.evaluate("""([tp, fields]) => {
      S = {...S, players: S.players.map((ps, i) => i !== tp ? ps
        : {...ps, slots: ps.slots.map((s, j) => j ? s : {...s, ...fields})})};
      render();
    }""", [tp, fields])
    return page.evaluate(f"S.players[{tp}].slots[0].uid")


def patch_page(page, tp, pg, fields):
    page.evaluate("""([tp, pg, fields]) => {
      S = {...S, players: S.players.map((ps, i) => i !== tp ? ps
        : {...ps, open_pages: ps.open_pages.map((e) => e.page !== pg ? e : {...e, ...fields})})};
      render();
    }""", [tp, pg, fields])


def slot_card(page, uid):
    return page.locator(f'[data-slot-uid="{uid}"][data-zone-kind="mamodo"]')


def zoom_slot(page, tp, uid):
    page.evaluate(f"zoom(S.players[{tp}].slots.find((s) => s.uid === {uid}).top, {{kind: 'slot', p: {tp}, uid: {uid}}})")


def item(kind, source, amount):
    return {"kind": kind, "source": source, "amount": amount}


M003 = {"top": "M-003", "stack": ["M-003"], "power": 5000,
        "power_breakdown": [item("mamodo", "M-003", 4000), item("static", "M-003", 1000)], "blocked_effects": []}


# ---------------------------------------------------------------- 數值分色與明細

def test_power_above_card_is_green_with_breakdown(page):
    tp = start_local(page)
    uid = patch_slot(page, tp, M003)
    badge = slot_card(page, uid).locator(".val-badge")
    assert badge.count() == 1 and "val-good" in badge.get_attribute("class") and "5000" in badge.inner_text()
    zoom_slot(page, tp, uid)
    assert page.locator("#zoom-card .val-badge.val-power.val-good").count() == 1
    details = page.locator("#zoom-actions .zoom-details").inner_text()
    assert "常駐效果" in details and "+1000" in details and "4000" in details


def test_equal_values_show_neutral_badge(page):
    # 與卡面相同時也顯示徽章(一致),只是不著色;放大檢視不著色、不列明細
    tp = start_local(page)
    uid = page.evaluate(f"S.players[{tp}].slots[0].uid")
    power = page.evaluate(f"S.players[{tp}].slots[0].power")
    badge = slot_card(page, uid).locator(".val-badge")
    assert badge.count() == 1 and str(power) in badge.inner_text()
    assert not {"val-good", "val-bad"} & set(badge.get_attribute("class").split())
    zoom_slot(page, tp, uid)
    assert page.locator("#zoom-card .val-badge.val-good, #zoom-card .val-badge.val-bad").count() == 0
    assert page.locator("#zoom-actions .zoom-details").count() == 0


def test_event_cost_above_card_is_red_with_breakdown(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    page.evaluate(f"send({{type: 'flip_pages', player: {tp}, count: 0}})")
    page.wait_for_function("S.phase === 'battle'")
    patch_page(page, tp, pos, {"card": "E-001", "cost": 1,
                               "cost_breakdown": [item("card", "E-001", 0), item("opponent_event", "M-040", 1)]})
    card = page.locator(f'[data-page="{pos}"][data-card="E-001"]')
    assert "val-bad" in card.locator(".val-badge").get_attribute("class").split()
    assert card.locator(".val-badge").inner_text() == "1"                      # 費用只寫數值(蓋住卡圖的費用格)
    # 費用與卡面相同的另一頁(雙方魔書都有這個頁碼):中性徽章
    for cls in page.locator(f'[data-page="{pos + 1}"][data-card] .val-badge').evaluate_all("els => els.map((e) => e.className)"):
        assert not {"val-good", "val-bad"} & set(cls.split())
    open_page_zoom(page, tp, pos)
    assert page.locator("#zoom-card .val-badge.val-cost.val-bad").count() == 1
    details = page.locator("#zoom-actions .zoom-details").inner_text()
    assert "+1" in details and page.evaluate("cname('M-040')") in details


# ---------------------------------------------------------------- 常駐效果失效

def test_blocked_effect_badge_and_zoom(page):
    tp = start_local(page)
    uid = patch_slot(page, tp, {"top": "M-031", "stack": ["M-031"], "power": 4000,
                                "power_breakdown": [item("mamodo", "M-031", 4000)],
                                "blocked_effects": [{"card": "M-031", "by": ["E-025"]}]})
    assert slot_card(page, uid).locator(".badge.blocked-mark").inner_text() == "失效"
    zoom_slot(page, tp, uid)
    details = page.locator("#zoom-actions .zoom-details").inner_text()
    assert "失效" in details and page.evaluate("cname('E-025')") in details


# ---------------------------------------------------------------- 效果來源卡聚焦與記錄

def steps_of(page, me, events, actor):
    """視角設為 me,回傳這批事件的聚焦格(kind、card、lines)。"""
    start_local(page)
    page.evaluate("Anim.idle()")
    return page.evaluate("""([me, events, actor]) => {
      SESSION = {...SESSION, viewer: me};
      localStorage.setItem('gash-spotlight', 'normal');
      return Anim.timeline(events, actor, false, false)
        .map((s) => ({kind: s.kind, card: s.card || null, caption: s.caption || null, lines: s.lines}));
    }""", [me, events, actor])


def test_trigger_by_own_action_gets_source_card_step(page):
    # 自己以 1 個行動棄掉 M-046,對手的 P-013 翻自己的魔書:自己的動作也要以 P-013 的卡片格展示
    events = [{"type": "card_discarded", "player": 0, "card": "M-046", "zone": "mamodo", "reason": "action", "slot": 5},
              {"type": "pages_turned", "player": 0, "count": 1, "pos": 6, "source": "P-013"}]
    steps = steps_of(page, 0, events, 0)
    cards = [s for s in steps if s["kind"] == "card"]
    assert [s["card"] for s in cards] == ["P-013"]
    assert any("翻動 1 張" in line for line in cards[0]["lines"])


def test_own_passive_gets_card_step(page):
    steps = steps_of(page, 0, [{"type": "mp_changed", "player": 0, "delta": 1, "mp": 3, "reason": "M-002"}], 0)
    assert [(s["kind"], s["card"]) for s in steps] == [("card", "M-002")]


@pytest.mark.parametrize("source", ["PR-011", "Ex-008"])
def test_promo_and_ex_sources_get_card_step(page, source):
    # PR- / Ex- 卡號也是效果來源卡(D5:卡號格式不只 M/S/P/E)
    steps = steps_of(page, 0, [{"type": "mp_changed", "player": 0, "delta": 2, "mp": 3, "reason": source}], 0)
    assert [(s["kind"], s["card"]) for s in steps] == [("card", source)]


def test_log_links_promo_and_ex_card_names(page):
    start_local(page)
    refs = page.evaluate("cardRefs({type: 'mp_changed', reason: 'PR-011', card: 'Ex-008', other: 'XX-001'})")
    assert sorted(refs) == ["Ex-008", "PR-011"]


def test_same_source_as_used_card_is_merged(page):
    events = [{"type": "book_card_used", "player": 1, "card": "E-005", "page": 4},
              {"type": "pages_turned", "player": 0, "count": 1, "pos": 6, "source": "E-005"}]
    steps = steps_of(page, 0, events, 1)
    assert [(s["kind"], s["card"]) for s in steps] == [("card", "E-005")]
    assert len(steps[0]["lines"]) == 1


def test_effect_blocked_step_and_log(page):
    events = [{"type": "effect_blocked", "player": 0, "card": "M-031", "slot": 7, "by": ["E-025"], "when": "damage"},
              {"type": "mamodo_injured", "player": 0, "slot": 7, "card": "M-031"}]
    steps = steps_of(page, 0, events, 1)
    assert [(s["kind"], s["card"]) for s in steps] == [("card", "M-031")]
    assert len(steps[0]["lines"]) == 2
    line = page.evaluate("logLine({type: 'effect_blocked', player: 0, card: 'M-031', slot: 7, by: ['E-025'], when: 'damage'})")
    assert page.evaluate("cname('M-031')") in line and page.evaluate("cname('E-025')") in line


def test_damage_prevented_log_names_source(page):
    start_local(page)
    line = page.evaluate("logLine({type: 'damage_prevented', player: 0, slot: 7, reason: 'immunity', source: 'M-031'})")
    assert page.evaluate("cname('M-031')") in line
    plain = page.evaluate("logLine({type: 'damage_prevented', player: 0, slot: 7, reason: 'no_target'})")
    assert page.evaluate("cname('M-031')") not in plain
