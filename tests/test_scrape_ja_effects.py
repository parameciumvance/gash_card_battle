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
    KNOWN_EXTRA_FLAVOR, KNOWN_SET_ERRORS, KNOWN_TEXT_ERRORS, parse_card_page, parse_header,
    parse_product_page,
)
import tools.scrape_ja_effects as scraper  # noqa: E402


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
LEVEL:1　テストパック
<br />
LEVEL:1　別テストパック

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
仮の効果文。テスト魔物第2の術

</div>
<hr />
<div>
テスト用の風味文その二。
<br />
LEVEL:1　テストパック

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
LEVEL:1　テストパック

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
<br />
パートナー＝テスト搭檔

</div>
<hr />
<div>
テスト用の風味文その四。
<br />
LEVEL:1　テストパック

</div>
</blockquote>
"""

# 魔物卡:卡面多印一段「框線規則」,wiki 拆成 4 段 <div>(對應 M-007/M-029 真實案例)
MAMODO_CARD_FRAMED_RULE_HTML = """
<h2>T-002　テスト変身魔物</h2>
<blockquote><div>
T-002　テスト変身魔物
<br />
魔物　5000
<br />
自分の「テスト魔物」に重ねる。

</div>
<hr />
<div>
以上、枠囲み

</div>
<hr />
<div>
《テスト技2》MPを1へらす→仮の効果文。
<br />
パートナー＝テスト搭檔2

</div>
<hr />
<div>
テスト用の風味文その十一。
<br />
LEVEL:1　テストパック

</div>
</blockquote>
"""

# 搭檔卡:最後一行「魔物＝X」宣告對應魔物(對應 P-001 真實案例)
PARTNER_CARD_HTML = """
<h2>T-301　テスト搭檔</h2>
<blockquote><div>
T-301　テスト搭檔
<br />
パートナー
<br />
《SET!》このカードを捨て札にする→仮の効果文。
<br />
魔物＝テスト魔物

</div>
<hr />
<div>
テスト用の風味文その六。
<br />
LEVEL:1　テストパック

</div>
</blockquote>
"""

# 搭檔卡:沒有「魔物＝X」尾行,最後一行應完整併入效果文
PARTNER_CARD_NO_TAIL_HTML = """
<h2>T-302　テスト搭檔2</h2>
<blockquote><div>
T-302　テスト搭檔2
<br />
パートナー
<br />
仮の効果文その一。

</div>
<hr />
<div>
テスト用の風味文その七。
<br />
LEVEL:1　テストパック

</div>
</blockquote>
"""

# 術卡:對象魔物名無連結,純文字(對應 S-043/S-048 等真實案例)
SPELL_CARD_UNLINKED_TAIL_HTML = """
<h2>T-105　テスト術4</h2>
<blockquote><div>
T-105　テスト術4
<br />
術　MP2　＋1000　バトル攻撃
<br />
仮の効果文。テスト魔物第1の術

</div>
<hr />
<div>
テスト用の風味文その八。
<br />
LEVEL:1　テストパック

</div>
</blockquote>
"""

# 術卡:指令術(コマンド),不屬於特定魔物
COMMAND_SPELL_HTML = """
<h2>T-106　テストコマンド術</h2>
<blockquote><div>
T-106　テストコマンド術
<br />
術　MP1　特殊　バトル攻撃
<br />
仮の効果文。
<br />
コマンド

</div>
<hr />
<div>
テスト用の風味文その九。
<br />
LEVEL:1　テストパック

</div>
</blockquote>
"""

# 搭檔卡:尾行格式跟登記過的已知缺漏(P-018)不同,應套用覆寫值而非報錯
PARTNER_CARD_KNOWN_GAP_HTML = """
<h2>P-018　テスト搭檔3</h2>
<blockquote><div>
P-018　テスト搭檔3
<br />
パートナー
<br />
仮の効果文。パートナー＝ヨポポ

</div>
<hr />
<div>
テスト用の風味文その十。
<br />
LEVEL:1　テストパック
<br />
TBB　N

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
LEVEL:1　テストパック

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
    assert r["sets_ja"] == "LEVEL:1　テストパック|LEVEL:1　別テストパック"


def test_parse_card_page_spell_two_line_header():
    r = parse_card_page(SPELL_CARD_TWO_LINE_HEADER_HTML, "術", "T-103")
    assert r["power"] == "特殊"
    assert r["ad"] == "D"
    assert r["effect_icon_ja"] == "非バトル"
    assert r["related_mamodo_ja"] == "テスト魔物"
    assert r["effect_ja"] == "仮の効果文。"  # 尾巴與敘述文黏同一行,句號前的文字仍保留


