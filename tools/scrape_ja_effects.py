"""從 atwiki(金色のガッシュベル！！THE CARD BATTLE Wiki)抓日文卡片資料,產出 data/cards_ja.csv。

流程:
1. 讀「產品頁」(如 LEVEL:1/2 booster 頁)的「収録カード」清單區塊,依 魔物/術/パートナー/イベント
   四個分類取得每張卡的卡號、名稱與個別卡頁連結。
2. 逐一抓個別卡頁,取 <blockquote> 內兩段 <div>(以 <hr/> 分隔):
   - 第一段:卡號+名稱(捨棄,已知)/ 資料頭(1~2 行,見下)/ 效果文(可能多行)/ 若為術卡,
     最後一行常是「<對應魔物>第N の術」(從其中的連結取魔物名)。
   - 第二段:風味文(第一行)+ 收錄產品清單(其餘每行一個)。
3. 輸出 data/cards_ja.csv,供之後另寫腳本由此表格導出 cards.json(本次不做)。

資料頭解析規則(token 式,全形空白分隔,不依賴固定位置):
- 每個 token 都必須被歸類到下列其中一種,否則視為未知標籤,直接 raise(不靜默略過、不歸類為屬性):
  類型(魔物/術/パートナー/イベント,已知略過)/ 級別(中級/上級)/ 費用(MP+數字)/ 傷害(ダメージ+數字)/
  魔力 power(見下)/ 元素屬性(水/火/雷/氷/木/風/重力)/ 效果 icon(バトル/非バトル/ジャマー)/
  回合欄位 AD(バトル攻撃/バトル防御/自分のターン/相手のターン,四者皆換算為 A/D/AD)。
- power 保留原始標記以區分格式:"4000"(無加號,魔物基礎魔力)、"+4000"(有加號,術的魔力加值)、
  "特殊"(Special)、"2000x" 這種數字+x 後綴(擲幣倍率型,如 S-040)。
- 必填欄位依卡片類型而定:イベント/術 需要 ad;魔物/術 需要 power。資料頭預設只吃第 1 行;
  第 1 行結束後必填欄位仍不齊,才接著吃第 2 行;吃完 2 行後仍不齊,直接 raise(例如某張卡漏刊資料)。
  E-015 是「AD 資訊在第 1 行就出現」的例子:第 1 行「イベント　MP0　自分のターン」已滿足 event
  卡必填的 ad,第 2 行不會被當成資料頭的一部分,而是直接併入效果文。

此網站會擋掉沒有瀏覽器 User-Agent 的請求(開發沙箱環境即被擋 403),需在有正常網路出口的機器上執行。
支援本機已存的 .html 檔案(如手動另存的頁面)混用網址,方便先驗證解析邏輯再正式大量抓取。
已存在 data/cards_ja.csv 的卡號會跳過(可分批執行、中斷續抓);每抓一張卡即寫回檔案,不怕中途中斷。

用法:
  python tools/scrape_ja_effects.py https://w.atwiki.jp/zatchbell/pages/33.html
  python tools/scrape_ja_effects.py https://w.atwiki.jp/zatchbell/pages/33.html https://w.atwiki.jp/zatchbell/pages/34.html
  python tools/scrape_ja_effects.py ref/1345.html   # 先用本機另存的頁面驗證解析邏輯
"""

from __future__ import annotations

import csv
import re
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/cards_ja.csv"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

FIELDNAMES = [
    "number", "type", "name_ja", "related_mamodo_ja", "cost", "ad", "class",
    "attr_ja", "effect_icon_ja", "effect_ja", "power", "damage", "flavor_ja",
    "sets_ja", "url", "raw_header_lines",
]

CATEGORY_TO_TYPE = {"魔物": "mamodo", "術": "spell", "パートナー": "partner", "イベント": "event"}
CLASS_MAP = {"中級": "intermediate", "上級": "superior"}
ELEMENT_TOKENS = {"水", "火", "雷", "氷", "木", "風", "重力"}
EFFECT_ICON_TOKENS = {"バトル", "非バトル", "ジャマー"}
AD_TOKENS = {"バトル攻撃": "A", "バトル防御": "D", "自分のターン": "A", "相手のターン": "D"}
REQUIRED_FIELDS = {"event": {"ad"}, "spell": {"ad", "power"}, "mamodo": {"power"}, "partner": set()}

