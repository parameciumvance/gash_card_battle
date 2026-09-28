## 1. 魔力勝負明細(引擎)

- [x] 1.1 先寫測試:
  - 以 NPC 自我對戰收集大量戰鬥,記下改寫前每場的雙方合計,作為改寫後比對的基準。
  - spec 情境:明細加總等於合計、P-007 待命加成的來源、無效化的來源、不防禦時明細為空、P-011 魔力視為 0。
  - 確認情境測試在改寫前失敗。
- [x] 1.2 `power_breakdown` / `side_breakdown`(design D1),`slot_power` / `_side_total` 改由明細推得
- [x] 1.3 記下術加成與無效化的來源(design D2)
- [x] 1.4 `showdown` 事件加入雙方明細(design D3);比對改寫前後合計完全相同,全部測試通過

## 2. 擲幣詢問的公開脈絡

- [x] 2.1 `PendingChoice.info`;M-012(`coin_confirm`)、M-019(`opp_coin_redo`)、E-011(`paid_reflip`)填入目前結果(design D4)
- [x] 2.2 測試:三種詢問的 `info.results` 與實際擲出結果一致,重擲後更新

## 3. 快照

- [x] 3.1 `views.snapshot`:pending 附 `info`;`battle` 附雙方明細;新增 `effects`(design D5)
- [x] 3.2 盤點所有 standby / modifier 種類,決定是否有純內部種類需排除,記入 design D5
- [x] 3.3 測試 `battle-api`「決策與戰鬥的公開脈絡」各情境:對所有視角相同、不含內部資料、已消耗的待命不列、戰鬥明細加總等於合計

## 4. 前端

- [x] 4.1 擲幣對話框逐枚顯示結果、重擲按鈕帶枚次與結果;非決策者的等待提示附結果
- [x] 4.2 明細檢視:行動記錄的魔力勝負條目與舞台合計可點,列出各項與勝負,來源卡名可點
- [x] 4.3 頂欄「作用中效果(N)」按鈕與清單:依擁有者分組、說明與時效的 i18n、退回效果文
- [x] 4.4 i18n:明細種類、效果種類與限制旗標、時效;測試檢查程式中出現的 standby / modifier 種類都有說明文字
- [x] 4.5 瀏覽器測試:`battle-ui` 三項新需求的情境

## 5. Reconciliation 與歸檔(指南 §13)

- [x] 5.1 同步 delta spec 回 `game-engine`、`battle-api`、`battle-ui` 主 spec
- [x] 5.2 Reconcile affected capability design and rationale:
  - `game-engine/design.md` 記錄「合計由明細推得」與明細項目。
  - `battle-api/design.md`(新):快照公開欄位與私有資料的界線(`pending.info` 與 `data`、作用中效果只送整理過的欄位)。
- [x] 5.3 Update capability map:`battle-api` 的 design 覆蓋改為 Partial
- [x] 5.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
