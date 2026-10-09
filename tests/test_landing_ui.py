"""首頁與設定頁的瀏覽器測試(battle-ui「首頁入口」「玩家暱稱」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_landing_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(聚焦預設關閉)
from tests.test_npc_ui import room_posts
from tests.test_spotlight_ui import open_page

ENTRIES = ["entry-npc", "entry-friend", "entry-builder", "entry-local", "entry-rules", "entry-feedback"]


def visible_panel(page):
    return page.evaluate("[...document.querySelectorAll('.setup-panel')]"
                         ".filter(p => !p.classList.contains('hidden')).map(p => p.id)")


def make_deck(page, name="mine"):
    """存一副合法的自訂牌組並刷新選單,回傳其 id。"""
    return page.evaluate(f"""async () => {{
        const d = DeckStore.create('{name}', await fetchPresetPages('level2'));
        renderLanding();
        return d.id;
    }}""")


def test_landing_has_only_entries(page):
    ids = page.evaluate("[...document.querySelectorAll('#landing-cards > .entry')].map(e => e.id)")
    assert ids == ENTRIES
    for eid in ENTRIES:
        entry = page.locator(f"#{eid}")
        assert entry.evaluate("e => e.tagName") == "BUTTON"
        assert entry.locator(".entry-title").text_content()
        assert entry.locator(".entry-desc").text_content()
    assert page.locator("#landing input, #landing select").count() == 0


def test_setup_page_back_returns_to_landing(page):
    posts = room_posts(page)
    page.locator("#entry-npc").click()
    assert page.locator("#setup").is_visible() and not page.locator("#landing").is_visible()
    assert visible_panel(page) == ["setup-npc"]
    assert page.locator("#setup-title").text_content() == "NPC 對戰"
    for field in ("#name-npc", "#deck-npc", "#deck-npc-opp", "#npc-level"):
        assert page.locator(field).is_visible()
    page.locator("#setup-back").click()
    assert page.locator("#landing").is_visible() and not page.locator("#setup").is_visible()
    assert posts == []


def test_local_setup_starts_local_game(page):
    assert page.locator("#entry-local .entry-title").text_content() == "自由調查時間"
    assert page.locator("#entry-local .entry-desc").text_content().startswith("沒有電腦對手")
    page.locator("#entry-local").click()
    assert visible_panel(page) == ["setup-local"]
    assert page.locator("#setup-title").text_content() == "自由調查時間"
    page.fill("#name-local-1", "小美")
    page.select_option("#deck-local-1", "preset:level2")
    page.locator("#local-start").click()
    page.wait_for_function("SESSION && SESSION.mode === 'local' && S")
    assert page.locator("#layout").is_visible()
    assert page.evaluate("pname(1)") == "小美"


def test_friend_toggle_keeps_values(page):
    page.locator("#entry-friend").click()
    assert visible_panel(page) == ["setup-friend"]
    assert "active" in page.locator('#friend-mode [data-mode="create"]').get_attribute("class")
    assert page.locator("#timer-select").is_visible() and not page.locator("#join-code").is_visible()
    assert page.locator("#friend-submit").text_content() == "建立房間"
    page.fill("#name-friend", "阿賢")
    page.select_option("#deck-friend", "preset:level2")
    page.locator('#friend-mode [data-mode="join"]').click()
    assert page.locator("#join-code").is_visible() and not page.locator("#timer-select").is_visible()
    assert page.locator("#friend-submit").text_content() == "加入房間"
    assert page.locator("#name-friend").input_value() == "阿賢"
    assert page.locator("#deck-friend").input_value() == "preset:level2"


def test_create_room_from_friend_setup(page):
    posts = room_posts(page)
    deck = make_deck(page)
    page.locator("#entry-friend").click()
    page.select_option("#deck-friend", deck)
    page.select_option("#timer-select", "60")
    page.locator("#friend-submit").click()
    page.wait_for_function("!document.getElementById('waiting').classList.contains('hidden')")
    assert posts[-1]["mode"] == "online" and posts[-1]["timer_seconds"] == 60
    assert posts[-1]["deck"] == {"pages": page.evaluate(f"DeckStore.get('{deck}').pages")}
    assert page.locator("#waiting-code").text_content()


def test_join_link_prefills_then_joins(browser, server):  # noqa: F811
    host_ctx, host, host_errors = open_page(browser, server, prefs={"spotlight": "off"})
    host.locator("#entry-friend").click()
    host.locator("#friend-submit").click()
    host.wait_for_function("document.getElementById('waiting-code').textContent")
    code = host.locator("#waiting-code").text_content()

    guest_ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale="zh-TW")
    guest_ctx.add_init_script("localStorage.setItem('gash-spotlight', 'off')")
    guest = guest_ctx.new_page()
    guest_errors = []
    guest.on("pageerror", lambda error: guest_errors.append(str(error)))
    guest.goto(f"{server}/?join={code.lower()}")
    guest.wait_for_function("Object.keys(CARDS).length > 0 && !document.getElementById('setup').classList.contains('hidden')")
    assert visible_panel(guest) == ["setup-friend"]
    assert "active" in guest.locator('#friend-mode [data-mode="join"]').get_attribute("class")
    assert guest.locator("#join-code").input_value() == code
    assert guest.evaluate("SESSION") is None                               # 尚未加入
    assert guest.evaluate("JSON.parse(localStorage.getItem('gash-setup') || '{}').friend") is None   # 不覆蓋記住的模式

    guest.select_option("#deck-friend", "preset:level2")
    guest.locator("#friend-submit").click()
    guest.wait_for_function("SESSION && SESSION.mode === 'online' && S", timeout=15000)
    host.wait_for_function("S && !document.getElementById('layout').classList.contains('hidden')", timeout=15000)
    assert guest.locator("#layout").is_visible()
    host_ctx.close()
    guest_ctx.close()
    assert not host_errors and not guest_errors


def test_join_failure_stays_on_setup(page):
    page.locator("#entry-friend").click()
    page.locator('#friend-mode [data-mode="join"]').click()
    page.fill("#name-friend", "阿賢")
    page.fill("#join-code", "ZZZZZZ")
    page.locator("#friend-submit").click()
    page.wait_for_function("!document.getElementById('toast').classList.contains('hidden') && document.getElementById('toast').textContent")
    assert visible_panel(page) == ["setup-friend"] and page.locator("#setup").is_visible()
    assert page.evaluate("SESSION") is None
    assert page.locator("#join-code").input_value() == "ZZZZZZ"
    assert page.locator("#name-friend").input_value() == "阿賢"


def test_back_from_join_link_resets_url(page, server):  # noqa: F811
    page.goto(f"{server}/?join=ABC123")
    page.wait_for_function("Object.keys(CARDS).length > 0 && !document.getElementById('setup').classList.contains('hidden')")
    page.locator("#setup-back").click()
    assert page.evaluate("location.search") == ""
    page.locator("#entry-friend").click()
    assert "active" in page.locator('#friend-mode [data-mode="create"]').get_attribute("class")


def test_choices_remembered_after_reload_and_builder(page):
    deck = make_deck(page)
    page.locator("#entry-npc").click()
    page.select_option("#deck-npc", deck)
    page.select_option("#deck-npc-opp", "preset:level2")
    page.select_option("#npc-level", "dummy")
    page.locator("#setup-back").click()
    page.locator("#entry-friend").click()
    page.select_option("#timer-select", "60")
    page.locator('#friend-mode [data-mode="join"]').click()
    page.fill("#join-code", "ABC123")

    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    page.locator("#entry-npc").click()
    assert page.locator("#deck-npc").input_value() == deck
    assert page.locator("#deck-npc-opp").input_value() == "preset:level2"
    assert page.locator("#npc-level").input_value() == "dummy"
    page.locator("#setup-back").click()
    page.locator("#entry-friend").click()
    assert "active" in page.locator('#friend-mode [data-mode="join"]').get_attribute("class")
    assert page.locator("#timer-select").input_value() == "60"
    assert page.locator("#join-code").input_value() == ""                 # 房號不記住

    page.locator("#setup-back").click()
    page.locator("#entry-builder").click()
    page.locator("#builder-back").click()
    page.locator("#entry-npc").click()
    assert page.locator("#deck-npc").input_value() == deck                # 從構築器返回不重設
    assert page.locator("#npc-level").input_value() == "dummy"


def test_forgotten_or_invalid_deck_falls_back_to_default(page):
    gone, broken = make_deck(page, "gone"), make_deck(page, "broken")
    page.locator("#entry-npc").click()
    page.select_option("#deck-npc", gone)
    page.locator("#setup-back").click()
    page.locator("#entry-local").click()
    page.select_option("#deck-local-0", broken)
    page.evaluate(f"""() => {{
        DeckStore.remove('{gone}');
        DeckStore.save({{...DeckStore.get('{broken}'), pages: Array(32).fill('M-001')}});   // 變得不合法
    }}""")
    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    page.locator("#entry-npc").click()
    assert page.locator("#deck-npc").input_value() == "preset:level1"
    page.locator("#setup-back").click()
    page.locator("#entry-local").click()
    assert page.locator("#deck-local-0").input_value() == "preset:level1"


def test_corrupted_saved_choices_use_defaults(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, prefs={"setup": "{broken"})
    page.locator("#entry-npc").click()
    assert page.locator("#deck-npc-opp").input_value() == "npc:random"
    assert page.locator("#npc-level").input_value() == "normal"
    page.select_option("#npc-level", "dummy")                              # 照常可存
    assert page.evaluate("JSON.parse(localStorage.getItem('gash-setup')).npc.level") == "dummy"
    context.close()
    assert not errors


def test_nickname_prefilled_except_local(page):
    page.evaluate("localStorage.setItem('gash-nick', '阿賢')")
    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    page.locator("#entry-npc").click()
    assert page.locator("#name-npc").input_value() == "阿賢"
    page.locator("#setup-back").click()
    page.locator("#entry-friend").click()
    assert page.locator("#name-friend").input_value() == "阿賢"
    page.locator("#setup-back").click()
    page.locator("#entry-local").click()
    assert page.locator("#name-local-0").input_value() == ""
    assert page.locator("#name-local-1").input_value() == ""


def test_disclaimer_on_landing_only(page):
    disclaimer = page.locator("#landing-disclaimer")
    assert disclaimer.is_visible()
    assert disclaimer.evaluate("e => e.tagName") != "BUTTON"
    text = disclaimer.text_content()
    assert "非官方粉絲專案,與原作者及 BANDAI 無關,亦未經授權;免費且不涉商業行為。" in text
    assert "作品與卡片相關權利屬於雷句誠、BANDAI 及各權利人;權利人如有疑慮,請透過「意見回報」聯絡。" in text
    assert page.locator("#landing-disclaimer a, #landing-disclaimer button").count() == 0   # 意見回報不做成連結
    box, cards = disclaimer.bounding_box(), page.locator("#landing-cards").bounding_box()
    assert box["y"] >= cards["y"] + cards["height"]                       # 在入口下方,不遮住入口
    page.locator("#entry-npc").click()
    assert not disclaimer.is_visible()


def test_invite_links_use_page_origin(browser, server):  # noqa: F811
    """battle-ui「公開邀請連結」:一律以 location.origin 組連結,伺服器回傳的其他網址不採用。"""
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale="zh-TW")
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")

    def meta_with_tunnel(route):
        res = route.fetch()
        route.fulfill(response=res, json={**res.json(), "tunnel_url": "https://stale.trycloudflare.com"})

    context.route("**/api/meta", meta_with_tunnel)
    page = context.new_page()
    try:
        page.goto(server)
        page.wait_for_function("Object.keys(CARDS).length > 0")
        page.locator("#entry-friend").click()
        page.locator("#friend-submit").click()
        page.wait_for_function("document.getElementById('waiting-code').textContent")
        code = page.locator("#waiting-code").text_content()
        assert page.input_value("#share-join") == f"{server}/?join={code}"
        assert page.input_value("#share-spec").startswith(f"{server}/")
    finally:
        context.close()
