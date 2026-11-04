# Proposal

## Why

v1.3.1 是 v1.3.0 的維修版(fix-session-identity、fix-reconnect、forfeit-and-absence)。使用者要求:公告中維修版 1.3.1 顯示在功能版 1.3.0 之下,如果 1.3.0 還沒讀過的話。目前跳出的介紹只顯示最新一版,沒讀過 1.3.0 的玩家會錯過功能版的內容。

## What Changes

- 跳出的介紹改為最新一版所屬版本線中尚未確認的版本,由舊到新(功能版在上、維修版在下);功能版已確認時只顯示維修版;更早的版本線不一起跳出。
- 新增 v1.3.1 的更新內容(四語,日期 2026-11-04,沒有標題):棄權、對手沒有回應的提示、雙方沒有回應時關閉房間、兩個分頁身分、連線不穩回不了對局、閒置斷線。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「維修版的跳出」;修改「更新內容」(跳出的版本改依「維修版的跳出」)。

## Impact

- `frontend/app.js`(`maybeShowRelease`、`popupReleases`)、`frontend/i18n/releases.*.json`、`tests/test_release_notes_ui.py`。
