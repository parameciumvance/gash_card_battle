"""戰術的預估合計魔力(battle-ui「戰術的預估合計魔力」)。需要 playwright 與 Chromium。

level1 預組開局:場上ガッシュ・ベル(魔力 4000),翻開第 3 頁 S-001(ガッシュ・ベル的攻防戰術,魔力 +2000)。

Run: python -m pytest tests/test_spell_power_preview_ui.py -q
"""
from tests.test_timing_ui import send, start_as


def to_battle(page, me):
    tp, mine = start_as(page, me)
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    return tp, mine


def zoom_page(page, p, page_no):
    page.evaluate("([p, n]) => zoom(S.players[p].book[n - 1], {kind: 'page', p, page: n})", [p, page_no])


def sections(page):
    return page.evaluate("""() => [...document.querySelectorAll('#zoom-overlay .zoom-details .info-section')].map(sec => ({
        title: sec.querySelector('h4').textContent,
        rows: [...sec.querySelectorAll('.info-row')].map(r => r.textContent)}))""")


def details_text(page):
    return page.locator("#zoom-overlay .zoom-details").text_content()


def test_zoom_shows_preview_for_attack_spell(page):
    tp, me = to_battle(page, "turn")
    zoom_page(page, me, 3)
    [sec] = [s for s in sections(page) if s["title"].startswith("預估合計魔力")]
    assert sec["title"] == "預估合計魔力 6000"
    assert len(sec["rows"]) == 2 and "4000" in sec["rows"][0] and "2000" in sec["rows"][1]
    assert "不含擲硬幣與戰鬥中的效果" in details_text(page)


def test_one_section_per_user(page):
    tp, me = to_battle(page, "turn")
    page.evaluate(f"""() => {{
        const ps = S.players[{me}];
        const extra = {{...ps.slots[0], uid: 99, top: 'M-014'}};
        ps.slots.push(extra);
        const e = ps.open_pages.find(x => x.page === 3);
        e.users = [...e.users, {{...e.users[0], slot_uid: 99, power: 7000,
            power_breakdown: [{{kind: 'mamodo', source: 'M-014', amount: 5000}}, {{kind: 'spell', source: 'S-001', amount: 2000}}]}}];
        render();
    }}""")
    zoom_page(page, me, 3)
    titles = [s["title"] for s in sections(page)]
    assert page.evaluate("`《${cname('M-001')}》的預估合計魔力 6000`") in titles
    assert page.evaluate("`《${cname('M-014')}》的預估合計魔力 7000`") in titles


def test_pick_user_note_has_total_and_cost(page):
    tp, me = to_battle(page, "turn")
    note = page.evaluate(f"""() => {{
        const e = S.players[{me}].open_pages.find(x => x.page === 3);
        let opts = null;
        const orig = startLocalPick;
        startLocalPick = (pick) => {{ opts = [...pick.options.values()]; }};
        const two = {{...e, users: [e.users[0], {{...e.users[0], slot_uid: 99}}]}};
        pickSpellUser({me}, two, () => {{}});
        startLocalPick = orig;
        return opts.map(o => o.note);
    }}""")
    assert note == ["合計 6000・費用 1", "合計 6000・費用 1"]


def test_opponent_and_spectator_see_no_preview(page):
    tp, me = to_battle(page, "turn")
    page.evaluate(f"SESSION = {{...SESSION, viewer: {1 - me}}}; render();")
    zoom_page(page, me, 3)
    assert "預估合計魔力" not in (page.locator("#zoom-overlay").text_content() or "")
    page.evaluate("SESSION = {...SESSION, viewer: 'spectator'}; render();")
    zoom_page(page, me, 3)
    assert "預估合計魔力" not in (page.locator("#zoom-overlay").text_content() or "")
