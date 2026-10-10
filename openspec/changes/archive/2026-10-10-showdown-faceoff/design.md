## Context

- 引擎 `_resolve_showdown` 發出 `showdown`(`attacker`、`attacker_total`、`defender_total`、`winner`、`attack_negated`、`attacker_breakdown`、`defender_breakdown`)。雙方的魔物與戰術在 `battle`(`attack_slot`、`attack_spell`、`defense_slot`、`defense_spell`)。
- 前端 `anim.js`:`run()` 依時間軸逐格播放,阻塞演出(`kind: "anim"`)以 `withTimeout(playBlocking(...), HARD_TIMEOUT)` 等候,`HARD_TIMEOUT` 為 1500ms;`showdown()` 是中央橫幅、數字滾動 380ms 加停留 420ms。動畫關閉時時間軸不放阻塞演出。
- 聚焦展示的停留 `spotlightMs`:演出設定的聚焦「快」或 `pending >= 2` 時加快;點擊 `#spotlight` 跳過。
- 卡面元件 `cardEl(num)`(app.js)處理卡圖與無卡圖時的文字卡面。

## Goals / Non-Goals

**Goals:** 中央上下對峙的演出,結果以大字明確呈現;引擎事件帶出對峙的卡。

**Non-Goals:** 不改音效;不改之後的傷害聚焦;不改行動記錄與明細檢視;不改舞台(`#battle-stage`)的即時合計。

## Decisions

### D1:事件欄位

`showdown` 事件加 `attack_mamodo`、`attack_spell`、`defense_mamodo`、`defense_spell`:
- 魔物為該魔物槽最上面的卡號(`slot.top`);槽已不存在時為 null。
- 攻擊戰術為 `battle.attack_spell`,無戰術攻擊為 null。
- 不防禦時防禦方兩欄皆為 null。

不用前端的前一個快照組資料:事件本身就能完整重現,不依賴快照時序。

### D2:版面與登場

- 全畫面半透明背景 `.fx-faceoff`(可點擊跳過),中央一欄:上方一組、中間「VS」、下方一組。
- 上下依 `topPlayerIndex()`:屬於上方玩家的那組放上面、從上方滑入;下方那組從下方滑入。觀戰與本機同理。
- 每組橫排「魔物卡、戰術卡」,以 `cardEl` 繪製(與盤面一致,沒有卡圖時也能顯示),組旁標「攻」/「防」與玩家名稱。
  - 不防禦:沒有使用戰術的魔物(防禦方可能有多隻,事件兩欄皆為空),那組只放一個虛線框加「不防禦」字樣。
  - 無戰術攻擊:戰術位置為 `attacker_breakdown` 中 `fixed` 項的來源卡;沒有來源卡時為虛線框加「無戰術攻擊」。
  - 魔物為 null(理論上不會發生)時以虛線框代替。
- 合計數字在組的外側(靠畫面邊緣的一側),VS 保持在正中央。

### D3:節奏

以比例分段(總長 `T`:標準 2500ms;聚焦「快」或 `pending >= 2` 時 1200ms):

| 時段 | 內容 |
|---|---|
| 0–20% | 雙方滑入、VS 出現 |
| 20–50% | 合計數字從 0 滾到合計;被無效的一方蓋「無效」戳記並歸 0 |
| 50–62% | 勝方朝敗方衝撞(位移後彈回),敗方震動 |
| 62–100% | 勝方放大金光、敗方變暗打叉,中央結果大字 |

- 結果文字:`winner === "attacker"` →「攻擊成功」;否則 `attack_negated` →「攻擊無效」,合計相同 →「防禦成功」加小字「同值・防禦方勝」,其餘 →「防禦成功」。
- 點擊背景立即結束(移除元素並 resolve)。
- 以 CSS 動畫加上 JS 依時段切換 class 實作;數字滾動用 requestAnimationFrame。

### D4:逾時

阻塞演出的硬性逾時改為依事件類型(`blockingLimit`):擲硬幣維持 1500ms;魔力對決為 `T + 1000ms`;傷害能量為能量時間加兩段保護者動作(橫置、回原位)再加 1000ms;保護移動為兩段保護者動作加 1000ms。保底仍然存在,演出卡住也會重繪。能量加保護者橫置與回原位約 1.55 秒,超過原本固定的 1.5 秒:盤面會在保護者回到原位前提早重繪,造成閃一下直放,所以不能沿用固定值。

