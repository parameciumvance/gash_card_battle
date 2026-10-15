"""牌組編輯器的卡片資訊瀏覽器測試(deck-builder「對頁編輯」、battle-ui「卡圖與文字卡面」):
對應魔物「無」與選事件時暫停、卡號標籤、中級 / 上級標籤、詳情按鈕。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_builder_card_info_ui.py -q
"""
import pytest

from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

DESKTOP = {"width": 1280, "height": 900}
PHONE = {"width": 390, "height": 844}


@pytest.fixture
def builder(browser, server):  # noqa: F811
    context = browser.new_context(viewport=DESKTOP, reduced_motion="reduce", locale="zh-TW")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server + "/?builder=1")
    page.wait_for_function("Object.keys(CARDS).length > 0 && document.querySelector('#pool-grid .card')")
    yield page
    context.close()
    assert not errors


def selects(page):
    sel = page.locator("#pool-filters select")
    return sel.nth(0), sel.nth(1), sel.nth(2)          # 類型、對應魔物、產品


def pool_numbers(page):
    return page.locator("#pool-grid .card .cnum").all_text_contents()


def cards_where(page, expr):
    """卡池中(已開放)符合條件的卡號。"""
    return page.evaluate(f"openCards().filter((c) => {expr}).map((c) => c.number).sort()")


def put(page, pages):
    """直接在魔書放卡:{頁碼: 卡號}。"""
    page.evaluate("""(pages) => {
      for (const [p, c] of Object.entries(pages)) B.deck.pages[p - 1] = c;
      builderMutated();
    }""", {str(k): v for k, v in pages.items()})


# ---------------------------------------------------------------- 篩選

def test_mamodo_filter_none_shows_command_spells(builder):
    _, mamodo, _ = selects(builder)
    mamodo.select_option("__none__")
    expected = cards_where(builder, "c.type === 'spell' && c.related_mamodo === 'コマンド'")
    assert expected and sorted(pool_numbers(builder)) == expected


def test_event_type_suspends_mamodo_filter(builder):
    ftype, mamodo, _ = selects(builder)
    name = builder.evaluate("CARDS['M-001'].related_mamodo")
    mamodo.select_option(name)
    ftype.select_option("event")
    ftype, mamodo, _ = selects(builder)
    assert mamodo.is_disabled()
    assert mamodo.input_value() == name                  # 保留原本的選擇
    assert sorted(pool_numbers(builder)) == cards_where(builder, "c.type === 'event'")
    ftype.select_option("")
    ftype, mamodo, _ = selects(builder)
    assert not mamodo.is_disabled() and mamodo.input_value() == name
    assert sorted(pool_numbers(builder)) == cards_where(builder, f"c.related_mamodo === '{name}'")


def test_mamodo_filter_none_combines_with_product(builder):
    _, mamodo, product = selects(builder)
    tag = builder.evaluate("""Object.values(CARDS).find((c) => c.type === 'spell'
      && c.related_mamodo === 'コマンド' && (c.sets || []).length).sets[0]""")
    mamodo.select_option("__none__")
    product.select_option(tag)
    expected = cards_where(builder, f"c.type === 'spell' && c.related_mamodo === 'コマンド' && (c.sets || []).includes('{tag}')")
    assert expected and sorted(pool_numbers(builder)) == expected


def test_event_type_ignores_mamodo_none(builder):
    ftype, mamodo, _ = selects(builder)
    mamodo.select_option("__none__")
    ftype.select_option("event")
    assert sorted(pool_numbers(builder)) == cards_where(builder, "c.type === 'event'")


# ---------------------------------------------------------------- 卡號與中級 / 上級

def test_class_labels_and_card_number(builder):
    mid = cards_where(builder, "c.class === 'intermediate'")[0]
    put(builder, {5: "S-005", 6: mid, 7: "S-001"})
    for scope in ("#pool-grid", "#book-grid"):
        def card(num):
            return builder.locator(f"{scope} .card", has=builder.locator(".cnum", has_text=num)).first
        assert card("S-005").locator(".cclass").text_content() == "上級"
        assert card(mid).locator(".cclass").text_content() == "中級"
        assert card("S-001").locator(".cclass").count() == 0
        num = card("S-005").locator(".cnum")
        assert num.is_visible()
        bg = num.evaluate("(el) => getComputedStyle(el).backgroundColor")
        assert bg not in ("rgba(0, 0, 0, 0)", "transparent")     # 有底色,不直接壓在卡圖上
        assert num.evaluate("(el) => parseFloat(getComputedStyle(el).fontSize)") >= 10


def test_zoom_shows_class_label(builder):
    builder.evaluate("zoom('S-005')")
    assert builder.locator("#zoom-card .cclass").text_content() == "上級"


# ---------------------------------------------------------------- 詳情

def test_pool_detail_opens_zoom_without_placing(builder):
    before = builder.evaluate("[...B.deck.pages]")
    card = builder.locator("#pool-grid .card", has=builder.locator(".cnum", has_text="S-005")).first
    card.locator(".card-detail").click()
    builder.wait_for_function("!document.getElementById('zoom-overlay').classList.contains('hidden')")
    assert builder.locator("#zoom-card .cnum").text_content() == "S-005"
    assert builder.locator("#zoom-actions button").count() == 0
    assert builder.evaluate("[...B.deck.pages]") == before


