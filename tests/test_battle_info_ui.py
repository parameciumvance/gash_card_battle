"""對戰資訊的瀏覽器測試(battle-ui「擲幣重擲詢問顯示目前結果」「魔力明細檢視」「作用中效果清單」)。
需要 playwright 與 Chromium。以本機測試模式(level1 預組)操作。

Run: python -m pytest tests/test_battle_info_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)


def start_local(page):
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")


def cmd(page, command):
    """以回合玩家(或指定 player)送出指令;command 內 player 為 'tp' / 'op' 時換成對應玩家。"""
    page.evaluate("""async (c) => {
        const tp = S.turn_player;
        const player = c.player === 'op' ? 1 - tp : tp;
        await send({...c, player});
    }""", command)


def to_effects_step(page):
    """回合玩家以 P3 的 S-001 攻擊,對手不防禦,停在戰鬥中效果步驟。"""
    cmd(page, {"type": "flip_pages", "count": 0, "player": "tp"})
    cmd(page, {"type": "declare_attack", "page": 3, "player": "tp"})
    cmd(page, {"type": "battle_in_response", "allow": True, "player": "op"})
    cmd(page, {"type": "no_defense", "player": "op"})
    page.wait_for_function("S.battle && S.battle.step === 'effects'")


def info_rows(page):
    return page.locator("#info-body .info-row").all_text_contents()


# ---------------------------------------------------------------- 擲幣重擲詢問

COIN_PENDING = """(player) => {
    S = {...S, pending: {kind: 'coin_confirm', player, source: 'S-027',
         options: [{value: null, label: 'keep'}, {value: 0, label: 'reflip'}, {value: 1, label: 'reflip'}],
         info: {results: ['heads', 'tails']}}};
    render();
}"""


def test_reflip_dialog_lists_current_results(page):
    start_local(page)
    page.evaluate(COIN_PENDING, 0)
    notes = page.locator("#action-bar .choice-notes").text_content()
    assert "第 1 枚:正面" in notes and "第 2 枚:反面" in notes
    buttons = page.locator("#action-bar .choice-options button").all_text_contents()
    assert "重擲第 1 枚(正面)" in buttons and "重擲第 2 枚(反面)" in buttons


def test_waiting_player_sees_current_results(page):
    start_local(page)
    page.evaluate("SESSION = {...SESSION, viewer: 0}")                    # 以玩家 1 的視角等待
    page.evaluate(COIN_PENDING, 1)
    assert page.locator("#action-bar .choice-prompt").count() == 0
    assert "第 2 枚:反面" in page.locator("#acting-info").text_content()


# ---------------------------------------------------------------- 魔力明細

def test_showdown_log_entry_opens_breakdown(page):
    start_local(page)
    to_effects_step(page)
    cmd(page, {"type": "pass", "player": "tp"})
    cmd(page, {"type": "pass", "player": "op"})
    page.evaluate("async () => { if (S.pending) await send({type: 'choose', player: S.pending.player, value: null}); }")
    page.wait_for_function("document.querySelector('#log .breakdown-ref') && !S.pending")
    page.locator("#log .breakdown-ref").last.click()
    assert page.locator("#info-overlay").is_visible()
    assert page.locator("#info-title").text_content() == "魔力勝負明細"
    sections = page.locator("#info-body .info-section h4").all_text_contents()
    assert "合計 6000" in sections[0] and "合計 0" in sections[1]
    rows = info_rows(page)
    assert any("魔物的魔力" in r and r.endswith("4000") for r in rows)
    assert any("戰術的魔力" in r and r.endswith("2000") for r in rows)
    assert "攻擊方獲勝" in page.locator("#info-body .info-result").text_content()
    page.locator("#info-body .card-ref").first.click()                    # 來源卡名可點
    assert page.locator("#zoom-overlay").is_visible()
    assert page.locator("#zoom-actions button").count() == 0


def test_stage_total_opens_live_breakdown(page):
    start_local(page)
    to_effects_step(page)
    page.locator("#stage-att-total").click()
    assert page.locator("#info-title").text_content() == "目前的合計魔力明細"
    assert any(r.endswith("4000") for r in info_rows(page))
    assert page.locator("#info-body .info-result").count() == 0


# ---------------------------------------------------------------- 作用中效果

def test_effects_list_shows_standby_and_updates(page):
    start_local(page)
    assert page.locator("#effects-toggle").text_content() == "作用中效果(0)"
    cmd(page, {"type": "flip_pages", "count": 1, "player": "tp"})       # 翻開 P4=P-001、P5=S-001
    cmd(page, {"type": "play_card", "page": 4, "player": "tp"})
    cmd(page, {"type": "pass", "player": "op"})
    page.evaluate("""async () => {
        const tp = S.turn_player;
        await send({type: 'use_field_ability', zone: 'partner', slot_uid: S.players[tp].slots[0].uid, player: tp});
    }""")
    page.wait_for_function("S.effects.length === 1")
    assert page.locator("#effects-toggle").text_content() == "作用中效果(1)"
    page.locator("#effects-toggle").click()
    rows = info_rows(page)
    gash = page.evaluate("mamodoName('ガッシュ・ベル')")
    assert len(rows) == 1 and f"下一場戰鬥:以 {gash} 的戰術攻擊時,對手不能防禦" in rows[0]   # P-001 限定賈修
    assert rows[0].endswith("本回合下一場戰鬥")
    # 開啟中:回合結束後待命到期,清單同步清空
    cmd(page, {"type": "pass", "player": "op"})
    cmd(page, {"type": "pass", "player": "tp"})
    page.wait_for_function("S.effects.length === 0")
    assert info_rows(page) == []
    assert page.locator("#effects-toggle").text_content() == "作用中效果(0)"


def test_effect_without_text_falls_back_to_card_effect(page):
    start_local(page)
    text = page.evaluate("""() => {
        S = {...S, effects: [{type: 'modifier', kind: 'mystery', source: 'E-006', owner: 0,
             duration: 'turn', created_turn: S.turn_no, target_player: 0, target_slot: null, amount: 0, flag: null}]};
        renderEffectsInfo();
        return document.querySelector('#info-body .info-row').textContent;
    }""")
    assert page.evaluate("TEXT['E-006'].effect") in text
