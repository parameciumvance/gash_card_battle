"""魔力對決對峙演出的瀏覽器測試(battle-ui「魔力對決對峙演出」「魔力對決結果呈現」「魔力對決演出的時間」)。
需要 playwright 與 Chromium。以本機測試模式觸發戰鬥,演出期間記錄 DOM。

Run: python -m pytest tests/test_showdown_ui.py -q
"""
import pytest

from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture
from tests.test_spotlight_ui import open_page
from tests.test_timing_ui import send, start_as

# 演出出現時記下內容;結果出現時再記一次;移除時記下時間
RECORD = """() => {
    window.__fo = [];
    const ov = document.getElementById('anim-overlay');
    const grab = (el) => {
        const side = (k) => {
            const g = el.querySelector(`.fo-group.${k}`);
            return g && {cards: [...g.querySelectorAll('[data-card]')].map(c => c.dataset.card),
                         empty: g.querySelector('.fo-empty') ? g.querySelector('.fo-empty').textContent : null,
                         total: g.querySelector('.fo-total').textContent,
                         top: g.classList.contains('top'), win: g.classList.contains('win'),
                         lose: g.classList.contains('lose'),
                         negated: !!g.querySelector('.fo-stamp')};
        };
        const r = el.querySelector('.fo-result');
        return {attack: side('attack'), defense: side('defense'), vs: !!el.querySelector('.fo-vs'),
                result: r ? r.querySelector('.fo-result-main').textContent : '',
                sub: r && r.querySelector('.fo-result-sub') ? r.querySelector('.fo-result-sub').textContent : ''};
    };
    new MutationObserver(() => {
        const el = ov.querySelector('.fx-faceoff');
        const last = window.__fo[window.__fo.length - 1];
        if (el && (!last || last.gone)) window.__fo.push({t0: performance.now(), first: grab(el)});
        else if (el && last) last.final = grab(el);
        else if (!el && last && !last.gone) { last.gone = true; last.ms = performance.now() - last.t0; }
    }).observe(ov, {childList: true, subtree: true, attributes: true, characterData: true});
}"""


ENERGY = """() => {
    window.__energy = [];
    const ov = document.getElementById('anim-overlay');
    new MutationObserver((muts) => {
        for (const m of muts) for (const n of m.addedNodes) {
            if (n.classList && n.classList.contains('fx-energy')) window.__energy.push({target: n.dataset.target, after: [...window.__fo].length});
            if (n.classList && n.classList.contains('fx-impact')) {
                const r = n.getBoundingClientRect();
                window.__energy.push({impact: true, x: r.left + r.width / 2, y: r.top + r.height / 2});
            }
        }
    }).observe(ov, {childList: true});
}"""


@pytest.fixture
def faceoff_page(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, motion="no-preference", prefs={"spotlight": "off"})
    yield page
    context.close()
    assert not errors


def battle_to_showdown(page, defend, expect_faceoff=True):
    tp, _ = start_as(page, "all")
    dp = 1 - tp
    page.evaluate(RECORD)
    page.evaluate(ENERGY)
    send(page, tp, {"type": "flip_pages", "count": 0})
    send(page, tp, {"type": "declare_attack", "page": 3})
    page.wait_for_function("S.battle_in")
    send(page, dp, {"type": "battle_in_response", "allow": True})
    page.wait_for_function("S.battle && S.battle.step === 'defense'")
    send(page, dp, {"type": "declare_defense", "page": 3} if defend else {"type": "no_defense"})
    page.wait_for_function("S.battle && S.battle.step === 'effects'")
    send(page, tp, {"type": "pass"})
    page.wait_for_function(f"S.battle && S.battle.effect_turn === {dp}")
    send(page, dp, {"type": "pass"})
    if not expect_faceoff:
        page.wait_for_function("!S.battle || S.pending")           # 勝負已結算(之後可能等受傷方決策)
        return tp, None
    page.wait_for_function("window.__fo.length && window.__fo[0].gone", timeout=8000)
    return tp, page.evaluate("window.__fo[0]")


def test_faceoff_no_defense_attack_success(faceoff_page):
    page = faceoff_page
    tp, fo = battle_to_showdown(page, defend=False)
    first, final = fo["first"], fo["final"]
    assert first["vs"]
    assert first["attack"]["cards"] == ["M-001", "S-001"]
    assert first["attack"]["top"] == page.evaluate(f"topPlayerIndex() === {tp}")   # 上方玩家的組在上
    assert first["defense"]["top"] != first["attack"]["top"]
    assert first["defense"]["cards"] == [] and first["defense"]["empty"] == "不防禦"
    assert final["attack"]["total"] == "6000" and final["defense"]["total"] == "0"
    assert final["result"] == "攻擊成功" and final["sub"] == ""
    assert final["attack"]["win"] and final["defense"]["lose"]
    assert 2000 <= fo["ms"] <= 3500                                         # 標準約 2.5 秒


def test_faceoff_tie_defense_success(faceoff_page):
    page = faceoff_page
    _, fo = battle_to_showdown(page, defend=True)                         # 雙方 ガッシュ + S-001 = 6000
    final = fo["final"]
    assert final["defense"]["cards"] == ["M-001", "S-001"]
    assert final["attack"]["total"] == final["defense"]["total"] == "6000"
    assert final["result"] == "防禦成功" and final["sub"] == "同值・防禦方勝"
    assert final["defense"]["win"] and final["attack"]["lose"]


