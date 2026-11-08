"""頂欄的換行(battle-ui「頂欄的換行」):中等寬度塞不下時整個項目換行,文字欄位不被壓成直排,
按鈕都在畫面內。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_topbar_wrap_ui.py -q
"""
import pytest


def battle_page(browser, server, width, lang):
    """自由調查時間進入戰鬥階段,第 5 回合、非回合玩家決策中(回合、階段與等待狀態已移到中線與行動欄,頂欄只剩標題與按鈕)。"""
    context = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce", locale=lang)
    context.add_init_script(f"localStorage.setItem('gash-lang', '{lang}'); localStorage.setItem('gash-spotlight', 'off')")
    page = context.new_page()
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    page.evaluate("Anim.idle()")
    page.evaluate("send({type: 'flip_pages', player: S.turn_player, count: 0})")
    page.wait_for_function("S.phase === 'battle'")
    page.evaluate("Anim.idle()")
    page.evaluate("""() => {
        S = {...S, turn_no: 5, pending: {kind: 'protect', player: 1 - S.turn_player, source: null, info: {}, options: []}};
        render();
    }""")
    page.wait_for_function("document.querySelector('#stage-head .stage-name').textContent")
    return context, page


def line_counts(page):
    """頂欄每個看得到的文字欄位與標題字佔幾行(文字行框的不同頂端數)。"""
    return page.evaluate("""() => [...document.querySelectorAll('#topbar > span')]
        .filter((el) => el.offsetParent && el.textContent.trim())
        .map((el) => {
            const range = document.createRange();
            range.selectNodeContents(el);
            // 垂直範圍重疊的行框算同一行(標題字大小不同、同一基線,中心高度不同)
            const rects = [...range.getClientRects()].filter((r) => r.width && r.height)
                .sort((a, b) => a.top - b.top);
            let lines = 0, bottom = -Infinity;
            for (const r of rects) {
                if (r.top >= bottom - 1) { lines += 1; bottom = r.bottom; } else bottom = Math.max(bottom, r.bottom);
            }
            return [el.id, lines];
        })""")


def buttons_outside(page):
    return page.evaluate("""() => [...document.querySelectorAll('#topbar > button')]
        .filter((b) => b.offsetParent)
        .filter((b) => { const r = b.getBoundingClientRect(); return r.left < 0 || r.right > innerWidth + 0.5; })
        .map((b) => b.id)""")


@pytest.mark.parametrize("width", [800, 1000])
@pytest.mark.parametrize("lang", ["ja", "zh-TW", "en"])
def test_medium_width_wraps_whole_items(browser, server, width, lang):  # noqa: F811
    context, page = battle_page(browser, server, width, lang)
    counts = line_counts(page)
    assert counts and all(n == 1 for _, n in counts), counts               # 沒有欄位被壓成多行(直排)
    assert ["title", 1] in counts                                          # 標題字在同一行
    assert buttons_outside(page) == []                                     # 按鈕都在畫面內
    context.close()


def test_wide_screen_stays_one_row(browser, server):  # noqa: F811
    context, page = battle_page(browser, server, 1540, "ja")
    tops = page.evaluate("""() => new Set([...document.querySelectorAll('#topbar > *')]
        .filter((el) => el.offsetParent)
        .map((el) => { const r = el.getBoundingClientRect(); return Math.round(r.top + r.height / 2); })).size""")
    assert tops == 1
    context.close()


def test_phone_unchanged(browser, server):  # noqa: F811
    context, page = battle_page(browser, server, 390, "ja")
    assert page.locator("#topbar #title .wm-text").is_hidden()            # 手機只留徽章
    assert buttons_outside(page) == []
    context.close()
