## Context

範圍與解讀見 proposal.md。既有的ジャマー機制(game-engine design「ジャマー」):
- `reg.jammer(number, mp_cost, discard_self, on)`,`on` 為 `mamodo_effect`(M-026)或 `event`(M-032)。
- 對手的行動開始前,有可用的持有者時存快照(`copy.deepcopy(state)`,費用已付);行動解決完、沒有待決事項時 `_offer_jammer_if_ready` 詢問;使用時 `_restore_effect_state` 還原。
- `_jammer_holder` 只看場上魔物(`slot.top`),每回合 1 次(`used_abilities`)。

## Goals / Non-Goals

**Goals:**
- 3 張依效果文實作並開放,每張至少一個依效果文寫的行為測試。

**Non-Goals:**
- M-058(最後一批)。
- 常駐效果與戰術獲勝時的效果的無效化(依規則不在ジャマー的範圍內)。

## Decisions

### D1 ジャマー的擴充

- `on` 新增 `mp_reduced`(M-065)。`reg.jammer` 新增參數:
  - `per_turn=None`(M-065 不限次數;其餘維持每回合 1 次);
  - `coin=True`(使用時擲硬幣,正面才無效;擲硬幣子階段照常);
  - `redo_cost=3`(Ex-034:不是無效,而是還原後重新解決,見 D3)。
- `_jammer_holder` 同時看場上魔物與搭檔(`slot.partner`):搭檔卡受「不能使用搭檔的效果」(`NO_PARTNER_EFFECTS`)限制,`discard_self` 時棄掉這張搭檔。
- 快照時機:對手的行動(事件卡、魔物的啟動效果、搭檔效果、借用的搭檔效果、非戰鬥戰術)開始前,對手有任何可能回應的ジャマー時存快照。`mp_reduced` 在行動解決後,只有持有者的 MP 在這個行動中實際減少(本批事件中有持有者的 `mp_changed` 負值)時才詢問。
- 同一個行動可能同時符合 `event` 與 `mp_reduced`(例如 E-018):所有可用的ジャマー在同一個決策中同時列出(`_offered_jammers`,依種類與場上順序、同卡號一次),選項值為ジャマー卡號(`True` 相容為第一個);多張時選項文字前加卡名(`choice.jammer_use.named`),只有一張時對話框的來源卡為它(使用者 2026-11-01:先是只提供第一張,再改為依序詢問,最後改為同時提供)。
- 選項文字依種類區分(`choice.jammer_use` 的 MP 改為帶數值、`.coin`、`.redo`),新事件 `effect_redone` 有記錄文字。

### D2 M-065 的擲幣

- 選擇使用後,以持有者為擲幣者擲 1 次(`flip_coins`,子階段中對手的 M-019 等可介入),callback 在正面時以 `_restore_effect_state` 還原快照;反面時不還原。
- 快照在擲幣期間保留在 `game.jammer_coin`(不放進狀態)。擲硬幣子階段中持有者可能使用 M-012 / Ex-026 / M-034 / P-039、對手可能使用 M-019:這些消耗記在擲幣資料的 `journal`,正面還原後補回,否則還原會把它們一起退回(實作中發現)。

### D3 Ex-034 的重新解決

- 使用時:棄掉 Ex-034(在目前狀態發事件,並在快照上同步移除,同 M-032 的 `_discard_jammer_silently`),再以 `_restore_effect_state` 還原到事件卡解決前。
- 還原後對手的 MP 若 ≥ 3:支付 3(原因 `jammer_redo`),重新執行該事件卡的 handler(同一頁、同一使用者),重新解決不再存快照、不再詢問ジャマー。若 < 3:不重新解決(事件卡無效),對手 MP 設為 0。
- 事件卡的「本回合已使用張數」與原本的費用不重複計算。

### D4 Ex-025 的「直後」

- `GameState` 新增 `action_seq`:每個非 `choose` 的指令處理完後 +1(choose 是決策,不是行動)。
- 每個非 `choose` 指令處理完後,若行動者本人有 `mp_changed` 正值(效果使自己 MP 增加;翻頁的 MP 不經過 `mp_changed`),記在行動者的 `PlayerState.last_effect_mp_gain = {"amount": n, "seq": action_seq}`。放在 `PlayerState` 中,ジャマー還原時一併還原(被無效時紀錄消失)。
- Ex-025 的使用條件:對手的 `last_effect_mp_gain` 存在且 `seq == action_seq`(之後沒有任何行動);效果為 `GainMpAsOpponentJustGained`。`timing="any"`:「直後」可能在戰鬥中,時機限制由使用條件決定。
- 開始階段與結束階段解決的待命不是行動,不產生紀錄。

## Risks / Trade-offs

- [每個對手行動都可能 deepcopy 狀態] → 只在對手場上有可能回應的ジャマー時才存快照,與既有做法相同。
- [Ex-034 重新解決時的決策] → 重新解決中的 Choose / 擲幣照一般流程建立決策;ジャマー的詢問狀態在重新解決前清除,避免重複詢問。
