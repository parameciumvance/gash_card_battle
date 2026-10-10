## 1. 引擎事件

- [x] 1.1 先寫測試確認修改前失敗:戰術攻防時 `showdown` 事件含攻擊魔物、攻擊戰術、防禦魔物、防禦戰術卡號;不防禦時防禦兩欄為空;M-027 無戰術攻擊時攻擊戰術為空、攻擊魔物為 M-027;疊放魔物為最上面的卡
- [x] 1.2 `_resolve_showdown` 加欄位(design D1);1.1 與 `tests/test_battle_info.py`、`tests/test_battle_start_characterization.py` 全過(期望檔若含 showdown 事件需說明並更新)

## 2. 對峙演出

- [x] 2.1 先寫瀏覽器測試確認修改前失敗(以本機模式觸發戰鬥,演出期間檢查 DOM):
  - 上下兩組各含對應的魔物與戰術卡,屬於上方玩家的組在上;中間有 VS;
  - 合計數字最終等於事件值;
  - 攻擊成功時中央為「攻擊成功」、勝方 / 敗方有對應 class;
  - 不防禦時戰術位置為「不防禦」;
  - 同值顯示「防禦成功」與「同值・防禦方勝」;
  - 點擊後演出立即消失;
  - 聚焦速度「快」時總長約 1.2 秒;
  - 動畫關閉時不出現
- [x] 2.2 實作 `anim.js` 的對峙演出與依類型的逾時(design D2–D4)、CSS(含窄螢幕)、i18n(design D5,簡中以工具產生);2.1 與 `pytest tests/test_spotlight_ui.py tests/test_i18n_languages.py tests/test_battle_info_ui.py` 全過
- [x] 2.3 截圖確認寬螢幕、手機與英日文的版面
- [x] 2.4 追加傷害能量演出(design D6):先寫瀏覽器測試(不保護後能量飛向防禦方魔書並在該處爆光;決定保護前沒有能量;防禦成功沒有能量),實作後全過
- [x] 2.5 回合轉盤改橢圓、降低高度(design D7),`tests/test_turn_dial_ui.py`、`tests/test_timing_ui.py` 全過並截圖確認寬螢幕、手機、英文
- [x] 2.6 箭頭只朝上下;保護演出(design D8):先寫引擎測試(`protected` 帶對象,修改前失敗)與瀏覽器測試(保護者移到魔書前、能量打在它身上、回原位後顯示負傷),實作後全過並截圖確認
- [x] 2.7 使用者在瀏覽器實際操作確認

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `battle-ui`、`game-engine` 主 spec
- [x] 3.2 Reconcile affected capability design:`battle-ui/design.md`「事件動畫管線」改寫魔力對決演出(版面、節奏、逾時)與傷害能量,「回合與時機指示」的轉盤改為橢圓的做法;`game-engine/design.md` 記錄 `showdown` 事件的對峙欄位
- [x] 3.3 確認 capability map 不需更新;`openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
