# Tasks

- [x] 1.1 瀏覽器測試:接回時網路失敗 / 代理回 502 HTML → 身分保留、顯示重試畫面,恢復後自動進入對局;重試中「回首頁」保留身分、首頁可返回;房間不存在照舊刪除回首頁;首頁清單查詢網路失敗時保留記錄;WebSocket 定時送心跳。確認修改前失敗
- [x] 1.2 `roomGone` 與 `api` 的非 JSON 回應(D1)
- [x] 1.3 接回的重試畫面(D2),四語
- [x] 1.4 首頁清單只在 D1 錯誤時移除(D3)
- [x] 1.5 WebSocket 心跳(D4)
- [x] 1.6 快速測試組(1520 passed)與全部非 slow 瀏覽器測試(378 passed)通過;`openspec validate fix-reconnect --strict`
- [x] 1.7 本機實際操作抽查(使用者)
- [x] 1.8 同步 battle-ui 主 spec 與 design
