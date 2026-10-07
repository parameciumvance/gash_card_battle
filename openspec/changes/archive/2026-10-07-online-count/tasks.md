## 1. 伺服器計數與端點

- [x] 1.1 `tests/test_online_count.py`(online-room「對戰中人數」各情境):玩家與觀戰者計入、同座位多條連線只算一人、NPC 不計入、等待對手的建房者計入、沒有連線的房間不計入、斷線後減少、回應只有 `count`;確認實作前失敗
- [x] 1.2 `RoomStore.online_count()`(design D1)與 `GET /api/online`(design D2);1.1 通過

## 2. 首頁顯示

- [x] 2.1 瀏覽器測試(battle-ui「首頁對戰中人數」各情境):以 route 控制回應,驗證人數文字、0 人文字、30 秒更新、回到首頁重新取得、離開首頁不再請求、隱藏時暫停且回來立即更新、失敗不顯示、日文;確認實作前失敗
- [x] 2.2 i18n 字典 `ui.online.count`、`ui.online.none`(繁中、英、日手寫,簡中以 `tools/build_zh_cn.py` 產生);`test_i18n_languages` 通過
- [x] 2.3 `index.html` / `app.js` / `style.css`:`#landing-online`、進入首頁抓取與 30 秒更新、離開首頁與頁面隱藏時停止、失敗隱藏、只採用最後一次請求(design D3、D4);2.1 通過
- [x] 2.4 截圖確認桌面與手機的首頁

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `online-room`、`battle-ui` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`online-room/design.md` 新增「對戰中人數」(計數規則、端點不含房間資訊、行為決定與理由);`battle-ui/design.md`「首頁與設定頁」補人數行的位置、更新時機與標籤理由
- [x] 3.3 capability map:`online-room` 責任補上對戰中人數
- [x] 3.4 `openspec validate --all --strict`、全部測試通過
