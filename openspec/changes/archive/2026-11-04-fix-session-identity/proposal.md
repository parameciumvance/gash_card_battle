# Proposal

## Why

使用者回報(v1.3.0):A 建立房間與 B 對戰中,A 重新整理後身分變成 B。同一個瀏覽器開兩個分頁可重現。原因:對局身分(房號、座位、token)只存在 `localStorage` 的 `gash-room-<房號>`,同一個瀏覽器的分頁共用;B 在另一個分頁加入同一房時蓋掉 A 的記錄,A 重新整理時讀到 B 的身分。

跨裝置的回報(ChatGPT 代理與使用者對戰)無法重現:不同瀏覽器的 `localStorage` 不共用,伺服器依 token 判斷身分。推測代理的瀏覽器開過不只一個分頁(例如預覽加入連結),屬同一原因;未確認。

## What Changes

- 每個分頁的對局身分另存在 `sessionStorage`(分頁各自一份、重新整理後仍在),重新整理(`?room=`)時優先使用;沒有時(新分頁、首頁「返回進行中的對局」)照舊使用瀏覽器記得的 `localStorage` 記錄。
- 離開房間時清除分頁的身分。
- 從 v1.3.0 修正(hotfix),之後合併回 main。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「分頁的對局身分」。

## Impact

- `frontend/app.js`(`saveSession` / `loadSession` / `leaveRoom`)。
- 瀏覽器測試 `tests/test_session_identity_ui.py`。