def test_parse_card_page_spell_unlinked_related_mamodo():
    """對象魔物名沒有包在連結裡也要能解析(對應 S-043/S-048 等真實案例)。"""
    r = parse_card_page(SPELL_CARD_UNLINKED_TAIL_HTML, "術", "T-105")
    assert r["related_mamodo_ja"] == "テスト魔物"
    assert "第1の術" not in r["effect_ja"]


def test_parse_card_page_command_spell():
    """指令術(コマンド)不屬於特定魔物,related_mamodo_ja 存為「コマンド」。"""
    r = parse_card_page(COMMAND_SPELL_HTML, "術", "T-106")
    assert r["related_mamodo_ja"] == "コマンド"
    assert r["effect_ja"] == "仮の効果文。"


def test_parse_card_page_partner_known_gap_override():
    """P-018:頁面尾行寫成「パートナー＝X」而非「魔物＝X」,登記為已知缺漏後套用覆寫值。"""
    r = parse_card_page(PARTNER_CARD_KNOWN_GAP_HTML, "パートナー", "P-018")
    assert r["related_mamodo_ja"] == "ヨポポ"


def test_parse_card_page_spell_missing_related_mamodo_raises():
    with pytest.raises(ValueError, match="related_mamodo_ja"):
        parse_card_page(SPELL_MISSING_AD_HTML.replace("＋2000", "＋2000　バトル攻撃"), "術", "T-107")


def test_parse_card_page_partner_missing_related_mamodo_raises_when_not_registered():
    with pytest.raises(ValueError, match="related_mamodo_ja"):
        parse_card_page(PARTNER_CARD_NO_TAIL_HTML, "パートナー", "T-302")


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
    assert r["related_partner_ja"] == "テスト搭檔"
    assert r["related_mamodo_ja"] == ""
    assert r["flavor_ja"] == "テスト用の風味文その四。"


def test_parse_card_page_mamodo_missing_partner_raises():
    html_without_partner_tail = MAMODO_CARD_HTML.replace(
        "\nパートナー＝テスト搭檔\n", "\n")
    with pytest.raises(ValueError, match="related_partner_ja"):
        parse_card_page(html_without_partner_tail, "魔物", "T-999-no-partner")


def test_parse_card_page_mamodo_framed_rule_block():
    """回歸測試:框線規則卡(變身/術相容性等)多拆出中間 <div>,對應 M-007/M-029 真實案例。
    框線提示「以上、枠囲み」應被濾掉,框線規則文字與後段《能力》效果文都要保留,
    パートナー＝X 尾行要能從最後一段(而非第一段)正確解析出來。"""
    r = parse_card_page(MAMODO_CARD_FRAMED_RULE_HTML, "魔物", "T-002")
    assert r["power"] == "5000"
    assert r["related_partner_ja"] == "テスト搭檔2"
    assert "枠囲み" not in r["effect_ja"]
    assert "自分の「テスト魔物」に重ねる" in r["effect_ja"]
    assert "仮の効果文" in r["effect_ja"]
    assert r["flavor_ja"] == "テスト用の風味文その十一。"


def test_parse_card_page_partner_tail_line_parsed():
    r = parse_card_page(PARTNER_CARD_HTML, "パートナー", "T-301")
    assert r["related_mamodo_ja"] == "テスト魔物"
    assert "魔物＝" not in r["effect_ja"]
    assert "仮の効果文" in r["effect_ja"]


def test_parse_card_page_missing_ad_raises():
    # 兩行資料頭都湊不齊必填的 ad;第 2 行本身若不是合法資料頭 token,
    # 也可能先在「無法辨識的標籤」報錯——兩者都是「不可靜默放行」這個核心行為的體現。
    with pytest.raises(ValueError):
        parse_card_page(SPELL_MISSING_AD_HTML, "術", "T-104")


# ---------------------------------------------------------------- 第三彈:土元素、傷害依效果、卡號範圍

def test_parse_header_earth_element():
    header, used = parse_header(["術　MP2　＋4000　ダメージ1　土　バトル攻撃"], "spell", "T-201")
    assert header["attr_ja"] == "土" and header["damage"] == 1


def test_parse_header_variable_damage():
    header, used = parse_header(["術　中級　MP4　＋8000　ダメージ?　バトル攻撃"], "spell", "T-202")
    assert header["damage"] == "?"


