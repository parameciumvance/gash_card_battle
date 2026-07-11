# Tasks: in-use-card-reveal

## 1. 後端揭露

- [x] 1.1 `views.py` `_player_view`:計算玩家 p 的使用中頁集合(battle_in 攻方頁、battle 攻方 attack_page/防方 defense_page),例外送出 `{page, card, cost?, in_use: true}`(持有者視角亦附 in_use)
- [x] 1.2 API/單元測試:宣告中對手與觀戰視角可見該頁(歸屬正確)、其餘頁仍保密、戰鬥結束恢復、無術攻擊(無頁)不揭露;既有資訊隱藏測試調整

## 2. 前端呈現

- [x] 2.1 `in_use` 頁高亮樣式(發光描邊);對手使用中頁經 `openPageEl` 自然渲染卡面,確認檢視面板對非控制者零按鈕
- [x] 2.2 記錄卡名可點:appendLog 後處理——取事件卡號欄位,以 splitText 包 `.card-ref` span(click → zoom 純展示);找不到片段退回純文字
- [x] 2.3 對決舞台攻防術名以同一 helper 可點

## 3. 驗證

- [x] 3.1 E2E(線上雙視角):宣告攻擊後對手端該頁翻正可點(無按鈕)、防禦術同、戰鬥結束恢復卡背;記錄卡名點開檢視;手機視窗同驗
- [x] 3.2 全套回歸(pytest + 既有 E2E)