def test_faceoff_click_skips(faceoff_page):
    page = faceoff_page
    page.evaluate("""() => new MutationObserver((_, obs) => {
        const el = document.querySelector('#anim-overlay .fx-faceoff');
        if (el) { obs.disconnect(); setTimeout(() => el.click(), 300); }
    }).observe(document.getElementById('anim-overlay'), {childList: true, subtree: true})""")
    _, fo = battle_to_showdown(page, defend=False)
    assert fo["ms"] < 1000


def test_faceoff_fast_setting(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, motion="no-preference", prefs={"spotlight": "fast"})
    _, fo = battle_to_showdown(page, defend=False)
    assert 900 <= fo["ms"] <= 2000                                          # 快約 1.2 秒(含之後的聚焦前結束)
    context.close()
    assert not errors


def test_faceoff_skipped_when_motion_off(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, motion="reduce", prefs={"spotlight": "off"})
    battle_to_showdown(page, defend=False, expect_faceoff=False)
    assert page.evaluate("window.__fo.length") == 0
    context.close()
    assert not errors


def test_damage_energy_hits_damaged_book(faceoff_page):
    page = faceoff_page
    tp, _ = battle_to_showdown(page, defend=False)                         # 攻擊成功:防禦方魔書受到傷害
    dp = 1 - tp
    page.wait_for_function("S.pending && S.pending.kind === 'protect'")    # 先決定是否保護,傷害在下一批
    assert page.evaluate("window.__energy.length") == 0
    send(page, dp, {"type": "choose", "value": None})
    page.wait_for_function("window.__energy.some(e => e.impact)", timeout=5000)
    energy = page.evaluate("window.__energy")
    assert energy[0]["target"] == f"book-{dp}"
    impact = next(e for e in energy if e.get("impact"))
    cover = page.evaluate(f"""(() => {{
        const r = document.querySelector('.player-zone[data-player="{dp}"] .book-cover').getBoundingClientRect();
        return {{x: r.left + r.width / 2, y: r.top + r.height / 2}};
    }})()""")
    assert abs(impact["x"] - cover["x"]) < 30 and abs(impact["y"] - cover["y"]) < 30   # 命中防禦方的魔書


def test_no_energy_without_damage(faceoff_page):
    page = faceoff_page
    battle_to_showdown(page, defend=True)                                   # 同值:防禦成功,沒有傷害
    page.wait_for_function("!S.battle")
    assert page.evaluate("window.__energy.length") == 0


GUARD = """() => {
    window.__guard = [];
    const ov = document.getElementById('anim-overlay');
    new MutationObserver((muts) => {
        for (const m of muts) {
            for (const n of m.addedNodes) {
                if (n.classList && n.classList.contains('fx-guard-wrap')) window.__guard.push({add: n.dataset.guardFor});
            }
            if (m.type === 'attributes' && m.target.classList && m.target.classList.contains('fx-guard')
                && m.target.classList.contains('guarding')) {
                const r = m.target.getBoundingClientRect();
                window.__guard.push({at: true});
            }
        }
    }).observe(ov, {childList: true, attributes: true, subtree: true});
}"""


def test_protector_moves_in_front_of_book_and_takes_energy(faceoff_page):
    page = faceoff_page
    tp, _ = battle_to_showdown(page, defend=False)
    dp = 1 - tp
    page.wait_for_function("S.pending && S.pending.kind === 'protect'")
    page.evaluate(GUARD)
    protector = page.evaluate(f"S.players[{dp}].slots[0].uid")
    # 複製品移除的那一刻:它已在對象前轉成橫置,且盤面上的保護者已重繪為橫置(不會閃一下直放)
    page.evaluate(f"""() => new MutationObserver((muts, obs) => {{
        for (const m of muts) for (const n of m.removedNodes) {{
            if (n.classList && n.classList.contains('fx-guard-wrap')) {{
                const b = document.querySelector('[data-slot-uid="{protector}"][data-zone-kind="mamodo"]');
                window.__removal = {{clone: n.querySelector('.fx-guard').classList.contains('injured'),
                                     board: b ? b.classList.contains('injured') : null}};
                obs.disconnect();
            }}
        }}
    }}).observe(document.getElementById('anim-overlay'), {{childList: true}})""")
    send(page, dp, {"type": "choose", "value": protector})
    page.wait_for_function("window.__energy.some(e => e.impact)", timeout=5000)
    assert page.evaluate("window.__guard")[0] == {"add": f"book-{dp}"}       # 保護者移到魔書前
    energy = page.evaluate("window.__energy")
    impact = next(e for e in energy if e.get("impact"))
    cover = page.evaluate(f"""(() => {{
        const r = document.querySelector('.player-zone[data-player="{dp}"] .book-cover').getBoundingClientRect();
        return {{x: r.left + r.width / 2, y: r.top + r.height / 2}};
    }})()""")
    assert abs(impact["x"] - cover["x"]) < 40 and abs(impact["y"] - cover["y"]) < 60   # 能量打在魔書前的保護者
    page.wait_for_function("window.__removal", timeout=5000)
    assert page.evaluate("window.__removal") == {"clone": True, "board": True}
