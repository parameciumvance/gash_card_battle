## Context

動機見 proposal.md。相關現況:

- 檢視節點 `PeekOpponentOpenPages`(`effects/tree.py`)發出 `pages_peeked{player, viewer, cards}`;E-014 已使用,M-018 沒有。M-018 只有 `When(OpponentOpenPagesLackDefenseSpell(), then=GainMp(2))`。
- 啟動型效果的時機只有 `Activated.timing`(any / battle / nonbattle),由 `engine._use_field_ability` 檢查「在不在戰鬥中」,沒有任何回合歸屬的檢查。卡池中只有 M-018 寫「自分のバトルフェイズ」。快照的 `_ability_view` 把 `timing` 給前端,前端依它停用放大檢視中的按鈕(`app.js` 的可用性判斷)。
- `api/views.filter_event` 對 `book_revealed` / `pages_peeked`:`viewer == ev.viewer` 才保留 `cards`,其餘去掉 `cards`;本機全視角(`"all"`)一律原樣回傳,本來就含卡片清單。
- 前端 `applyPayload` 以 `animSeq` 游標只把新事件交給 `Anim.apply(fresh, prevS, render, actor)`;`actor` 為 null 的批次(開局、金手指、重連)不播音效。`pages_peeked` 目前只在 `logText` 寫一行記錄。
- 既有資訊對話框 `showInfo(kind, title, body)` / `closeInfo()`(`#info-overlay`),更新內容已用它做「確認」按鈕。

## Goals / Non-Goals

**Goals:**
- M-018 依效果文:檢視 → 判斷 → 加 MP;只限自己回合的非戰鬥中。
- 讓檢視者實際看到被檢視的頁(E-014、M-018 共用)。

**Non-Goals:**
- 不改 E-016 / E-017 的 `book_revealed` 顯示(它們的選擇提示本來就列出那些頁)。
- 不在引擎新增「確認已看過」的待決策。
- 不改被檢視方的記錄文字。

## Decisions

### D1:M-018 效果樹在判斷前加入檢視

```
Sequence(steps=(
    PeekOpponentOpenPages(),
    When(OpponentOpenPagesLackDefenseSpell(), then=GainMp(amount=2)),
))
```

檢視與判斷看的是同一組「今のページ」,中間沒有任何會翻頁的步驟。

### D2:以 `Activated.own_turn` 表達「限自己回合」,錯誤碼 `ability.timing`

- `Activated` 新增 `own_turn: bool = False`;`_use_field_ability` 在現有 timing 檢查旁加上:`own_turn` 且 `player != turn_player` 時拒絕 `ability.timing`。檢查在支付 MP 與標記已使用之前,所以被拒絕時不付費、不算使用過。
- M-018 登記為 `timing="nonbattle", own_turn=True`。
- `_ability_view` 一併輸出 `own_turn`,前端的可用性判斷在非自己回合時停用 M-018 的使用按鈕(battle-ui「操作與決策互動」只提供合法操作)。
- 替代方案:寫成 `condition`(效果樹的條件節點)。不採用:錯誤碼會是 `ability.condition`,而這是時機限制;且前端無法從快照得知,要另外處理。另一個方案是新增 timing 值(例如 `own_nonbattle`),但時機(戰鬥中與否)和回合歸屬是兩個獨立維度,合成一個值之後組合會增加。

### D3:檢視對話框在前端依事件跳出

- 在 `applyPayload` 中,`Anim.apply(...)` 回傳的 promise 完成後(聚焦、阻塞動畫、重繪都結束),若這批是即時批次(`actor` 不為 null),從這批新事件中挑出含 `cards` 的 `pages_peeked`,依序以 `showInfo("peek", 標題, 卡片列)` 顯示;「確定」按鈕關閉。同一批有多個時合併成一個對話框、各自一段。
- 「即時」的判斷沿用音效的規則:`actor` 為 null 的批次(開局、金手指、重連的全量快照)不跳出;`fetchMissedEvents` 補回的事件只進記錄,不經 `Anim.apply`,也不跳出。重新整理後 `animSeq` 從頭開始,但 welcome 不帶事件,補回的事件走 `appendLog`,因此不會重跳。
- 是否跳出只看事件是否帶 `cards`:伺服器已經依視角過濾,前端不再比對 viewer。這樣本機全視角(收到原樣事件)不必特例,線上的被檢視方與觀戰者收到的事件沒有 `cards`,自然不跳出。
- 卡片列沿用既有卡片元件(卡圖或文字卡面),點擊開啟放大檢視;放大檢視疊在對話框上,關掉回到對話框。
- 對話框不阻擋對局:不送任何指令,計時照常。若對話框開著時又來了新批次,新的檢視事件替換內容(不會發生在同一使用者短時間連續兩次檢視以外的情況)。
- 替代方案:引擎加入待決策讓玩家按「確定」。不採用:檢視不需要玩家做任何選擇,加待決策會影響計時、NPC 與行動權輪替。

### D4:i18n

- 新增對話框標題 `ui.peek.title`(例如「對手目前翻開的頁」)與頁碼標籤;按鈕沿用確認文字。四種語言的 `i18n/*.json`(簡中由 `tools/build_zh_cn.py` 產生)。

### 行為決定(reconciliation 時寫入 `card-effects/design.md`「行為決定與理由」)

- **M-018 只能在自己的回合使用**:依「自分のバトルフェイズに」,對手回合的戰鬥階段不是自己的戰鬥階段。使用者已確認(對手的回合不該發動)。確認狀態 `Confirmed`。
- **M-018 只能在非戰鬥中使用**:卡面沒有戰鬥圖示的場上效果是非戰鬥時機,「自分のバトルフェイズに」只限定回合,不擴大到戰鬥中。使用者已確認(沒有 battle 圖示就是非戰鬥)。確認狀態 `Confirmed`。
- **M-018 先檢視再判斷**:「相手の魔本の今のページを見る。そこに…」,檢視是效果的一部分,判斷的對象就是看到的頁。確認狀態 `Confirmed`(使用者指出應讓玩家檢視)。

## Risks / Trade-offs

- [跳出的對話框蓋住盤面] → 只在自己的效果結束後跳出,一鍵關閉;battle-ui「決策提示不得以對話框呈現」針對的是決策,檢視不是決策。
- [對話框開著時輪到自己行動,玩家沒注意計時] → 計時照常顯示在頂欄;對話框只有一個按鈕,關閉成本低。
- [NPC 使用 M-018 會多知道對手的頁] → 這是效果文本來的結果;`npc-opponent` 已把 viewer 為 NPC 的 `pages_peeked` 列入可見範圍,determinize 會保留這些頁。