def test_number_ranges_filter():
    from tools.scrape_ja_effects import in_ranges, parse_range
    ranges = [parse_range("M-032:M-034"), parse_range("E-041:E-043")]
    assert in_ranges("M-033", ranges) and in_ranges("E-043", ranges)
    assert not in_ranges("M-059", ranges) and not in_ranges("S-033", ranges)
    assert in_ranges("M-059", [])                                            # 未指定範圍:不篩選


def test_parse_header_third_line_only_when_all_tokens():
    # S-093 型:資料頭跨 3 行(第 2 行只有 power,ad 與效果 icon 在第 3 行)
    header, used = parse_header(["術　MP1", "特殊", "自分のターン　非バトル", "効果文。"], "spell", "T-203")
    assert used == 3 and header["ad"] == "A" and header["effect_icon_ja"] == "非バトル"


def test_parse_header_third_line_effect_text_not_consumed():
    # 第 3 行是效果文時不讀入資料頭,仍以缺漏報錯
    with pytest.raises(ValueError):
        parse_header(["術　MP1", "特殊", "仮の効果文。"], "spell", "T-204")


def test_spell_tail_with_unknown_spell_number():
    from tools.scrape_ja_effects import SPELL_TAIL_RE
    m = SPELL_TAIL_RE.search("ゼオン第Xの術")
    assert m and m.group(1) == "ゼオン"


def test_parse_header_trailing_icon_line_consumed():
    # S-086 型:必填欄位在前 2 行已齊,第 3 行只有效果 icon
    header, used = parse_header(["術　MP1　特殊", "自分のターン", "非バトル", "効果文。"], "spell", "T-205")
    assert used == 3 and header["effect_icon_ja"] == "非バトル"


def test_parse_header_mamodo_ad_only_line_consumed():
    # M-039 型:魔物卡第 2 行只有回合欄位(魔物效果攻擊 / 防禦的標示)
    header, used = parse_header(["魔物　4500", "バトル攻撃　バトル防御", "《格闘》効果文。"], "mamodo", "T-206")
    assert used == 2 and header["ad"] == "AD"


def test_parse_header_effect_line_not_consumed_after_satisfied():
    header, used = parse_header(["イベント　MP0　自分のターン", "仮の効果文。"], "event", "T-207")
    assert used == 1


def test_parse_header_marker_lines_split_across_lines():
    # M-039 實際頁面:「バトル攻撃」「バトル防御」分在兩行
    header, used = parse_header(["魔物　4500", "バトル攻撃", "バトル防御", "《格闘》効果文。"], "mamodo", "T-208")
    assert used == 3 and header["ad"] == "AD"


MAMODO_MARKER_IN_SECOND_DIV_HTML = """
<blockquote><div>
T-301　テスト魔物
<br />
魔物　4500　
<br />
バトル攻撃
</div>
<hr />
<div>
バトル防御
<br />
《格闘》仮の効果文。
<br />
パートナー＝テスト人
</div>
<hr />
<div>
風味文。
<br />
LEVEL:1
</div></blockquote>
"""


def test_parse_card_page_marker_line_in_middle_segment():
    r = parse_card_page(MAMODO_MARKER_IN_SECOND_DIV_HTML, "魔物", "T-301")
    assert r["ad"] == "AD" and r["effect_ja"].startswith("《格闘》")
    assert r["related_partner_ja"] == "テスト人"


S069_WRONG = ("●この術を防御に使ったとき相手は、この攻撃を防御できない。コインを投げてオモテなら、相手の魔本にダメージ。"
              "●この術を攻撃に使ったとき魔力勝負の勝敗にかかわらず、コインを投げてオモテなら、相手の攻撃を無効にする。")


def _s069_html(effect):
    return f"""
<h2>S-069　リグロン</h2>
<blockquote><div>
S-069　リグロン
<br />
術　MP2　特殊　ダメージ1　バトル攻撃　バトル防御
<br />
{effect}
<br />
<a href="//w.example.test/pages/901.html"  >ロップス</a>第1の術

</div>
<hr />
<div>
風味文。
<br />
LEVEL:3　テスト

</div>
</blockquote>
"""


def test_known_text_error_corrected():
    """S-069:atwiki 的效果文把攻擊與防禦兩段的標題寫反,登記為已知效果文錯誤後取代。"""
    r = parse_card_page(_s069_html(S069_WRONG), "術", "S-069")
    assert r["effect_ja"] == KNOWN_TEXT_ERRORS["S-069"][1]
    assert r["effect_ja"].startswith("●この術を攻撃に使ったとき相手は、この攻撃を防御できない。")


