"""賽季的瀏覽器測試(battle-ui「設定頁的賽季選單」「牌組選單依賽季」「魔書不符房間賽季的錯誤訊息」)。
需要 playwright 與 Chromium。"""
import json
from urllib.request import Request, urlopen


def api(server, path, body):
    req = Request(server + path, data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req) as res:
        return json.loads(res.read())


def open_setup(page, mode):
    page.locator(f"#entry-{mode}").click()
    page.wait_for_selector(f"#setup-{mode}:not(.hidden)")


def option(page, select, value):
    return page.locator(f'{select} option[value="{value}"]')


def test_season_limits_npc_deck_menus(page):
    open_setup(page, "npc")
    assert page.locator("#season-npc").input_value() == "3"                     # 缺省第 3 賽季
    assert not option(page, "#deck-npc", "preset:zeon").is_disabled()
    page.select_option("#season-npc", "1")
    for sel in ("#deck-npc", "#deck-npc-opp"):
        assert not option(page, sel, "preset:level1").is_disabled()
        for preset, season in (("level2", 2), ("gash-nakama", 3), ("zeon", 3)):
            opt = option(page, sel, f"preset:{preset}")
            assert opt.is_disabled()
            assert opt.inner_text().endswith(f"(第 {season} 賽季起)")
    assert option(page, "#deck-npc", "preset:level1").inner_text().find("賽季") == -1


def test_switching_season_resets_unusable_deck(page):
    open_setup(page, "npc")
    page.select_option("#deck-npc", "preset:zeon")
    page.select_option("#season-npc", "1")
    assert page.locator("#deck-npc").input_value() == "preset:level1"


def test_random_npc_candidates_follow_season(page):
    page.evaluate("""async () => {
        DeckStore.create('mine', await fetchPresetPages('level1'));
        DeckStore.create('late', await fetchPresetPages('zeon'));
        renderLanding();
    }""")
    open_setup(page, "npc")
    page.select_option("#season-npc", "2")
    assert page.locator("#deck-npc-opp").input_value() == "npc:random"
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/api/rooms")) as req:
        page.click("#npc-start")
    body = req.value.post_data_json
    mine = page.evaluate("DeckStore.list().find(d => d.name === 'mine').pages")
    assert body["season"] == 2
    assert body["npc_decks"] == [{"preset": "level1"}, {"preset": "level2"}, {"pages": mine}]
    page.wait_for_function("SESSION && SESSION.mode === 'npc' && R && R.season === 2")


def test_season_is_remembered(page):
    open_setup(page, "local")
    page.select_option("#season-local", "2")
    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    open_setup(page, "local")
    assert page.locator("#season-local").input_value() == "2"
    assert page.locator("#season-npc").input_value() == "3"                     # 各模式分開記


def test_create_friend_room_sends_season_and_join_mode_hides_it(page):
    open_setup(page, "friend")
    assert page.locator("#season-friend").is_visible()
    page.select_option("#season-friend", "1")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/api/rooms")) as req:
        page.click("#friend-submit")
    assert req.value.post_data_json["season"] == 1
    page.wait_for_selector("#waiting:not(.hidden)")
    assert page.evaluate("R.season") == 1


def test_join_mode_has_no_season_and_shows_room_season_on_reject(page, server):
    room = api(server, "/api/rooms", {"mode": "online", "season": 1})
    open_setup(page, "friend")
    page.click('#friend-mode button[data-mode="join"]')
    assert page.locator("#season-friend").is_hidden()
    assert not option(page, "#deck-friend", "preset:zeon").is_disabled()       # 加入模式不依賽季禁用
    assert option(page, "#deck-friend", "preset:zeon").inner_text().endswith("(第 3 賽季起)")
    page.select_option("#deck-friend", "preset:zeon")
    page.fill("#join-code", room["code"])
    page.click("#friend-submit")
    page.wait_for_selector("#toast:not(.hidden)")
    assert "此房間為第 1 賽季" in page.locator("#toast").inner_text()
    assert page.locator("#setup-friend").is_visible()
    assert page.locator("#join-code").input_value() == room["code"]
