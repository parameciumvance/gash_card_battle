"""魔物位置固定的瀏覽器測試(battle-ui「魔物位置固定」)。

Run: python -m pytest tests/test_mamodo_columns_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture
from tests.test_timing_ui import send, start_as, zone_of


def cells(page, p):
    return page.evaluate(f"""() => [...document.querySelectorAll('{zone_of(page, p)} .mamodo-row .mamodo-cell')]
        .map(c => {{ const m = c.querySelector('[data-zone-kind="mamodo"]'); return m ? Number(m.dataset.slotUid) : null; }})""")


def test_left_mamodo_leaves_middle_stays(page):
    tp, _ = start_as(page, "all")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    # 以快照模擬:左邊(第 0 欄)空出,另一隻在第 1 欄(第 0 欄的魔物送墓後的狀態)
    uid = page.evaluate(f"""() => {{
        const ps = S.players[{tp}];
        const s = ps.slots[0];
        S = {{...S, players: S.players.map((x, i) => i === {tp} ? {{...x, slots: [{{...s, column: 1}}]}} : x)}};
        render();
        return s.uid;
    }}""")
    assert cells(page, tp) == [None, uid, None]
