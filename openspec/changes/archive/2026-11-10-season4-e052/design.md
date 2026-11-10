# Design

## Context

- 效果文:E-052「このターン中に、相手のジャマー効果や『無効にする』効果などで無効にされた自分のカードの効果1つを選ぶ。その効果を使っていないことにする(コストとしてはらったMPや、コストとして捨て札にしたカードはもどってくる)。」無圖示(非戰鬥中),A/D 欄 AD。
- atwiki 卡頁 pages/1185:FAQ A1「使っていなかったことにした術や魔物の効果を、同じターンにまた使うことはできますか?」→ できます。解說:自己的卡當作沒用過,對手的卡照算用過。
- 干擾在戰鬥中不能用(season4-events-b),所以戰鬥中的無效只來自戰鬥中效果與防禦戰術的「無効にする」。
- 2026-11-09 explore,專案負責人決定:解讀嚴格依字面;費用卡回不到原位時留在棄牌區;回場不算「場に出た」。

## Decisions

### D1:使用紀錄

各可被無效的使用路徑在付費時建立「使用紀錄」:

```
{"card", "kind", "mp": 實際支付的 MP(含追加費用), "returns": [當作費用棄掉的卡的原位], "undo": {要重設的使用紀錄}}
```

| 路徑 | kind | undo |
|---|---|---|
| 事件卡(`_use_book_card`) | `event` | `events_used_this_turn` −1 |
| 魔物 / 搭檔的啟動效果(`_use_field_ability`) | `ability` | `used_abilities` 的 key、`used_per_game` |
| 借用的搭檔效果(E-010) | `borrowed` | 借用的 `used` |
| 非戰鬥戰術 | `nonbattle_spell` | `used_nonbattle_pages`、戰術名稱 / 屬性紀錄 |
| 干擾(M-026 / M-032 / M-065;連鎖被對手 M-026 無效) | `jammer` | `used_abilities` 的 key |
| 攻擊(戰術 / 魔物效果) | `attack` | `spell_page_uses` −1 或魔物效果的 key、戰術名稱 / 屬性紀錄 |
| 防禦(戰術 / 魔物效果) | `defense` | 同上 |

- `returns`:魔物(整疊、搭檔、負傷狀態、欄位)以 `_discard_slot(reason="cost")` 棄掉時;搭檔(`discard_attached_partner(reason="cost")`)時記原本的魔物 uid。MJ12 的效果不會被無效(沒有回應它的干擾),不記。
- 使用紀錄放在干擾的詢問資料(`game.jammer["usage"]`)與戰鬥資料(`battle.data["attack_usage"]` / `["defense_usage"]`)。

### D2:被無效的效果

- `PlayerState.negated_this_turn: list[dict]`:使用紀錄,回合結束清空。
- 干擾:無效化成立(還原快照之後)把被無效那一方的使用紀錄加進去,包括 M-065 擲出正面、Ex-034 付不起追加費用、連鎖時自己的干擾被對手的 M-026 無效。
- 戰鬥:`_end_battle` 時,攻擊或防禦被無效、且無效它的效果屬於對手(新增 `battle.data["<side>_negated_owner"]`,在 `NegateAttack`、`NegateOpponentSpell` 等設定時記下)時,把那一方的使用紀錄加進去。M-055 反面是自己的效果,不算。
- 戰術名稱 / 屬性紀錄(`spell_names_by_turn` / `spell_attrs_by_turn`)由集合改為清單,還原時只移除一筆;既有的「是否用過」判斷照舊以 `in`。

### D3:E-052 的還原

- 選項:`negated_this_turn` 中的紀錄(決策種類 `pick_negated_effect`,選項帶卡號與種類)。只有 1 筆時自動選(既有慣例)。沒有紀錄時不能使用(`event.condition`)。
- 還原:
  1. 退回 `mp`(`gain_mp`,原因 `refund`;不是「效果使 MP 增加」,不受 P-020 / P-044 的「MPをふやせない」影響:字面是「もどってくる」不是「ふやす」,專案負責人 2026-11-09 確認)。
  2. `returns`:魔物回到場上(原 uid、整疊、搭檔、負傷狀態;欄位原本的空著就用原欄,否則最左邊的空欄);場上已有 3 隻,或同名魔物已在場上時留在棄牌區。搭檔回到原本的魔物;那隻魔物已離場或已裝了搭檔時留在棄牌區。都從棄牌區移除,不發 `card_played`、不觸發「場に出たとき」。
  3. `undo` 的使用紀錄全部重設。
  4. 從 `negated_this_turn` 移除這筆。
- 事件 `effect_undone`(卡號、退回的 MP、回來的卡)。

## Risks / Trade-offs

- [使用路徑多] → 測試涵蓋事件卡、魔物效果、費用棄掉的魔物、搭檔、非戰鬥戰術、攻擊、防禦、干擾連鎖。
- [「場上已滿」的上限] → 依引擎現有的放出上限判斷(同名、3 隻)。
