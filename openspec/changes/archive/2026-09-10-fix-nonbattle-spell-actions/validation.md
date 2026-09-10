# 驗證紀錄

- `python -m pytest tests/test_nonbattle_ui.py tests/test_views.py tests/test_api.py tests/test_cheat_editor.py tests/test_cards.py tests/test_level2.py -q`：141 passed。
- `node --check frontend/app.js`、`git diff --check`：通過。
- `openspec validate fix-nonbattle-spell-actions --strict`：通過。

## 檢查範圍

- 五張非對戰術皆顯示「使用」，送出 use_book_card 的玩家／頁碼正確，詳情隨提交關閉。
- S-026 使用真實本機 API：book_card_used 與 coin_flipped 事件存在，沒有 battle／battle_in；重新載入後使用紀錄恢復，另一頁同卡號仍禁用。
- MP 不足、缺少魔物、同卡號已使用、A/D/AD 時機與最新快照刷新；battle、battle_in、pending、非持有者及無行動權不提供操作。
- 一般術攻擊、目前卡池的指示術防禦與多魔物選擇、事件卡「使用」及每回合限制；既有金手指瀏覽器回歸。
- 持有者使用紀錄初始值、排序、使用後更新、引擎回合重置，及本人／對手／觀戰／本機快照可見性。
- 詳情卡號以 14px 獨立文字顯示，檢查 1280、390、320px 版面及缺圖卡背；純展示詳情不帶行動按鈕。
- 卡號依最新偏好改為純卡號、一般字重，位於詳情內容最底下；版面測試驗證其在效果文下方且為最後一個元素。

瀏覽器測試使用既有 Playwright 可選測試環境及隔離的本機伺服器。效果測試使用真實 API；其他卡片的操作分支與禁用情境以瀏覽器狀態配置及請求攔截驗證，並由既有引擎測試涵蓋效果裁決。

- 卡號改為底部純文字及一般字重後，重跑 `python -m pytest tests/test_nonbattle_ui.py -q`：14 passed。
