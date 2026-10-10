## Context

- 疊放清除負傷的三處:`engine._play_card`(`base_slot.injured = False`,註解「疊放登場回復健康」)、`tree.DeployMamodoFromBook`(E-012 等自魔書放出,疊放分支)、`tree.StackFromBookOnto`(S-048)。
- 事件卡有 `reg.EVENT_CONDITION`(`when=`),引擎在付費前檢查、拒絕 `event.condition`;非戰鬥戰術沒有對應機制。
- `RobnosTransformMode.options` 只看場上數量;S-043 分裂用 `PlaceMamodoFromBookUpTo` 依頁序自動放出至多 2 張(未讓玩家選)。
- 前端事件卡與非戰鬥戰術不知道使用條件,按下後才由伺服器拒絕。

## Goals / Non-Goals

**Goals:** 疊放繼承負傷;選不到對象的非戰鬥戰術不能使用且不付費;畫面預先停用。

**Non-Goals:** 不改 E-027、S-039、M-025;不改啟動效果與事件卡既有的條件內容(只是讓畫面看得到)。

## Decisions

### D1:疊放不改負傷

三處都拿掉 `injured = False`。疊放魔物以 slot 為單位保存負傷,最上層換卡不影響。

### D2:非戰鬥戰術的使用條件

- `reg.spell_nonbattle(number, effect=..., when=None)`,`when` 存到 `reg.SPELL_NONBATTLE_CONDITION`(`fn(game, player) -> bool`,與事件卡相同介面)。
- 引擎非戰鬥戰術分支:在時機、使用魔物、每回合次數檢查之後、計費之前檢查,不成立拒絕 `spell.condition`。
- S-048:`when=All(OwnFieldHas("M-028"), HasOptions(OwnBookCopiesOf("M-027")))`。
- S-043:`when=HasOptions(RobnosTransformMode())`;`RobnosTransformMode` 的模式改為完整可行才列出(合體加「魔書有 M-025」,分裂加「魔書至少 2 張 M-024」與場上空位 `len(slots) - 1 + 2 <= MAX_FIELD_MAMODO`),`validate` 一致。

### D3:S-043 分裂由玩家選 2 張

分裂改為 `Sequence(DiscardOwnMamodoByNumber("M-025", 1), Choose(OwnBookCopiesOf("M-024"), bind="page", prompt="pick_mamodo_in_own_book", then=PlayMamodoFromBook()), Choose(... 同上 ...))`;第二次選擇時第一張已離開魔書,自然不會重複。移除 `PlaceMamodoFromBookUpTo` 與其節點測試,改為新情境的測試。

### D4:快照與前端

- `_player_view`(持有者視角)對翻開的事件卡加 `condition_ok = EVENT_CONDITION.get(num)(game, p)`(無條件為 true),非戰鬥戰術用 `SPELL_NONBATTLE_CONDITION`。
- 前端:事件卡的使用判斷與 `nonbattleSpellUsable` 在 `condition_ok === false` 時停用,原因 `ui.condition`(「不符合使用條件(例如沒有可選的對象)」)。

### D5:翻閱時的決策目標頁

場上魔書翻閱(`browsedPageEl`)原本一律唯讀,進行中的「從魔書挑頁」決策目標頁翻到時無法選擇。改為:`PICK.book` 中有該頁時,卡面以 `{kind: "pick", zone: "book"}` 的 ctx 發光(與網格相同,放大檢視按「選擇」);已離開魔書的空頁目標點卡背直接選。

### 行為決定(reconciliation 時寫入 `card-effects/design.md`「行為決定與理由」)

- **疊放繼承負傷狀態**:疊放是在前身之上變身 / 合體,前身的狀態延續;取代原本「疊放登場回復健康」的解讀。專案負責人確認,`Confirmed`。
- **需要選擇對象的效果選不到對象時不能使用**:S-048、S-043 以「選得到對象」為使用條件,不付費。S-043 分裂比照效果文剛好選 2 張,所以魔書至少要有 2 張 M-024,且場上放得下。E-027、S-039、M-025 不適用(理由見 proposal)。專案負責人確認,`Confirmed`。

## Risks / Trade-offs

- [既有測試驗證「疊放恢復健康」] → 依新行為改寫,改寫前先確認它們在新測試下失敗的原因就是這個行為。
- [`condition_ok` 與伺服器判斷不一致] → 同一個條件函式,快照與引擎共用。