def test_known_text_error_source_changed_raises():
    with pytest.raises(ValueError):
        parse_card_page(_s069_html("●別の効果文。"), "術", "S-069")


def _e024_html(flavor_lines):
    lines = "\n<br />\n".join(flavor_lines)
    return f"""
<h2>E-024　テストイベント</h2>
<blockquote><div>
E-024　テストイベント
<br />
イベント　MP0　自分のターン　相手のターン
<br />
仮の効果文。

</div>
<hr />
<div>
{lines}

</div>
</blockquote>
"""


def test_known_extra_flavor_line_not_a_product():
    """E-024:風味文有兩行,第二行不是收錄產品,併入 flavor_ja。"""
    extra = KNOWN_EXTRA_FLAVOR["E-024"]
    r = parse_card_page(_e024_html(["森の妖精･･････? (LEVEL:S)", extra, "LEVEL:2　UR自販機", "LEVEL:S　N"]),
                        "イベント", "E-024")
    assert r["flavor_ja"] == f"森の妖精･･････? (LEVEL:S)\n{extra}"
    assert r["sets_ja"] == "LEVEL:2　UR自販機|LEVEL:S　N"


def test_known_extra_flavor_source_changed_raises():
    with pytest.raises(ValueError):
        parse_card_page(_e024_html(["森の妖精･･････? (LEVEL:S)", "LEVEL:2　UR自販機"]), "イベント", "E-024")


def test_known_set_error_corrected():
    """P-018:收錄產品「TBB　N」實為 TBB2(atwiki 頁標籤「THE BEST BOOSTER 2」)。"""
    r = parse_card_page(PARTNER_CARD_KNOWN_GAP_HTML, "パートナー", "P-018")
    wrong, fixed = KNOWN_SET_ERRORS["P-018"]
    assert fixed in r["sets_ja"].split("|") and wrong not in r["sets_ja"].split("|")


def test_known_set_error_source_changed_raises():
    with pytest.raises(ValueError):
        parse_card_page(PARTNER_CARD_KNOWN_GAP_HTML.replace("TBB　N", "TBB2　N"), "パートナー", "P-018")


# ---------------------------------------------------------------- 第 3 賽季:拡張シート與特典卡頁

EX_SHEET_PAGE_HTML = """
<h3 id="id_x">収録カード</h3>
<h4 id="id_a">魔物</h4>
<ul><li>Ex-001 <a href="//w.example.test/pages/911.html"  >
テスト魔物
</a> R/N</li></ul>
<br />
<h4 id="id_b">術</h4>
<ul><li>Ex-013 <a href="//w.example.test/pages/912.html"  >
テスト術
</a></li></ul>
<br />
<h3 id="id_y">収録カード（シート別）</h3>
<h4 id="id_c">シート1</h4>
<ul><li>Ex-001 <a href="//w.example.test/pages/911.html"  >
テスト魔物
</a> R/N</li>
<li>Ex-013 <a href="//w.example.test/pages/912.html"  >
テスト術
</a></li></ul>
<div id="atwiki-page-tags">...</div>
"""

PROMO_PAGE_HTML = """
<h2>特典カード</h2>
<h3 id="id_p">PR<a id="PR" name="PR"></a></h3>
<ul><li>PR-001 <a href="//w.example.test/pages/921.html"  >
テスト魔物
</a></li>
<li>PR-005 <a href="//w.example.test/pages/922.html"  >
テストイベント
</a></li></ul>
<h3 id="id_q">Ex<a id="Ex" name="Ex"></a></h3>
<ul><li>Ex-000 <a href="//w.example.test/pages/923.html"  >
テスト
</a></li></ul>
"""


def test_ex_sheet_page_skips_sheet_groups():
    entries = parse_product_page(EX_SHEET_PAGE_HTML, "https://example.test/p.html")
    assert [(n, c) for n, _, _, c in entries] == [("Ex-001", "魔物"), ("Ex-013", "術")]


def test_untyped_card_list_reads_whole_page():
    entries = scraper.parse_card_list(PROMO_PAGE_HTML, "https://example.test/p.html")
    assert [(n, name, c) for n, _, name, c in entries] == [
        ("PR-001", "テスト魔物", ""), ("PR-005", "テストイベント", ""), ("Ex-000", "テスト", "")]


def test_ex_and_pr_ranges():
    ranges = [scraper.parse_range("Ex-025:Ex-048"), scraper.parse_range("PR-001:PR-011")]
    assert scraper.in_ranges("Ex-030", ranges) and scraper.in_ranges("PR-011", ranges)
    assert not scraper.in_ranges("Ex-000", ranges) and not scraper.in_ranges("EX-030", ranges)


