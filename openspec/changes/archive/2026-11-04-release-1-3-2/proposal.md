# Proposal

## Why

main 上 v1.3.1 之後的修改(card-action-menu、card-detail-panel)還沒發布,其中棄牌區視窗無法關閉(有卡時只能點卡進入放大檢視)影響體驗。使用者決定不另拆修正線,直接從 main 一起發布為 v1.3.2。

## What Changes

- 新增 v1.3.2 的更新內容(四語,日期 2026-11-04,沒有標題):卡片行動選單、寬螢幕的卡片詳情面板、棄牌區視窗可以關閉。
- 沒有規格變更:三項行為已由 card-action-menu、card-detail-panel 寫進 battle-ui;跳出方式依既有「維修版的跳出」(沒讀過 v1.3.0 的玩家依序看到 v1.3.0、v1.3.1、v1.3.2)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

(無)

## Impact

- `frontend/i18n/releases.*.json`。
