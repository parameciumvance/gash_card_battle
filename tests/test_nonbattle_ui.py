"""Nonbattle actions and card detail browser regressions (optional Playwright)."""
import pytest
from tests.test_cheat_editor import browser, page, server, pw  # shared isolated browser/server fixtures


def setup_spell(page, number="S-026", mamodo="M-001"):
    page.evaluate("startLocal()")
    page.evaluate("""({number, mamodo}) => {
      const p = S.turn_player;
      S.phase = 'battle'; S.action_player = p; S.battle = null; S.battle_in = null; S.pending = null;
      S.players[p].slots[0].top = mamodo;
      S.players[p].open_pages = [{page:2,card:number,cost:CARDS[number].cost || 0}];
      S.players[p].mp = 20;
      render();
      zoom(number,{kind:'page',p,page:2});
    }""", {"number": number, "mamodo": mamodo})


@pytest.mark.parametrize("number,mamodo", [
    ("S-026", "M-001"), ("S-041", "M-023"), ("S-043", "M-024"),
    ("S-048", "M-028"), ("S-057", "M-001"),
])
def test_nonbattle_use_payload(page, number, mamodo):
    setup_spell(page, number, mamodo)
    buttons = page.locator("#zoom-actions button")
    assert buttons.all_text_contents() == ["使用"]
    assert buttons.first.is_enabled()
    assert page.locator("#zoom-card .cnum").inner_text() == number
    state = page.evaluate("S")
    page.route("**/commands", lambda route: route.fulfill(json={"state": state}))
    with page.expect_request(lambda r: r.url.endswith('/commands')) as sent:
        buttons.first.click()
    assert sent.value.post_data_json["command"] == {"type":"use_book_card", "player":state["turn_player"], "page":2}
    assert not page.locator("#zoom-overlay").is_visible()


def test_s026_real_effect_and_reload(page):
    page.evaluate("startLocal()")
    p = page.evaluate("S.turn_player")
    page.evaluate("""async () => {
      const base = `/api/rooms/${SESSION.code}`;
      const headers = {'X-Player-Token':Object.values(SESSION.tokens)[0], 'Content-Type':'application/json'};
      const data = await api(`${base}/debug-state`,{headers});
      data.players[S.turn_player].book[1] = 'S-026';
      data.players[S.turn_player].book[2] = 'S-026';
      await api(`${base}/debug-state`,{method:'POST',headers,body:JSON.stringify(data)});
      await send({type:'flip_pages',player:S.turn_player,count:0});
      zoom('S-026',{kind:'page',p:S.turn_player,page:2});
    }""")
    page.locator("#zoom-actions button").click()
    page.wait_for_function("S.players[S.turn_player].used_nonbattle_spells.includes('S-026')")
    assert page.evaluate("!S.battle && !S.battle_in")
    events = page.evaluate("api(`/api/rooms/${SESSION.code}/events?since=0`, {headers:{'X-Player-Token':Object.values(SESSION.tokens)[0]}})")["events"]
    assert any(e["type"] == "book_card_used" and e["card"] == "S-026" for e in events)
    assert any(e["type"] == "coin_flipped" and e.get("source") == "S-026" for e in events)
    page.reload()
    page.wait_for_function("S && S.players[S.turn_player].used_nonbattle_spells.includes('S-026')")
    page.evaluate("p => send({type:'pass',player:1-p})", p)
    page.evaluate("p => zoom('S-026',{kind:'page',p,page:3})", p)
    assert page.locator("#zoom-actions button").is_disabled()
    assert page.locator("#zoom-actions .zoom-reason").inner_text()


def test_reasons_and_latest_snapshot(page):
    setup_spell(page, "S-041", "M-023")
    def update(code):
        page.evaluate("{const p=S.turn_player; " + code + "; renderZoom();}")
    update("S.players[p].mp=0")
    assert "MP 不足" in page.locator(".zoom-reason").inner_text()
    update("S.players[p].mp=20; S.players[p].slots=[]")
    assert "魔物" in page.locator(".zoom-reason").inner_text()
    update("S.players[p].used_nonbattle_spells=['S-041']")
    assert page.locator(".zoom-reason").inner_text() == page.evaluate("t('ui.used')")
    update("S.players[p].used_nonbattle_spells=[]; S.players[p].slots=[{top:'M-023'}]")
    assert page.locator("#zoom-actions button").is_enabled()
    page.evaluate("S.turn_player=1-S.turn_player; renderZoom()")
    assert "自己的回合" in page.locator(".zoom-reason").inner_text()
    page.evaluate("CARDS['S-041'].ad='D'; renderZoom()")
    assert page.locator("#zoom-actions button").is_enabled()
    page.evaluate("S.turn_player=1-S.turn_player; renderZoom()")
    assert "對手的回合" in page.locator(".zoom-reason").inner_text()
    page.evaluate("CARDS['S-041'].ad='AD'; renderZoom()")
    assert page.locator("#zoom-actions button").is_enabled()
    page.evaluate("delete S.players[S.turn_player].used_nonbattle_spells; renderZoom()")
    assert page.locator("#zoom-actions button").is_enabled()


