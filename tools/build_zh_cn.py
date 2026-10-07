"""由繁體中文產生簡體中文(card-data「簡體中文卡片文字」、battle-ui「語言選擇」)。

簡中檔全部由對應的繁中檔轉換,不手動編輯;改了繁中就重跑本工具:

- `frontend/i18n/zh-TW.json`       → `frontend/i18n/zh-CN.json`
- `frontend/i18n/rules.zh-TW.json` → `frontend/i18n/rules.zh-CN.json`
- `frontend/i18n/releases.zh-TW.json` → `frontend/i18n/releases.zh-CN.json`
- `data/cards.zh-TW.json`          → `data/cards.zh-CN.json`

轉換用 OpenCC `tw2sp`(字形 + 大陸用語),再以 `TERMS` 保留遊戲術語、修正不適合的詞語轉換。
角色名、卡名、術名只轉字形,沿用繁中譯名。只轉換字串值;`name_ja`(日文原名)與 `app.title`(網站名稱,專有名稱,各語言相同)不轉換。

用法: python tools/build_zh_cn.py(需要 dev 依賴 opencc-python-reimplemented)
"""

from __future__ import annotations

import json
from pathlib import Path

import opencc

ROOT = Path(__file__).resolve().parent.parent
FILES = {
    ROOT / "frontend/i18n/zh-TW.json": ROOT / "frontend/i18n/zh-CN.json",
    ROOT / "frontend/i18n/rules.zh-TW.json": ROOT / "frontend/i18n/rules.zh-CN.json",
    ROOT / "frontend/i18n/releases.zh-TW.json": ROOT / "frontend/i18n/releases.zh-CN.json",
    ROOT / "data/cards.zh-TW.json": ROOT / "data/cards.zh-CN.json",
}
SKIP_KEYS = {"name_ja", "app.title"}

# 繁中詞 → 簡中寫法。不套用 tw2sp 的詞語轉換,改用這裡的寫法
TERMS = {
    "宣告": "宣告",      # 遊戲術語,不轉為「声明」
    "進階": "进阶",      # 「進階規則」不可轉為「高端规则」
    "顯示": "显示",      # 避免「即可顯示卡圖」被斷詞轉成「可显卡图」
    "複製": "复制",      # 大陸介面用「复制」,不轉為「拷贝」
    "文字": "文字",      # 「文字標示」不轉為「文本标示」
    "預設": "默认",      # tw2sp 會轉成「缺省」
    "帳號": "账号",      # 字形轉換只得到「帐号」
}
_PLACEHOLDER = 0xE000    # 私用區字元,OpenCC 不會動


def _converter():
    tw2sp = opencc.OpenCC("tw2sp")
    marks = {term: chr(_PLACEHOLDER + i) for i, term in enumerate(TERMS)}

    def convert(text: str) -> str:
        for term, mark in marks.items():
            text = text.replace(term, mark)
        text = tw2sp.convert(text)
        for term, mark in marks.items():
            text = text.replace(mark, TERMS[term])
        return text
    return convert


def _walk(value, convert, key=None):
    if key in SKIP_KEYS:
        return value
    if isinstance(value, str):
        return convert(value)
    if isinstance(value, dict):
        return {k: _walk(v, convert, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_walk(v, convert) for v in value]
    return value


def build() -> dict[Path, object]:
    """{輸出路徑: 轉換後的資料}。"""
    convert = _converter()
    return {out: _walk(json.loads(src.read_text(encoding="utf-8")), convert) for src, out in FILES.items()}


def main() -> None:
    for path, data in build().items():
        indent = 1 if path.parent.name == "data" else 2   # 與對應的繁中檔一致
        path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