### D6:傷害能量

- 使用者在對峙演出實作後追加。
- 對象事件:`damage_dealt`(目標為該方 `.book-cover`)、`mamodo_injured`,以及 `reason` 為 `damage` 的 `mamodo_discarded`(目標為該魔物槽)。
- 時間軸遇到這些事件時(動畫開啟)插入一段阻塞演出,之後的聚焦文字另起一格。這時盤面尚未重繪,送墓的魔物也還在原位,所以量得到目標位置。音效隨能量那一格播放,文字格不重複列入該事件。
- 起點固定在畫面中央:對峙演出與聚焦展示都在中央,傷害來源(戰術、反擊、效果)不一定在場上有位置。事件沒有帶來源,也不需要為此修改引擎。
- 外觀:發光球加尾跡,以 left/top transition 飛行(總長 70%),命中處放射狀爆光(30%)。標準 650ms、快或落後時 380ms,在原本 1.5 秒的保底內。
- 戰鬥傷害常要先等受傷方決定是否保護,所以能量通常和對峙演出不在同一批,在決定後那一批播放。

### D7:回合轉盤改橢圓(順帶調整)

- 使用者在本 change 期間要求把回合轉盤改成橢圓、降低行動欄高度(寬螢幕約 132×70,手機約 88×48),不另開 change。
- 外圈改為橢圓後,不能再整圈旋轉帶動標籤(會走圓形軌跡)。改法:
  - `--dial-angle` 以 `@property` 登記為角度,在 `#turn-dial` 上做轉場;
  - 「回合玩家」標籤的位置以 `sin()`/`cos()` 沿橢圓計算,標籤維持正向;
  - 三角箭頭只朝上或朝下(回合玩家在上方時朝上,`.dial-tab.up`),傾斜時也不歪(使用者指定)。
- 順時鐘箭頭的 SVG 以 `preserveAspectRatio="none"` 隨橢圓拉伸,線寬用 `non-scaling-stroke` 維持粗細。
- 角度規則(累計、順時鐘、轉回)不變。

### D8:保護演出

- 使用者追加。`protected` 事件加 `target`(`book` / `slot`)與 `target_slot`(被保護的魔物槽)。
- 時間軸遇到 `protected`(動畫開啟)時插入阻塞演出 `guardMove`:
  - 複製保護者的盤面元素,原元素暫時隱藏;
  - 複製品移到對象正前方:中心對齊,朝畫面中央偏移最多 28px,讓對象仍露出一部分;
  - 記在 `guard`。
- 複製品放在只負責移動的外框 `.fx-guard-wrap`(以中心定位、left/top 過渡)裡,卡本身保留自己的 class:已負傷的保護者維持橫置。不能用外框的尺寸直接定位卡,旋轉後的外框寬高是對調的。
- 接著的能量若打在同一隻保護者(`mamodo_injured` / 因傷害送墓),改打在複製品的位置。命中後:
  - 負傷:複製品在原地加 `injured` 轉成橫置,再回到原位;
  - 送墓:複製品在原地淡出,原元素維持隱藏,重繪後該魔物已不存在。
  - 順序依使用者指定:承受 → 橫置 → 回到原位。
- 回到原位後複製品留在原位,等盤面重繪(已是負傷橫置)後才移除(`clearGuardLeftovers`),否則重繪前會短暫露出舊的直放卡。下一批開始時也會清掉殘留。
- 沒有能量(傷害被防止、保護者免疫)時,在重繪前回到原位;演出出錯時直接移除並恢復,不留殘影。
- 複製品不在 `#board` 底下,所以盤面卡片的尺寸與隱藏規則也套用到 `.fx-guard`。

### D5:i18n

- 新增:`anim.showdown.vs`、`anim.showdown.attack_success`、`anim.showdown.defense_success`、`anim.showdown.tie`、`anim.showdown.attack_negated`、`anim.showdown.negated`(無效戳記)、`anim.showdown.no_defense`、`anim.showdown.no_spell`。
- 保留 `anim.showdown.att` / `def` 作為組的標籤。
- 四語(簡中以工具產生)。

## Risks / Trade-offs

- [演出變長,拖慢對局] → 快速設定 1.2 秒、落後自動加快、點擊跳過;動畫可關。
- [手機上兩組四張卡太寬] → 窄螢幕縮小卡片;一組兩張橫排在 390px 寬度內放得下。