@pytest.mark.parametrize('window', ['battle', 'battle_in', 'pending', 'no_control', 'no_priority'])
def test_nonbattle_no_actions_outside_window(page, window):
    setup_spell(page)
    page.evaluate("""window => {
      const p=S.turn_player;
      if(window==='battle') S.battle={step:'defense',attacker:1-p};
      if(window==='battle_in') S.battle_in={attacker:1-p};
      if(window==='pending') S.pending={};
      if(window==='no_control') SESSION.viewer='spectator';
      if(window==='no_priority') S.action_player=1-p;
      CARDS['S-026'].ad='AD'; renderZoom();
    }""", window)
    assert page.locator('#zoom-actions button').count() == 0


def test_battle_command_spells_and_events(page):
    setup_spell(page, 'S-001')
    assert page.locator('#zoom-actions button').inner_text() == page.evaluate("t('ui.attack')")
    assert page.locator('#zoom-actions button').is_enabled()
    page.evaluate("""() => {
      const p=S.turn_player;
      const c=Object.values(CARDS).find(c=>isCommandSpell(c)&&c.effect_icon!=='nonbattle'&&c.ad==='D');
      S.players[p].open_pages=[{page:2,card:c.number,cost:0}];
      S.players[p].slots.push({...S.players[p].slots[0],uid:999});
      S.battle={step:'defense',attacker:1-p};
      zoom(c.number,{kind:'page',p,page:2});
    }""")
    assert page.locator('#zoom-actions button').is_enabled()
    page.locator('#zoom-actions button').click()
    assert page.locator('#dialog-options .card').count() == 2
    page.evaluate("""() => {
      document.querySelector('#dialog-overlay').classList.add('hidden');
      const p=S.turn_player;
      S.battle={step:'defense',attacker:1-p};
      zoom(S.players[p].open_pages[0].card,{kind:'page',p,page:2});
    }""")
    assert page.locator('#zoom-actions button').inner_text() == page.evaluate("t('ui.defend')")
    assert page.locator('#zoom-actions button').is_enabled()
    page.evaluate("""() => {
      const p=S.turn_player; S.battle=null;
      S.players[p].open_pages=[{page:2,card:'E-001'}];
      zoom('E-001',{kind:'page',p,page:2});
    }""")
    assert page.locator('#zoom-actions button').inner_text() == '使用'
    assert page.locator('#zoom-actions button').is_enabled()
    page.evaluate("S.players[S.turn_player].used_event_this_turn=true; renderZoom()")
    assert page.locator('#zoom-actions button').is_disabled()


def test_number_layout_and_pure_detail(page):
    page.route('**/static/assets/cards/S-026.jpg',lambda route:route.abort())
    page.evaluate("zoom('S-026')")
    pw.expect(page.locator('#zoom-card img')).to_have_attribute('src','/static/back.jpg')
    assert page.locator('#zoom-actions button').count() == 0
    for width in [1280,390,320]:
        page.set_viewport_size({'width':width,'height':844})
        num=page.locator('#zoom-card .cnum')
        assert num.inner_text()=='S-026'
        assert num.evaluate("e=>parseFloat(getComputedStyle(e).fontSize)")>=14
        box=num.bounding_box(); effect=page.locator('#zoom-card .ceffect').bounding_box()
        assert box['y'] >= effect['y']+effect['height']
        assert num.evaluate("e=>getComputedStyle(e).fontWeight") == '400'
        assert num.evaluate("e=>e === e.parentElement.lastElementChild")
        assert box['x']>=0 and box['x']+box['width']<=width
    page.evaluate("zoom('S-001')")
    assert page.locator('#zoom-card .cnum').inner_text()=='S-001'
