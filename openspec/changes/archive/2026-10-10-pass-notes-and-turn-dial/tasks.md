## 1. 快照

- [x] 1.1 先寫測試確認修改前失敗:非戰鬥中 pass 後三種視角的快照 `consecutive_passes` 為 1;行動後為 0;雙方 pass 進入下一回合後為 0;戰鬥效果步驟 pass 後不增加
- [x] 1.2 `views.py` 快照加 `consecutive_passes`(design D1);1.1 全過

## 2. 行動欄附註

- [x] 2.1 先寫瀏覽器測試確認修改前失敗:自己回合非戰鬥中 Pass 附註「不進行自己回合行動」、對手回合「不進行對手回合行動」、戰鬥效果步驟「不使用戰鬥中效果」、迎戰按鈕「迎戰」與附註「或選擇非戰鬥行動而不迎戰」、「不防禦」沒有附註
- [x] 2.2 `addBtn` 支援附註、i18n(design D2,簡中以工具產生)、CSS;2.1 與 `tests/test_i18n_languages.py` 全過

## 3. 回合轉盤

- [x] 3.1 先寫瀏覽器測試確認修改前失敗:
  - 轉盤指向回合玩家的區塊,區塊名稱旁沒有回合玩家徽章;
  - pass 一次後角度為原位 +45°,對手行動後轉回;
  - 雙方 pass 換到對手回合後角度為原位 +180° 且是由 45° 增加上去(不反向);
  - 戰鬥效果步驟 pass 不傾斜,舞台展開時轉盤在右端,中心顯示「戰鬥中」;
  - 觀戰者也看得到轉盤;
  - 對局結束後不顯示
- [x] 3.2 實作 `renderTurnDial`、移除 `.turn-marker` 徽章(design D3–D5),修改 `tests/test_timing_ui.py` 依徽章的斷言;3.1 與 `pytest tests/test_timing_ui.py tests/test_book_browse_ui.py` 全過
- [x] 3.3 依使用者回饋改版:轉盤放大並移到行動欄左端取代摘要文字,外圈與旋轉箭頭固定、只有「回合玩家」標籤繞行,中心綠底「非戰鬥」/ 紅底「戰鬥中」,加「行動玩家」箭頭;日文統一「非バトル」;測試同步更新
- [x] 3.4 使用者在瀏覽器實際操作確認(含窄螢幕、英日文)

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `battle-ui`、`battle-api` 主 spec
- [x] 4.2 Reconcile affected capability design:`battle-ui/design.md`「回合與時機指示」改寫回合玩家記號為轉盤(角度規則、位置)並加行動欄附註;`battle-api/design.md`「快照中的公開脈絡」加 `consecutive_passes`
- [x] 4.3 確認 capability map 不需更新;`openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