@pytest.mark.parametrize("header, category", [
    ("魔物　4000", "魔物"), ("イベント　MP0　自分のターン", "イベント"),
    ("術　MP2　＋1000　ダメージ1　バトル攻撃　雷", "術"), ("パートナー", "パートナー"),
])
def test_card_page_category_from_header(header, category):
    html = f"<blockquote><div>\nPR-001　テスト\n<br />\n{header}\n<br />\n効果。\n</div><hr /><div>風味。</div></blockquote>"
    assert scraper.card_page_category(html, "PR-001") == category


def test_card_page_category_unknown_raises():
    html = "<blockquote><div>\nPR-001　テスト\n<br />\nなにか　4000\n</div><hr /><div>風味。</div></blockquote>"
    with pytest.raises(ValueError):
        scraper.card_page_category(html, "PR-001")


def _ex_html(number, main_lines, last_lines):
    main = "\n<br />\n".join([f"{number}　テスト"] + main_lines)
    last = "\n<br />\n".join(last_lines)
    return f"<blockquote><div>\n{main}\n</div>\n<hr />\n<div>\n{last}\n</div></blockquote>"


def test_spell_tail_in_last_block():
    # 拡張シートの卡:「第N の術」印在最後一段開頭,沒有風味文
    html = _ex_html("Ex-013", ["術　MP1　＋3000　ダメージ1", "バトル攻撃　バトル防御", "相手の魔本にダメージ。"],
                    ['<a href="//w.example.test/p.html">ガッシュ・ベル</a>第1の術', "拡張1"])
    r = parse_card_page(html, "術", "Ex-013")
    assert r["related_mamodo_ja"] == "ガッシュ・ベル" and r["effect_ja"] == "相手の魔本にダメージ。"
    assert r["flavor_ja"] == "" and r["sets_ja"] == "拡張1"


def test_partner_tail_in_last_block():
    html = _ex_html("Ex-010", ["パートナー", "効果。"], ["魔物＝ハイド", "拡張1"])
    r = parse_card_page(html, "パートナー", "Ex-010")
    assert r["related_mamodo_ja"] == "ハイド" and r["flavor_ja"] == "" and r["sets_ja"] == "拡張1"


def test_no_flavor_only_products():
    html = _ex_html("Ex-004", ["魔物　4000", "パートナー＝テスト"], ["拡張1　R"])
    r = parse_card_page(html, "魔物", "Ex-004")
    assert r["flavor_ja"] == "" and r["sets_ja"] == "拡張1　R"


def test_two_flavor_lines_before_products():
    html = _ex_html("Ex-007", ["パートナー", "効果。", "魔物＝テスト"],
                    ["(スナック)風味その一。", "(TBB)風味その二。", "拡張1", "TBB1", "RE"])
    r = parse_card_page(html, "パートナー", "Ex-007")
    assert r["flavor_ja"] == "(スナック)風味その一。\n(TBB)風味その二。"
    assert r["sets_ja"] == "拡張1|TBB1|RE"


def test_known_misplaced_flavor():
    # Ex-005:風味文印在第一段的「パートナー＝」之後
    flavor = scraper.KNOWN_MISPLACED_FLAVOR["Ex-005"]
    html = _ex_html("Ex-005", ["魔物　4000", "パートナー＝大海恵", flavor], ["拡張1　R"])
    r = parse_card_page(html, "魔物", "Ex-005")
    assert r["related_partner_ja"] == "大海恵" and r["flavor_ja"] == flavor and r["effect_ja"] == ""


def test_known_misplaced_flavor_source_changed_raises():
    html = _ex_html("Ex-005", ["魔物　4000", "パートナー＝大海恵"], ["別の風味文。", "拡張1　R"])
    with pytest.raises(ValueError):
        parse_card_page(html, "魔物", "Ex-005")


def test_product_names_match_converter():
    from tools.build_cards_json import PRODUCTS
    assert scraper.PRODUCT_NAMES == (set(PRODUCTS) - {"別売魔本(第2弾)"}) | {"TBB"}


def test_ex002_stray_comma_removed():
    html = _ex_html("Ex-002", ["魔物　2000", "効果(0より小さくはならない)。,", "パートナー＝テスト"], ["風味。", "拡張1"])
    assert parse_card_page(html, "魔物", "Ex-002")["effect_ja"] == "効果(0より小さくはならない)。"
