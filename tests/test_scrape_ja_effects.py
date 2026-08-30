"""tools/scrape_ja_effects.py 的純解析函式測試(不需要網路)。

fixture 用自己編的最小合成 HTML,只照著已用真實頁面核對過的結構(<blockquote> 內以 <hr/>
分隔兩段、全形空白分隔的資料頭)造,卡號/名稱/效果文字全為測試占位文字,不重製任何真實卡片內容,
也不依賴 ref/ 下未版控的頁面存檔。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.scrape_ja_effects import (  # noqa: E402
    parse_card_page, parse_header, parse_product_page,
)

PRODUCT_PAGE_HTML = """
<h2>テスト商品</h2>
<h3 id="id_x">収録カード</h3>
<h4 id="id_a">魔物</h4>
<ul><li>T-001 <a href="//w.example.test/pages/901.html"  >
テスト魔物
</a></li></ul>
<br />
<h4 id="id_b">術</h4>
<ul><li>T-101 <a href="//w.example.test/pages/902.html"  >
テスト術
</a></li>
<li>T-102 <a href="//w.example.test/pages/903.html"  >
非バトル術
</a></li></ul>
<div id="atwiki-page-tags">...</div>
"""

# 資料頭全部在第 1 行就滿足必填(術卡:ad + power)
SPELL_CARD_HTML = """
<h2>T-101　テスト術</h2>
<blockquote><div>
T-101　テスト術
<br />
術　中級　MP5　＋4000　ダメージ3　バトル攻撃　重力
<br />
仮の効果文その一。
<br />
仮の効果文その二。
<br />
<a href="//w.example.test/pages/901.html"  >テスト魔物</a>第4の術

</div>
<hr />
<div>
テスト用の風味文。
<br />
LEVEL:テスト　テストパック
<br />
LEVEL:テスト　別テストパック

</div>
</blockquote>
"""

# 資料頭跨兩行:第 1 行只有 power,ad 要到第 2 行才出現(相手のターン)
SPELL_CARD_TWO_LINE_HEADER_HTML = """
<h2>T-103　テスト術2</h2>
<blockquote><div>
T-103　テスト術2
<br />
術　MP3　特殊　非バトル
<br />
相手のターン
<br />
仮の効果文。

</div>
<hr />
<div>
テスト用の風味文その二。
<br />
LEVEL:テスト　テストパック

</div>
</blockquote>
"""

# event 卡:ad 資訊在第 1 行(自分のターン)就出現,第 2 行不應被當成資料頭(對應 E-015 案例)
EVENT_CARD_HTML = """
<h2>T-201　テストイベント</h2>
<blockquote><div>
T-201　テストイベント
<br />
イベント　MP0　自分のターン
<br />
【ステイ】自分の魔物1体を選ぶ。攻撃を仕掛ける。

</div>
<hr />
<div>
テスト用の風味文その三。
<br />
LEVEL:テスト　テストパック

</div>
</blockquote>
"""

MAMODO_CARD_HTML = """
<h2>T-001　テスト魔物</h2>
<blockquote><div>
T-001　テスト魔物
<br />
魔物　3000　バトル
<br />
《テスト技》MPを1へらす→自分が攻撃するバトル中、この魔物の魔力を+500する。

</div>
<hr />
<div>
テスト用の風味文その四。
<br />
LEVEL:テスト　テストパック

</div>
</blockquote>
"""

# 缺必填欄位:術卡兩行都沒有 ad 資訊
SPELL_MISSING_AD_HTML = """
<h2>T-104　テスト術3</h2>
<blockquote><div>
T-104　テスト術3
<br />
術　MP3　＋2000
<br />
仮の効果文。

</div>
<hr />
<div>
テスト用の風味文その五。
<br />
LEVEL:テスト　テストパック

