"""各語言的靜態一致性檢查(battle-ui「i18n 字典」「規則頁」「更新內容」「錯誤訊息依錯誤碼顯示」、
card-data「日文與英文卡片文字」)。只保證完整與一致,不檢查翻譯品質。"""

import json
import re
from pathlib import Path

import pytest

from tools.build_card_texts import build_ja, load_csv, load_tts_names

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "frontend/i18n"
DATA = ROOT / "data"
LANGS = ("zh-TW", "zh-CN", "en", "ja")
PARAM_RE = re.compile(r"\{(\w+)\}")
KANA_RE = re.compile(r"[぀-ヿ]")

# 規則書中有、但本遊戲(第一、二彈卡池)不存在的機制,依語言的稱呼
ABSENT = {
    "zh-TW": ("石版", "W魔物", "VS魔物", "S魔物", "H魔物", "MJ12", "巴爾肯", "飛行"),
    "zh-CN": ("石版", "W魔物", "VS魔物", "S魔物", "H魔物", "MJ12", "巴尔肯", "飞行"),
    "ja": ("石版", "W魔物", "VS魔物", "S魔物", "H魔物", "MJ12", "バルカン", "飛行"),
    "en": ("stone tablet", "w mamodo", "vs mamodo", "s mamodo", "h mamodo", "mj12", "vulcan", "flying"),
}
# 「攻(A)」「防(D)」的兩種意思:攻防用的術(攻擊 / 防禦時)與事件卡、非戰鬥術(回合玩家)
ICON_TERMS = {
    "zh-TW": ("攻(A)", "防(D)", "攻擊時", "防禦時", "回合玩家"),
    "zh-CN": ("攻(A)", "防(D)", "攻击时", "防御时", "回合玩家"),
    "ja": ("攻(A)", "防(D)", "攻撃するとき", "防御するとき", "ターンプレイヤー"),
    "en": ("A (Attack)", "D (Defense)", "when attacking", "when defending", "turn player"),
}


def load(name):
    return json.loads((I18N / name).read_text(encoding="utf-8"))


def cards_json():
    return {c["number"]: c for c in json.loads((DATA / "cards.json").read_text(encoding="utf-8"))}


