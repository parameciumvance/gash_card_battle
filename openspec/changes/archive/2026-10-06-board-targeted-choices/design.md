## Context

- 選項目前的形式:`{value, card}`、`{value, card, page}`、`{page, card}`(放出魔物)、`{index, item}`(受傷順序)、`{value, label}`(純選項)。
- 前端分不出 `value` 是魔物槽 uid 還是頁碼,無法對應到畫面位置。
- 卡片層級的行動一律經由放大檢視(`battle-ui`「操作與決策互動」),點卡 → 放大檢視 → 行動按鈕。

## Goals / Non-Goals

**Goals:**

- 決策期間可以查閱場面、魔本、棄牌區。
- 每個目標都能辨識:在場上的位置、在魔本的頁碼。

**Non-Goals:**

- 客戶端自己的前置選擇(指令術選使用者 `pickSlotThen`、查看棄牌區 `showDiscard`)仍用原本的對話框。
- 不改引擎的決策邏輯與 `value`。

## Decisions

### D1:選項的位置欄位

`primitives.py` 提供三個建立函式,各處改用它們:

```text
slot_option(player, slot, card=None, **extra)
    → {value: slot.uid, card: card or slot.top, zone: "slot", player, slot: slot.uid}
page_option(player, page, card=None, **extra)
    → {value: page, page, card?, zone: "book", player}
discard_option(player, index, card, **extra)
    → {value: index, card, zone: "discard", player, index}
```

- `extra` 保留既有的附加欄位(例如 `slot_uid`)。
- 受傷順序(`damage_order`)的 `{index, item}` 中,魔物項加上 `zone: "slot"`、`player`、`slot`;魔本項不加,維持按鈕。
- 放出魔物(`deploy_page`)原本沒有 `value`,改用 `page_option`,`value` 為頁碼。原本前端就以頁碼回應,行為相同。
- 位置欄位只出現在決策者看得到的 pending 選項中(沿用視角過濾)。

### D2:行動欄的決策提示

輪到自己決策時,行動欄改為顯示決策區塊:

```text
[標題]  玩家 2:選擇自己魔本中的搭檔卡
[來源]  海德《乘風者》:【MP減少1→】從自己魔本…   (有來源卡時)
[脈絡]  第 1 枚:正面、第 2 枚:反面                (擲幣結果)
[提示]  點選場上發光的卡 / 從魔本選一頁 / 從棄牌區選一張
[按鈕]  開啟魔本  開啟棄牌區  跳過  不保護 …
[未對應的卡片選項]                                  (退回:直接列出,點了即選)
```

- 決策者以外(對手、觀戰)維持現在的摘要「等待 … 決策」。
- 蓋住畫面的決策對話框不再用於 pending。

### D3:目標標示與選擇

- 選擇模式:`pickTargets()` 依目前 pending 算出 `{slot: Map(uid → 選項), book: {player, Map(page → 選項)}, discard: {player, Map(index → 選項)}}`。
- **場上**:
  - 選項卡號等於魔物槽的 `top` → 標在魔物卡上。
  - 選項卡號等於魔物槽的 `partner` → 標在搭檔卡上。
  - 加上 `.pickable` 發光(和可用卡的發光區分顏色)。
- **翻開的頁**:場上魔本的翻開頁若是可選頁,也加 `.pickable`。
- **放大檢視**:`zoomActions` 在既有按鈕之外,若該實例是可選目標,加上主要按鈕「選擇」,按下送出 `choose`。
  - 新增 `ctx.kind = "pick"`,用於魔本網格與棄牌區中、不在場上的卡。
- **魔本網格**:沿用查閱魔本的對頁網格(`showBookReview(p, pick)`)。
  - 自己的魔本:32 頁都有卡面(快照的 `book`),可選頁加 `.pickable`。
  - 對手的魔本(E-016):只有選項中的頁有卡面,其他頁只顯示頁碼與卡背。
  - 點可選頁 → 放大檢視 → 選擇。
- **棄牌區**:`showDiscard(p, pick)` 可選的卡加 `.pickable`,點了開放大檢視。
- pending 結束或改變時,選擇按鈕與發光隨重繪消失。開著的網格依新狀態重繪,不再是決策時則關閉。

### D4:不自動開啟網格

決策開始時不自動開啟魔本網格與棄牌區,由提示區的按鈕開啟。網格會蓋住場面,自動開啟就違背了「決策時可以查閱場面」的目的。

### D5:實作中的調整

- **選完關閉網格**:從魔本網格送出選擇後自動關閉網格,回到場面(端到端操作時發現選完網格還蓋著場面)。
- **放大檢視疊在網格之上**:原本放大檢視的 z-index(50)低於查閱魔本(55),網格中的卡放大後被蓋住;調為 56。
- **空頁直接選**:空頁沒有卡面可放大,點了直接送出。

## Risks / Trade-offs

- [多一次點擊] → 換來能先看完整效果、避免誤觸送出;使用者已確認。
- [新的選項來源忘了用建立函式] → 前端退回在提示區列出,不會卡住;測試掃描所有 pending 選項種類都帶 `zone` 或 `label`。