</div>
</blockquote>
"""


def test_parse_product_page_groups_by_category():
    entries = parse_product_page(PRODUCT_PAGE_HTML, "https://example.test/product.html")
    assert entries == [
        ("T-001", "https://w.example.test/pages/901.html", "テスト魔物", "魔物"),
        ("T-101", "https://w.example.test/pages/902.html", "テスト術", "術"),
        ("T-102", "https://w.example.test/pages/903.html", "非バトル術", "術"),
    ]


def test_parse_header_single_line_satisfies_required():
    header, consumed = parse_header(
        ["術　中級　MP5　＋4000　ダメージ3　バトル攻撃　重力", "效果文"], "spell", "T-101")
    assert consumed == 1
    assert header["class"] == "intermediate"
    assert header["cost"] == 5
    assert header["power"] == "+4000"
    assert header["damage"] == 3
    assert header["attr_ja"] == "重力"
    assert header["ad"] == "A"


def test_parse_header_falls_through_to_second_line():
    header, consumed = parse_header(
        ["術　MP3　特殊　非バトル", "相手のターン", "效果文"], "spell", "T-103")
    assert consumed == 2
    assert header["power"] == "特殊"
    assert header["effect_icon_ja"] == "非バトル"
    assert header["ad"] == "D"


def test_parse_header_event_satisfied_by_first_line_only():
    """對應 E-015:自分のターン 在第 1 行就出現,不應嘗試消耗第 2 行。"""
    header, consumed = parse_header(
        ["イベント　MP0　自分のターン", "這行是效果文,不該被當成資料頭"], "event", "E-015")
    assert consumed == 1
    assert header["ad"] == "A"
    assert header["cost"] == 0


def test_parse_header_mamodo_bare_power_no_ad_required():
    header, consumed = parse_header(["魔物　3000　バトル"], "mamodo", "T-001")
    assert consumed == 1
    assert header["power"] == "3000"
    assert header["effect_icon_ja"] == "バトル"
    assert header["ad"] == ""  # 魔物卡不要求 ad


def test_parse_header_power_x_suffix_format():
    header, _ = parse_header(["術　MP2　2000x　バトル攻撃"], "spell", "S-040-test")
    assert header["power"] == "2000x"


def test_parse_header_power_multiplication_sign_suffix():
    """實際 wiki 用的是乘號「×」(U+00D7),不是字母 x(S-040 真實案例)。"""
    header, _ = parse_header(["術　MP2　2000×　ダメージ1　木　バトル攻撃"], "spell", "S-040")
    assert header["power"] == "2000×"
    assert header["attr_ja"] == "木"
    assert header["damage"] == 1


def test_parse_header_known_data_gap_override():
    """S-021:官方頁面本身漏刊 power token,登記為已知缺漏後應套用覆寫值而非報錯。"""
    header, consumed = parse_header(["術　MP2　バトル防御"], "spell", "S-021")
    assert consumed == 1
    assert header["power"] == "特殊"
    assert header["ad"] == "D"


def test_parse_header_unknown_card_still_raises_on_missing_power():
    """已知缺漏清單只對登記過的卡號生效,其他卡缺 power 仍要報錯。"""
    with pytest.raises(ValueError, match="power"):
        parse_header(["術　MP2　バトル防御"], "spell", "S-999-not-registered")


def test_parse_header_missing_required_field_raises():
    with pytest.raises(ValueError, match="power"):
        parse_header(["術　MP3　バトル攻撃", "還是沒有 power"], "spell", "T-999")


def test_parse_header_unknown_token_raises():
    with pytest.raises(ValueError, match="無法辨識"):
        parse_header(["術　MP3　＋2000　謎の属性"], "spell", "T-998")


def test_parse_card_page_spell_single_line_header():
    r = parse_card_page(SPELL_CARD_HTML, "術", "T-101")
    assert r["class"] == "intermediate"
    assert r["cost"] == 5
    assert r["power"] == "+4000"
    assert r["damage"] == 3
    assert r["attr_ja"] == "重力"
    assert r["ad"] == "A"
    assert r["related_mamodo_ja"] == "テスト魔物"
    assert r["effect_ja"] == "仮の効果文その一。仮の効果文その二。"
    assert r["flavor_ja"] == "テスト用の風味文。"
    assert r["sets_ja"] == "LEVEL:テスト　テストパック|LEVEL:テスト　別テストパック"


def test_parse_card_page_spell_two_line_header():
    r = parse_card_page(SPELL_CARD_TWO_LINE_HEADER_HTML, "術", "T-103")
    assert r["power"] == "特殊"
    assert r["ad"] == "D"
    assert r["effect_icon_ja"] == "非バトル"
    assert r["effect_ja"] == "仮の効果文。"


def test_parse_card_page_event_second_line_is_effect_text():
    r = parse_card_page(EVENT_CARD_HTML, "イベント", "T-201")
    assert r["ad"] == "A"
    assert r["cost"] == 0
    assert "攻撃を仕掛ける" in r["effect_ja"]  # 第 2 行完整併入效果文,不被誤判為資料頭


def test_parse_card_page_mamodo_ability_text_not_misparsed():
    """回歸測試:魔物卡技能文字裡出現「攻撃」字樣,不應被誤判成資料頭或遺失。"""
    r = parse_card_page(MAMODO_CARD_HTML, "魔物", "T-001")
    assert r["power"] == "3000"
    assert r["ad"] == ""
    assert "攻撃" in r["effect_ja"]
    assert r["flavor_ja"] == "テスト用の風味文その四。"


def test_parse_card_page_missing_ad_raises():
    # 兩行資料頭都湊不齊必填的 ad;第 2 行本身若不是合法資料頭 token,
    # 也可能先在「無法辨識的標籤」報錯——兩者都是「不可靜默放行」這個核心行為的體現。
    with pytest.raises(ValueError):
        parse_card_page(SPELL_MISSING_AD_HTML, "術", "T-104")
