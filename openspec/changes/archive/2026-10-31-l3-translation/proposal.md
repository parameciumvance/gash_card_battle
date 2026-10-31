## Why

l12-translation 把第 1、2 彈的繁中改成日文直譯，第 3 彈之後(`sets` 不含 `level-1` / `level-2`,共 197 張)只統一了戰術卡的固定句型。2026-10-31 的 explore 逐張對照這 197 張的繁中與 `effect_ja`,發現兩類問題:
- 意思有出入：主詞改變(S-084 / S-100「此戰術卡不可被防禦」)、多了日文沒有的措辭(S-076 / S-077「直接」、Ex-047「必須」、M-058 的「時」)、漏掉措辭(S-067 / S-097 的「できる」、Ex-022 / Ex-027 / PR-007 的「そうしたなら」條件、Ex-003「好きな」)、句子重排(P-032 / S-074、S-084)等。
- 同一個日文句型和第 1、2 彈的直譯用了不同譯法(「此事件卡僅於」/「此效果在」、「套用」/「使用」、「1頁」/「1張」),卡名漏掉「」。

使用者決定：兩類都修正，英文也逐張核對。對照中沒有發現實作差異。

## What Changes

- 197 張的 `data/cards.zh-TW.json` `effect`:
  - 有出入的改成直譯;
  - 固定句型統一成第 1、2 彈的譯法(design D2);
  - 「」括起的卡名、戰術名保留「」。
  - 效果名(`attr`)、卡名與戰術名不改(代理版譯名)。
- 同一批卡的 `data/cards.en.json`:逐張核對 `effect`,有偏差的改成直譯。`name` / `attr` 不改。
- `data/cards.zh-CN.json`:由 `tools/build_zh_cn.py` 重新產生。
- 只改顯示文字，不改遊戲行為。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:新增「效果文的固定譯法」需求，規定同一個日文句型在所有卡片使用同一種繁中譯法。

## Impact

- 資料：`data/cards.zh-TW.json`、`data/cards.en.json`、`data/cards.zh-CN.json`(由工具產生)。
- 測試:`tests/test_i18n_languages.py` 等;寫死舊譯文的測試依新譯文更新。
- 前端顯示的卡片文字會改變。
