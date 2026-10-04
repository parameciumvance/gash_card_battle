## 1. 先寫測試

- [x] 1.1 新增 `tests/test_landing_ui.py`,涵蓋 `battle-ui`「首頁入口」新情境:首頁只有五個入口(順序、沒有輸入欄與選單)、進入設定頁並返回、切換建立與加入、經連結加入(預填房號、尚未加入、加入後雙方進入對局)、記住上次的選擇(重新整理與構築器返回後)、記住的牌組已失效回缺省;「玩家暱稱」的暱稱記憶與本機測試不預填。確認修改前失敗
- [x] 1.2 改 `tests/test_npc_ui.py`、`tests/test_rules_ui.py` 點首頁入口的步驟,改為「點入口 → 在設定頁操作 → 開始」

## 2. 首頁與設定頁

- [x] 2.1 `index.html`:首頁入口改為按鈕(名稱 + 簡介),順序 NPC 對戰 / 與朋友對戰 / 本機測試 / 牌組構築 / 規則;新增 `#setup` 視圖(返回、標題、三個面板),欄位依 design D3 沿用與合併 id
- [x] 2.2 `app.js`:`show()` 加入 `setup`;`openSetup(mode)`、返回;入口按鈕行為;`createRoom()` / `joinRoom()` 改讀 `name-friend` / `deck-friend`
- [x] 2.3 與朋友對戰的建立 / 加入切換:模式說明、計時 / 房號欄、送出按鈕文字;切換不清除已填的值(design D4)
- [x] 2.4 加入連結開啟加入模式並預填房號;返回時網址換回 `/`(design D5)
- [x] 2.5 記住選擇:`gash-setup` 在選單變更時存,`renderLanding()` 重新產生選單後還原,不可選時回缺省;加入連結不覆蓋記住的模式;localStorage 不可用時用缺省(design D6、D7)
- [x] 2.6 `style.css`:入口按鈕、設定頁、建立 / 加入切換、窄螢幕;大寫顯示只套在房號欄
- [x] 2.7 i18n:`ui.landing.friend`、`ui.landing.friend_desc`、`ui.setup.back`(design D9)
- [x] 2.8 截圖確認桌面與手機
- [x] 2.9 加入失敗時留在設定頁(design D4);順帶修正頂欄「規則」按鈕漏掉的樣式(design D9)

## 3. 文件

- [x] 3.1 README 中首頁入口的說明改為五個入口與設定頁

## 4. Reconciliation 與歸檔(指南 §13)

- [ ] 4.1 同步 delta spec 回 `battle-ui` 主 spec
- [ ] 4.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 補「首頁與設定頁」(視圖結構、記住選擇的時機與還原、加入連結不自動加入的理由、本機測試暱稱不預填、不動瀏覽器歷史)
- [ ] 4.3 Update capability map(`battle-ui` 責任的「首頁入口」改為「首頁與設定頁」)
- [ ] 4.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