def card_texts(lang):
    return json.loads((DATA / f"cards.{lang}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 語言清單與字典

def test_language_list():
    langs = load("languages.json")
    assert [x["code"] for x in langs] == ["zh-TW", "zh-CN", "en", "ja"]
    assert [x["name"] for x in langs] == ["繁體中文", "简体中文", "English", "日本語"]


@pytest.mark.parametrize("lang", ["zh-CN", "en", "ja"])
def test_dictionaries_have_same_keys_and_params(lang):
    base, other = load("zh-TW.json"), load(f"{lang}.json")
    assert sorted(set(base) - set(other)) == []
    assert sorted(set(other) - set(base)) == []
    mismatched = {k: (base[k], other[k]) for k in base
                  if set(PARAM_RE.findall(base[k])) != set(PARAM_RE.findall(other[k]))}
    assert mismatched == {}


@pytest.mark.parametrize("lang", ["en", "ja"])
def test_dictionary_values_are_translated(lang):
    """日、英字典不應殘留中文(只用於中文的漢字詞)——以常見中文介面字檢查漏翻。"""
    d = load(f"{lang}.json")
    zh_only = re.compile(r"[們這嗎沒對擲幣牌區夥]")
    leftovers = {k: v for k, v in d.items() if zh_only.search(v)}
    assert leftovers == {}
    if lang == "en":
        assert {k: v for k, v in d.items() if re.search(r"[぀-ヿ一-鿿]", v)
                and k != "app.title"} == {}


def test_card_name_format_by_language():
    assert load("zh-TW.json")["ui.card_with_attr"] == "{name}《{attr}》"
    assert load("zh-CN.json")["ui.card_with_attr"] == "{name}《{attr}》"
    assert load("ja.json")["ui.card_with_attr"] == "{name}《{attr}》"
    assert load("en.json")["ui.card_with_attr"] == "{name} ({attr})"


@pytest.mark.parametrize("lang", LANGS)
def test_hints_name_card_icons_as_printed(lang):
    d = load(f"{lang}.json")
    a, dd = ICON_TERMS[lang][:2]
    assert a in d["hint.own_turn_cards"] and dd in d["hint.opp_turn_cards"]


# ---------------------------------------------------------------- 規則頁

@pytest.mark.parametrize("lang", ["zh-CN", "en", "ja"])
def test_rules_have_same_sections(lang):
    base, other = load("rules.zh-TW.json"), load(f"rules.{lang}.json")
    assert [s["id"] for s in other["sections"]] == [s["id"] for s in base["sections"]]
    for bs, os_ in zip(base["sections"], other["sections"]):
        assert [list(b) for b in os_["blocks"]] == [list(b) for b in bs["blocks"]], bs["id"]
    assert set(other["figure"]["marks"]) == set(base["figure"]["marks"])
    assert set(other) == set(base) and set(other["figure"]) == set(base["figure"])


@pytest.mark.parametrize("lang", LANGS)
def test_rules_no_absent_mechanics(lang):
    text = (I18N / f"rules.{lang}.json").read_text(encoding="utf-8")
    if lang == "en":   # 英文以整個詞比對(避免「its MAMODO」誤判為「S Mamodo」)
        assert [w for w in ABSENT[lang] if re.search(rf"\b{w}\b", text, re.I)] == []
    else:
        assert [w for w in ABSENT[lang] if w in text] == []


@pytest.mark.parametrize("lang", LANGS)
def test_rules_icons_section_explains_both_meanings(lang):
    icons = next(s for s in load(f"rules.{lang}.json")["sections"] if s["id"] == "icons")
    text = json.dumps(icons, ensure_ascii=False)
    assert [w for w in ICON_TERMS[lang] if w not in text] == []


# ---------------------------------------------------------------- 更新內容

VERSION_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
RELEASE_KINDS = {"new", "fix", "change"}


def release_shape(data):
    """不需翻譯的部分:版本、日期、標題有無、各條目分類。"""
    return [(r["version"], r["date"], "title" in r, [i["kind"] for i in r["items"]]) for r in data["releases"]]


@pytest.mark.parametrize("lang", LANGS)
def test_releases_are_well_formed(lang):
    data = load(f"releases.{lang}.json")
    assert set(data) == {"releases"} and data["releases"]
    versions = []
    for r in data["releases"]:
        assert set(r) <= {"version", "date", "title", "items"}, r
        m = VERSION_RE.match(r["version"])
        assert m, r["version"]
        versions.append(tuple(int(x) for x in m.groups()))
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", r["date"]), r
        if "title" in r:
            assert isinstance(r["title"], str) and r["title"].strip(), r
        for item in r["items"]:
            assert set(item) == {"kind", "text"} and item["kind"] in RELEASE_KINDS, item
            assert item["text"].strip(), item
    assert versions == sorted(set(versions), reverse=True)              # 由新到舊、不重複


@pytest.mark.parametrize("lang", ["zh-CN", "en", "ja"])
def test_releases_match_across_languages(lang):
    assert release_shape(load(f"releases.{lang}.json")) == release_shape(load("releases.zh-TW.json"))


@pytest.mark.parametrize("lang", LANGS)
def test_release_kind_labels(lang):
    d = load(f"{lang}.json")
    assert [k for k in sorted(RELEASE_KINDS) if not d.get(f"release.kind.{k}")] == []


@pytest.mark.parametrize("lang", ["en"])
def test_releases_are_translated(lang):
    text = (I18N / f"releases.{lang}.json").read_text(encoding="utf-8")
    assert not re.search(r"[぀-ヿ一-鿿]", text)


# ---------------------------------------------------------------- 卡片文字檔

@pytest.mark.parametrize("lang", LANGS)
def test_card_texts_cover_all_cards(lang):
    texts = card_texts(lang)
    missing = [n for n in cards_json() if not (texts.get(n) or {}).get("name") or not texts[n].get("effect")]
    assert missing == []


@pytest.mark.parametrize("lang", LANGS)
def test_card_text_name_ja_matches_csv(lang):
    texts = card_texts(lang)
    rows = {r["number"]: r for r in load_csv()}
    assert {n: texts[n]["name_ja"] for n in rows if texts[n]["name_ja"] != rows[n]["name_ja"]} == {}


def test_ja_card_texts_are_generated():
    assert card_texts("ja") == build_ja(load_csv())


# ---------------------------------------------------------------- 簡體中文(由繁中產生)

def test_zh_cn_files_are_generated_from_zh_tw():
    """繁中改了而沒有重跑 tools/build_zh_cn.py 時失敗。"""
    build_zh_cn = pytest.importorskip("tools.build_zh_cn")
    stale = [str(path.relative_to(ROOT)) for path, data in build_zh_cn.build().items()
             if json.loads(path.read_text(encoding="utf-8")) != data]
    assert stale == []


def test_zh_cn_converts_script_and_keeps_names():
    zh_tw, zh_cn = card_texts("zh-TW"), card_texts("zh-CN")
    assert zh_cn["M-001"]["name"] == "贾修・贝尔"                     # 譯名只轉字形
    assert {n: t["name_ja"] for n, t in zh_cn.items() if isinstance(t, dict)} == \
        {n: t["name_ja"] for n, t in zh_tw.items() if isinstance(t, dict)}   # 日文原名不轉換
    assert load("zh-CN.json")["app.title"] == load("zh-TW.json")["app.title"]
    assert load("zh-CN.json")["ui.landing.npc"] == "NPC 对战"


def test_zh_cn_terms():
    effects = "".join(t["effect"] for t in card_texts("zh-CN").values() if isinstance(t, dict))
    assert "【宣告使用→】" in effects and "声明" not in effects        # 遊戲術語保留
    rules = (I18N / "rules.zh-CN.json").read_text(encoding="utf-8")
    assert "进阶规则" in rules and "高端" not in rules
    d = load("zh-CN.json")
    assert d["ui.name.placeholder"] == "留白用默认"
    assert "复制" in d["ui.feedback.copy"]


def test_ja_card_text_examples():
    ja = card_texts("ja")
    assert ja["M-001"]["attr"] == "やさしい王様"
    assert ja["M-001"]["effect"] == cards_json()["M-001"]["effect_ja"]
    assert ja["S-001"]["attr"] == cards_json()["S-001"]["attr_name"]
    assert ja["E-001"]["attr"] is None


def test_en_names_match_tts_sheet():
    en, tts = card_texts("en"), load_tts_names()
    assert {n: (en[n]["name"], en[n]["attr"]) for n in en
            if (en[n]["name"], en[n]["attr"]) != (tts[n]["name"], tts[n]["attr"])} == {}
    assert en["M-001"]["name"] == "Zatch Bell"


def test_en_effects_are_translated():
    en = card_texts("en")
    assert [n for n, c in en.items() if KANA_RE.search(c["effect"])] == []


# ---------------------------------------------------------------- 錯誤碼

ERROR_RE = re.compile(
    r"""(?:IllegalCommand|DeckError|_npc_http_error)\(\s*f?["']([\w.]+)["']"""
    r"""|RoomError\(\s*\d+\s*,\s*["']([\w.]+)["']"""
    r"""|["']code["']:\s*["']([\w.]+)["']""")


def server_error_codes():
    codes = set()
    for path in (ROOT / "src").rglob("*.py"):
        for m in ERROR_RE.finditer(path.read_text(encoding="utf-8")):
            codes.add(next(g for g in m.groups() if g))
    return codes


def test_error_code_scan_finds_known_codes():
    codes = server_error_codes()
    assert {"room.not_found", "deck.first_page", "ability.condition", "npc.bad_level",
            "room.code_exhausted", "debug_state.bad_book"} <= codes
    assert len(codes) > 80


@pytest.mark.parametrize("lang", LANGS)
def test_every_error_code_is_translated(lang):
    d = load(f"{lang}.json")
    assert sorted(c for c in server_error_codes() if f"error.{c}" not in d) == []
