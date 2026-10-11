## 1. S-043 分裂

- [x] 1.1 先寫測試確認修改前失敗:魔書剛好 2 張 M-024 時,選第一張後只放出一張並停在第二次選擇(選項只有剩下那頁),選了才放出;更新 `test_level2.py` 的 `test_s043_split_complete_into_two_doubles`(原本預期自動)
- [x] 1.2 S-043 第二次 `Choose` 加 `auto_single=False`(design D1);`pytest` 全過

## 2. 選擇提示

- [x] 2.1 先寫瀏覽器測試確認修改前失敗:有魔書決策目標時網格顯示決策標題與來源卡名;棄牌區決策顯示標題與來源卡;單純查閱不顯示
- [x] 2.2 `pickHint`、網格 `#book-review-hint`、`showDiscard` 的 notes / 來源卡(design D2);2.1 與既有瀏覽器測試全過
- [x] 2.3 自動開啟等演出播完、棄牌飛向棄牌區、`card_discarded` 加 `slot`、自訂屬性改 `setProperty`(design D3–D5):先寫測試(引擎事件帶 slot;瀏覽器:放卡後至少 450ms 才自動開啟、搭檔被棄時出現飛向棄牌區的複製品並播完移除),修改前失敗;實作後全過並截圖確認
- [x] 2.4 同一批事件到兩次時仍等演出播完(`pickOpenNotBefore`):先寫重現測試(連送兩次同一批,開啟時間仍 ≥ 450ms),修改前失敗,修改後通過
- [x] 2.5 使用者在瀏覽器實際操作確認

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `card-effects`、`effect-tree`、`battle-ui` 主 spec
- [x] 3.2 `battle-ui/design.md`「決策互動」補選擇提示與自動開啟延後、「事件動畫管線」補棄牌演出與自訂屬性的注意事項;`game-engine/design.md` 記 `card_discarded.slot`;`effect-tree/design.md` 的 `auto_single` 說明補 S-043
- [x] 3.3 確認 capability map 不需更新;`openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