def test_book_detail_opens_zoom_without_selecting(builder):
    put(builder, {5: "S-005"})
    slot = builder.locator('#book-grid .page-slot[data-page="4"]')
    slot.locator(".card-detail").click()
    builder.wait_for_function("!document.getElementById('zoom-overlay').classList.contains('hidden')")
    assert builder.locator("#zoom-card .cnum").text_content() == "S-005"
    assert builder.locator("#zoom-actions button").count() == 0
    assert builder.evaluate("B.selected") is None
    assert builder.evaluate("B.deck.pages[4]") == "S-005"


def test_detail_button_keyboard(builder):
    builder.locator("#pool-grid .card .card-detail").first.focus()
    builder.keyboard.press("Enter")
    builder.wait_for_function("!document.getElementById('zoom-overlay').classList.contains('hidden')")
    assert builder.evaluate("B.deck.pages.every((c) => c === null)")


def test_phone_layout_keeps_labels_apart(browser, server):  # noqa: F811
    context = browser.new_context(viewport=PHONE, reduced_motion="reduce", locale="zh-TW")
    page = context.new_page()
    page.goto(server + "/?builder=1")
    page.wait_for_function("Object.keys(CARDS).length > 0 && document.querySelector('#pool-grid .card')")
    put(page, {1: "M-001", 5: "S-005"})

    def overlap(a, b):
        return not (a["x"] + a["width"] <= b["x"] or b["x"] + b["width"] <= a["x"]
                    or a["y"] + a["height"] <= b["y"] or b["y"] + b["height"] <= a["y"])

    for index in (0, 4):                                  # P1(首頁說明較長)與一般頁
        slot = page.locator(f'#book-grid .page-slot[data-page="{index}"]')
        pno, num, detail = (slot.locator(sel).first.bounding_box() for sel in (".pno", ".cnum", ".card-detail"))
        card = slot.locator(".card").bounding_box()
        assert not overlap(pno, num) and not overlap(num, detail) and not overlap(pno, detail)
        assert num["x"] + num["width"] > card["x"] + card["width"] - 10      # 卡號在右上
        assert num["y"] < card["y"] + 10
    # 空的首頁仍顯示完整說明
    page.evaluate("B.deck.pages[0] = null; builderMutated()")
    assert "首頁" in page.locator('#book-grid .page-slot[data-page="0"] .pno').text_content()
    context.close()


# ---------------------------------------------------------------- 移除改用按鈕(deck-builder「對頁編輯」)

def test_double_click_does_not_remove(builder):
    put(builder, {3: "S-001"})
    slot = builder.locator('#book-grid .page-slot[data-page="2"]')
    slot.click()
    builder.locator('#book-grid .page-slot[data-page="2"]').click()
    assert builder.evaluate("B.deck.pages[2]") == "S-001"                    # 連點不刪卡
    assert builder.evaluate("B.selected") is None                             # 第二次取消選取


def test_remove_button_on_selected_filled_slot(builder):
    put(builder, {3: "S-001"})
    assert builder.locator("#book-grid .slot-remove").count() == 0           # 未選中:沒有按鈕
    builder.locator('#book-grid .page-slot[data-page="2"]').click()
    btn = builder.locator('#book-grid .page-slot[data-page="2"] .slot-remove')
    assert btn.count() == 1 and btn.text_content() == "移除"
    btn.click()
    assert builder.evaluate("B.deck.pages[2]") is None
    assert builder.evaluate("B.selected") == 2                                # 仍選中,可直接補卡
    assert builder.locator("#book-grid .slot-remove").count() == 0           # 空頁沒有按鈕


def test_delete_key_removes_selected(builder):
    put(builder, {3: "S-001"})
    slot = builder.locator('#book-grid .page-slot[data-page="2"]')
    slot.click()
    builder.locator('#book-grid .page-slot[data-page="2"]').press("Delete")
    assert builder.evaluate("B.deck.pages[2]") is None


# ---------------------------------------------------------------- 尚未開放的卡(deck-builder「卡池不顯示尚未開放的卡」)

def test_pending_cards_hidden_from_pool_and_products(builder):
    assert "M-035" not in pool_numbers(builder) and "M-001" in pool_numbers(builder)
    _, _, product = selects(builder)
    options = product.locator("option").all_text_contents()
    # 只含尚未開放卡的產品不列出;含已開放卡的產品照常列出(Spell Book 含第 1 批的 M-033)。
    # 之後的批次開放 Dawn of the Ancients 的卡時,改用其他仍全為尚未開放卡的產品。
    assert "Dawn of the Ancients" not in options and "Spell Book" in options
    put(builder, {6: "E-028"})                                              # 匯入等方式放進魔書
    assert "E-028" in builder.locator("#builder-validation").text_content()


def test_variable_damage_card_face(builder):
    builder.evaluate("zoom('S-061')")                                         # 卡面「ダメージ?」
    assert "傷害 ?" in builder.locator("#zoom-card .cmeta").text_content()
    builder.evaluate("zoom('S-001')")
    assert "傷害 1" in builder.locator("#zoom-card .cmeta").text_content()