# 已知官方頁面本身漏刊必填欄位的卡:{卡號: {欄位: 值}}。人工核對過缺漏(對照英文資料確認)
# 才登記於此,不是用來繞過解析錯誤,而是記錄「這張卡的 wiki 頁面漏刊」這個事實。
KNOWN_DATA_GAPS: dict[str, dict] = {
    "S-021": {"power": "特殊"},  # 效果為「無視魔力」的特殊防禦術,頁面漏刊 power token
}

POWER_X_RE = re.compile(r"^\d+[x×]$", re.I)  # 擲幣倍率型,如 S-040 的 "2000×"(乘號,非字母 x)
POWER_PLUS_RE = re.compile(r"^[＋+](\d+)$")  # 術的魔力加值,如 "＋4000"

TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.I)


def fetch(url_or_path: str) -> str:
    """網址走 HTTP 抓取;否則視為本機檔案路徑讀取。"""
    if url_or_path.startswith("http"):
        req = urllib.request.Request(url_or_path, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.read().decode("utf-8", errors="replace")
    return Path(url_or_path).read_text(encoding="utf-8", errors="replace")


def strip_tags(html: str) -> str:
    return TAG_RE.sub("", html).strip()


# ---------------------------------------------------------------- 產品頁:収録カード 清單

SECTION_RE = re.compile(r">収録カード</h3>(.*?)(?:<div id=\"atwiki-page-tags\"|$)", re.S)
CATEGORY_RE = re.compile(r'<h4[^>]*>([^<]+)</h4>(.*?)(?=<h4|\Z)', re.S)
CARD_LI_RE = re.compile(r'<li>\s*([A-Z]+-\d+)\s*<a href="([^"]+)"[^>]*>\s*([^<]*?)\s*</a>', re.S)


def parse_product_page(html: str, base_url: str) -> list[tuple[str, str, str, str]]:
    """回傳 [(卡號, 個別卡頁絕對網址, 名稱, 分類原文), ...]。"""
    m = SECTION_RE.search(html)
    if not m:
        raise ValueError("找不到「収録カード」區塊,頁面格式可能不同")
    section = m.group(1)
    out = []
    for category, block in CATEGORY_RE.findall(section):
        for number, href, name in CARD_LI_RE.findall(block):
            out.append((number, urljoin(base_url, href), name.strip(), category.strip()))
    return out


# ---------------------------------------------------------------- 個別卡頁:官方資料區塊

BLOCK_RE = re.compile(r"<blockquote>\s*<div>(.*?)</div>\s*<hr\s*/?>\s*<div>(.*?)</div>\s*</blockquote>",
                     re.S)
SPELL_TAIL_RE = re.compile(r'<a[^>]*>([^<]+)</a>\s*第(\d+)の?術')


def classify_token(tok: str, header: dict, number: str) -> None:
    """就地更新 header dict。無法歸類的 token 直接 raise,不默默略過或誤歸類為屬性。"""
    if tok in CATEGORY_TO_TYPE:
        return
    if tok in CLASS_MAP:
        header["class"] = CLASS_MAP[tok]
        return
    if tok.startswith("MP") and tok[2:].isdigit():
        header["cost"] = int(tok[2:])
        return
    if tok.startswith("ダメージ") and tok[4:].isdigit():
        header["damage"] = int(tok[4:])
        return
    if tok in ELEMENT_TOKENS:
        header["attr_ja"] = tok
        return
    if tok in EFFECT_ICON_TOKENS:
        header["effect_icons"].append(tok)
        return
    if tok in AD_TOKENS:
        header["ad_hits"].add(AD_TOKENS[tok])
        return
    if tok == "特殊":
        header["power"] = tok
        return
    if POWER_X_RE.match(tok):
        header["power"] = tok
        return
    m = POWER_PLUS_RE.match(tok)
    if m:
        header["power"] = "+" + m.group(1)
        return
    if tok.isdigit():
        header["power"] = tok
        return
    raise ValueError(f"{number}: 無法辨識的標籤 {tok!r}(原始: {header.get('_line', '')!r})")


def parse_header(main_lines: list[str], type_: str, number: str) -> tuple[dict, int]:
    """回傳 (header 欄位 dict, 消耗掉的行數 1 或 2)。必填欄位(見 REQUIRED_FIELDS)第 1 行
    填不滿時接著吃第 2 行,吃完 2 行仍不滿則 raise。"""
    if not main_lines:
        raise ValueError(f"{number}: 沒有資料列")
    required = REQUIRED_FIELDS.get(type_, set())
    header = {"class": "none", "cost": None, "power": None, "damage": None,
              "attr_ja": None, "ad_hits": set(), "effect_icons": []}

    def missing_fields() -> set[str]:
        m = set()
        if "ad" in required and not header["ad_hits"]:
            m.add("ad(回合欄位)")
        if "power" in required and header["power"] is None:
            m.add("power")
        return m

    def consume(line: str) -> None:
        header["_line"] = line
        for tok in line.split("　"):
            tok = tok.strip()
            if tok:
                classify_token(tok, header, number)

    consume(strip_tags(main_lines[0]))
    missing = missing_fields()
    consumed = 1
    if missing and len(main_lines) > 1:
        consume(strip_tags(main_lines[1]))
        consumed = 2
        missing = missing_fields()
    if missing and number in KNOWN_DATA_GAPS:
        header.update(KNOWN_DATA_GAPS[number])
        missing = missing_fields()
    if missing:
        raise ValueError(f"{number}: 缺少必填欄位 {missing}(已讀 {consumed} 行資料頭)")

    header.pop("_line", None)
    ad_hits = header.pop("ad_hits")
    header["ad"] = "AD" if len(ad_hits) == 2 else (next(iter(ad_hits)) if ad_hits else "")
    header["effect_icon_ja"] = "|".join(header.pop("effect_icons"))
    return header, consumed


def parse_card_page(html: str, category_ja: str, number: str) -> dict:
    m = BLOCK_RE.search(html)
    if not m:
        raise ValueError("找不到卡片資料區塊(<blockquote><div>...<hr/><div>...</div></blockquote>)")
    main_raw, flavor_raw = m.group(1), m.group(2)
    type_ = CATEGORY_TO_TYPE.get(category_ja, category_ja)

    main_lines = [x for x in BR_RE.split(main_raw) if strip_tags(x)]
    main_lines = main_lines[1:]  # 第一行是「卡號　名稱」,略去

    header, consumed = parse_header(main_lines, type_, number)
    result: dict = {"related_mamodo_ja": "", "effect_ja": "",
                     "raw_header_lines": "|".join(strip_tags(x) for x in main_lines[:consumed]),
                     **header}

    body_lines = main_lines[consumed:]
    tail = SPELL_TAIL_RE.search(body_lines[-1]) if body_lines else None
    if type_ == "spell" and tail:
        result["related_mamodo_ja"] = tail.group(1).strip()
        body_lines = body_lines[:-1]
    result["effect_ja"] = "".join(strip_tags(x) for x in body_lines)

    flavor_lines = [strip_tags(x) for x in BR_RE.split(flavor_raw) if strip_tags(x)]
    result["flavor_ja"] = flavor_lines[0] if flavor_lines else ""
    result["sets_ja"] = "|".join(flavor_lines[1:])
    return result


def main() -> None:
    sources = sys.argv[1:]
    if not sources:
        print(__doc__)
        raise SystemExit(1)

    rows: dict[str, dict] = {}
    if OUT.exists():
        with OUT.open(encoding="utf-8-sig", newline="") as f:
            rows = {row["number"]: row for row in csv.DictReader(f)}

    entries: dict[str, tuple[str, str, str]] = {}  # 卡號 → (url, name, category)
    for src in sources:
        html = fetch(src)
        for number, url, name, category in parse_product_page(html, src):
            entries[number] = (url, name, category)
    print(f"從 {len(sources)} 個產品頁取得 {len(entries)} 張卡(去重後)")

    def flush() -> None:
        with OUT.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES)
            w.writeheader()
            for number in sorted(rows):
                w.writerow(rows[number])

    ok = skip = fail = 0
    failures: list[str] = []
    for number, (url, name, category) in sorted(entries.items()):
        if number in rows:
            skip += 1
            continue
        try:
            html = fetch(url)
            parsed = parse_card_page(html, category, number)
            rows[number] = {
                "number": number, "type": CATEGORY_TO_TYPE.get(category, category),
                "name_ja": name, "url": url, **parsed,
            }
            flush()
            ok += 1
            print(f"✓ {number} {name}")
            if url.startswith("http"):
                time.sleep(0.5)  # 避免限流
        except Exception as exc:  # noqa: BLE001 — 記錄後繼續
            failures.append(f"{number}\t{url}\t{exc}")
            fail += 1
            print(f"✗ {number}: {exc}", file=sys.stderr)

    if failures:
        (ROOT / "data/cards_ja_failed.txt").write_text("\n".join(failures), encoding="utf-8")
    print(f"完成: 新抓 {ok}、已存在跳過 {skip}、失敗 {fail}"
          + ("(清單見 data/cards_ja_failed.txt)" if failures else ""))


if __name__ == "__main__":
    main()
