## 1. 先寫測試

- [x] 1.1 引擎測試:魔物、魔本頁、棄牌區、保護、受傷順序、放出魔物的選項帶 `zone` / `player` / 定位欄位;`value` 不變。確認修改前失敗
- [x] 1.2 瀏覽器測試:決策時沒有蓋住畫面的對話框,行動欄顯示標題、來源與純選項按鈕;場上目標發光,點了開放大檢視、按選擇送出;魔本網格標頁碼、同一張卡兩頁可分辨;對手魔本只顯示選項頁的卡面;棄牌區選擇;決策期間仍可查閱魔本與棄牌區;非決策者看不到選擇按鈕。確認修改前失敗

## 2. 引擎

- [x] 2.1 `slot_option` / `page_option` / `discard_option`(design D1)
- [x] 2.2 `tree.py` 各選項規格、`engine.py` 的保護、受傷順序、改傷害目標、放出魔物改用建立函式

## 3. 前端

- [x] 3.1 行動欄決策區塊(design D2),i18n 四種語言(簡中由工具產生)
- [x] 3.2 `pickTargets()`、場上與翻開頁的 `.pickable`、放大檢視的「選擇」(design D3)
- [x] 3.3 魔本網格與棄牌區的選擇模式(design D3、D4)
- [x] 3.4 更新依賴舊對話框的測試
- [x] 3.5 截圖確認桌面與手機

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `battle-ui`、`game-engine` 主 spec
- [x] 4.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 新增決策互動一節;`game-engine/design.md`「中途決策」補選項的位置欄位
- [x] 4.3 Update capability map(若責任描述需要)
- [x] 4.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
