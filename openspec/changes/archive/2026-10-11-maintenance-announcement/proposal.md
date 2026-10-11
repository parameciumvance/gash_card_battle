## Why

維護(更新、重啟)會讓進行中的對局消失,需要事先告知玩家;目前只有新版上線後才跳出的「更新內容」,沒有事先發布公告的方式。

## What Changes

- 伺服器讀取卡圖 volume 中的公告檔 `announcement.json`(`id`、各語言的 `message`、可選的 `until`),以 `GET /api/announcement` 提供;每次請求即時讀檔,編輯檔案即可發布或撤下,不需重新部署或重啟。過了 `until` 不再提供;檔案不存在或格式錯誤時視為沒有公告。
- 前端在頂欄下方顯示公告橫幅(首頁、設定頁、對局畫面都有),依語言設定選訊息;載入時與之後每 2 分鐘查詢,對戰中的玩家也會看到新公告。可關閉,同一則(依 `id`)關閉後不再出現。
- README 說明如何發布與撤下公告。
- 不在維護前擋住新房間(使用者決定先不做)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-api`:新增「維護公告」。
- `battle-ui`:新增「維護公告橫幅」。

## Impact

- `src/gash/api/app.py`(端點)、`src/gash/paths.py`(公告檔位置)。
- `frontend/index.html`、`app.js`、`style.css`、i18n(關閉按鈕)。
- `README.md`。
- 測試:API、瀏覽器。
