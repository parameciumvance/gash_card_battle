## Context

- 引擎:非戰鬥中 `st.consecutive_passes` 在 pass 時加 1,達 2 進入結束階段;任何行動(含宣告攻擊)、戰鬥結束、新回合開始都歸零。戰鬥效果步驟另用 `battle.effect_passes`。快照目前沒有送任何一個。
- 前端:回合玩家是 `renderPlayerZone` 在區塊名稱旁加的 `.turn-marker` 徽章(`ui.turn_marker`);中線 `#battle-stage` 內有 `#timing-track`,戰鬥開始確認與戰鬥中展開為 `.open` 並顯示 `#stage-content`。
- `renderActionBar` 的 Pass 用 `ui.pass`,迎戰用 `ui.allow_battle`(「迎戰(戰鬥開始)」)。
- 上方區塊的玩家是 `topPlayerIndex()`,下方是另一位。

## Goals / Non-Goals

**Goals:** Pass / 迎戰按鈕附註;回合轉盤取代回合玩家徽章,以傾斜提示「再 pass 就換人」。

**Non-Goals:** 不改引擎規則;戰鬥中的 pass 不反映在轉盤;「不防禦」不加附註;不改行動權外框與「行動中」標籤。

## Decisions

### D1:快照欄位

`views.py` 頂層加 `consecutive_passes`(整數),所有視角相同;這是雙方都看得到的公開行動結果。`effect_passes` 不送(轉盤不用,見 D4)。

### D2:按鈕附註

- `addBtn` 增加可選的附註參數,有附註時按鈕內放兩個 span:`.btn-label`(上行)與 `.btn-note`(下行,較小、淡色)。
- i18n 新增:
  - `ui.pass_note.own_turn`:「不進行自己回合行動」;
  - `ui.pass_note.opp_turn`:「不進行對手回合行動」;
  - `ui.pass_note.battle`:「不使用戰鬥中效果」;
  - `ui.allow_battle_note`:「或選擇非戰鬥行動而不迎戰」。
- `ui.allow_battle` 改為「迎戰」(原括號內的「戰鬥開始」由附註取代)。
- 加到 zh-TW / en / ja,簡中以 `tools/build_zh_cn.py` 產生。
- Pass 的附註依 `timing` 與 `awaited === S.turn_player` 選擇:`effects` 用 battle,非戰鬥中依是否回合玩家選 own / opp。

### D2b:行動欄配色

行動欄底色是深色(輪到自己時深綠),所以:行動選項按鈕改淺色(一般為淺藍白底深字,主要選項為淺橘底深棕字);「展開提示」是虛線外框、透明底,和行動選項區分;「回合玩家」「行動玩家」標籤外的三角箭頭用亮金色(`--glow`)。範圍只限行動欄,放大檢視與對話框的按鈕不變。

### D3:轉盤結構與位置

- 位置:行動欄左端,取代摘要文字。演進經過:最初提議放中線正中央;實作時截圖發現中央上下緊貼魔物欄、會蓋到卡,經確認改放中線右端;使用者看過後認為太小、旋轉箭頭不清楚、文字被覆蓋、英日文出框,改為放大並移到行動欄,取代摘要文字。
- 行動欄拆成常駐的 `#turn-cluster` 與每次重建的 `#action-main`:轉盤元素不能隨 `renderActionBar` 清空重建,否則沒有旋轉動畫。`mine` 的醒目標示仍加在 `#action-bar`。
- `#turn-dial` 由三層組成:
  - `.dial-ring`:外圈與順時鐘旋轉箭頭(SVG),固定不動。箭頭分左右兩段弧(類似循環符號),避開「回合玩家」標籤會停留的上、下、左下、右上四個位置;放在正上方時,輪到上方玩家的回合會被標籤蓋住;
  - `.dial-rotor`:與外圈同大小、以 `--dial-angle` 旋轉,上面的 `.dial-tab` 是跨在外圈下緣、三角形朝外的「回合玩家」標籤;標籤文字反向旋轉維持正向;
  - `.dial-center`:中心圓,不旋轉,`data-phase` 決定底色。
- 中心文字(`ui.turn_dial.<phase>`)依 `currentTiming()`:start →「開始階段」;nonbattle → 綠底「非戰鬥」;battle_in / defense / effects → 紅底「戰鬥中」;end →「結束階段」。英文為 Start / No BATTLE / BATTLE / End,日文為 スタート / 非バトル / バトル中 / エンド,都要放得進中心圓。使用者的圖只有非戰鬥與戰鬥中;開始、結束階段也顯示對應名稱,避免顯示錯誤的時機。
- 轉盤右側 `.turn-side`:「行動玩家」標籤 `#acting-pointer`(三角形朝上 `.up` 或朝下,指向 `awaitedPlayer()` 所在的一側)與傾斜提示 `#dial-note`。
- 摘要文字 `actionSummary()` 改設為 `#turn-cluster` 的 `aria-label`(`role="status"`),不在畫面上顯示。
- 窄螢幕縮小尺寸。對局結束(`over`)時隱藏。

### D4:角度

- 目標角度:回合玩家在下方為 0°(標籤朝下),在上方為 180°;非戰鬥中且 `consecutive_passes >= 1` 時加 45°。
  - 戰鬥中不加,因為 `consecutive_passes` 在宣告攻擊時已歸零。
  - 結束階段等待選擇時 `consecutive_passes` 為 2,同樣只加 45°,標籤仍指向回合玩家那一側。
- 角度以累計值保存在前端(`dialAngle`),新目標角度 `target`(0..359)決定實際轉法:
  - 若是「轉回」(目標 = 目前 − 45°),直接減 45° 反向轉回;
  - 否則一律順時鐘前進到最近的等值角度(`dialAngle + ((target − dialAngle) mod 360)`),所以換人時從 45° 繼續轉到 180°。
- 第一次繪製或重新連線時直接設定、不做動畫。動畫關閉(`reduced-motion`)時不做 transition。
- 觀戰與本機模式的上下方依既有的 `topPlayerIndex()`。

### D6:傾斜時的提示

轉盤傾斜時,轉盤右側「行動玩家」標籤下方(固定位置)以小字顯示下一個回合是誰的,依觀看者稱呼(與行動欄摘要相同):回合玩家是自己時「已 pass 一次,再 pass 就換對手的回合」,是對手時「…就換你的回合」,本機模式與觀戰「…就換〔玩家名〕的回合」(`ui.turn_dial.one_pass.opp` / `mine` / `named`);沒有傾斜時不顯示。不使用滑鼠提示(`title`),觸控裝置也看得到。戰鬥中轉盤不會傾斜,提示也不出現。

### D7:日文「非バトル」

日文介面(`ja.json` 的時機、提示、附註、記錄)與規則頁(`rules.ja.json`)的「バトルしていないとき」「バトル以外」統一為「非バトル」,與「バトル中」對稱、放得進轉盤。卡片效果文(`effect_ja`)不動。

### D5:移除徽章

`renderPlayerZone` 不再加 `.turn-marker`;`ui.turn_marker` 與相關 CSS 一併移除。`test_timing_ui.py` 改為檢查轉盤的指向。

## Risks / Trade-offs

- [行動欄變高,佔用盤面空間] → 窄螢幕縮小轉盤;行動欄原本就是固定在底部。
- [累計角度無限增大] → 只是數字,CSS rotate 可接受;重新整理時歸位。
- [沒看過說明的玩家看不懂 45°] → 見 D6 的提示,行動欄 Pass 附註也說明。
