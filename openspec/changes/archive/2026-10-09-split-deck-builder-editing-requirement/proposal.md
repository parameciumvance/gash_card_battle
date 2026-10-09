## Why

`deck-builder-card-info` 把卡池篩選(對應魔物「無」、選事件時暫停)、卡號與中級 / 上級顯示、詳情按鈕都加進「對頁編輯」這一條需求的說明,使說明超過 500 字,`openspec validate --strict` 對 `deck-builder` 失敗。一條需求混了多個行為,也不好查閱與引用。

## What Changes

- 「對頁編輯」的說明還原為原本的範圍(對頁網格、卡池瀏覽、寬窄螢幕版面、放卡 / 移除 / 互換、允許空頁與違規)。它的 11 個情境全部保留(OpenSpec 的 MODIFIED 不能移走既有情境),其中 5 個描述的正是下列行為。
- 新增三條需求,各自承接一個行為的說明,並各附不重複的情境(都是目前已實作、已有測試的行為):
  - 「卡池篩選的對應魔物」:「無」只篩指令術;選事件時暫停。
  - 「構築器顯示卡號與中級 / 上級」。
  - 「構築器的卡片詳情」。
- 純規格整理,行為與程式都不變。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `deck-builder`:拆分「對頁編輯」需求為四條,行為不變。

## Impact

- 只改 `openspec/specs/deck-builder/spec.md`(經 delta 同步),程式不變。新需求的情境若缺直接對應的測試,在 `tests/test_builder_card_info_ui.py` 補上。
