## Context

動機見 proposal.md。相關現況:

- 引擎 `_validate_spell_declaration`(攻擊 / 防禦):指令戰術需要 `slot_uid`(場上只有一隻時自動);一般戰術有 `slot_uid` 且該魔物能用時以它為使用者,否則挑第一隻能用的魔物。之後檢查 E-024 封鎖(`MAMODO_LOCKED`)與依使用者計算的費用。
- 引擎 `_use_book_card` 的非戰鬥戰術分支:不接受使用者,只檢查「至少一隻能用」,以 `spell_cost(..., slot=None)`(能用的魔物中最低費用)計費,不檢查封鎖。
- 相容判定 `_spell_usable_by`:家族相符,或 `reg.SPELL_COMPAT`(M-023 木屬性、M-029 名為「ザケル」的賈修戰術,完全相符)。
- 前端 `spellUsable` / `nonbattleSpellUsable` 以 `hasSpellMamodo` 自行判斷相容(M-029 用子字串);`pickSlotThen` 只對指令戰術跳出 `showDialog` 選擇。`showDialog` 的卡片選項不支援停用。
- 快照 `_player_view` 的翻開頁對戰術附 `cost`(未指定使用者的最低費用)。
- NPC `_spell_declarations` 本來就對每隻能用的魔物各產生一個帶 `slot_uid` 的候選(含待命允許的任意頁)。
- P-015 的待命(`kind: "spell_any_page"`,`data.spell_name`)讓 `_validate_spell_declaration` 接受未翻開、未離開魔書的頁上同名戰術(`_spell_any_page_standby`);快照與前端都沒有對應的資料與入口。
- `_play_card` 的搭檔分支以 `next(...)` 取第一隻對應的魔物,該魔物已有搭檔就拒絕;前端 `pageButtons` 以 `mamodoInPlay`(同樣取第一隻)判斷。NPC 放卡候選只有 `{"type": "play_card", "page"}`。

## Goals / Non-Goals

**Goals:**
- 玩家能選擇使用戰術的魔物,費用與魔力依選擇計算。
- 戰術相容只由引擎判定,前端照快照顯示。

**Non-Goals:**
- 不改 NPC 的攻防與非戰鬥戰術候選(攻防本來就依每隻可用魔物各產生一個)。

## Decisions

### D1:快照附 `users`

- `_player_view` 在 `can_see_player` 且該頁是戰術時,加 `users = [{"slot_uid", "cost", "locked"}]`:對自己場上每隻魔物,指令戰術或 `_spell_usable_by` 成立就列入;`cost` 為 `spell_cost(..., slot=該魔物)`;`locked` 為 `slot_restricted(..., MAMODO_LOCKED, uid)`。依場上順序。
- 原本的 `cost` 保留(最低費用,用於卡面顯示)。

### D2:非戰鬥戰術接受使用者

- `use_book_card` 增加可選的 `slot_uid`。非戰鬥戰術分支:
  - 有 `slot_uid`:該魔物必須存在且能用(指令戰術:任一魔物),否則 `spell.no_mamodo`;被封鎖則 `spell.mamodo_locked`;以它計費。
  - 沒有 `slot_uid`:候選為能用且未被封鎖的魔物;沒有能用的魔物 → `spell.no_mamodo`;有但全被封鎖 → `spell.mamodo_locked`;以候選中最低費用計費。
- `spell_cost(..., slot=None)` 的最低費用計算排除被封鎖的魔物(畫面顯示與非戰鬥戰術一致);全被封鎖時沿用原本的計算,只作顯示。
- 非戰鬥戰術的效果不依使用者,handler 簽名不變。
- 目前卡池中沒有「不同魔物使用時費用不同」的非戰鬥戰術(指令戰術 S-026 / S-057 費用為 0;其餘非戰鬥戰術只有同名魔物能用),所以非戰鬥戰術的選擇視窗目前不會出現,實際作用是 E-024 封鎖的檢查;計費機制以修改測試中卡片費用的方式驗證。

### D3:前端的使用者選擇

- `spellUsers(p, entry)`:回傳 `entry.users`,每項加上 `selectable = !locked && cost <= mp` 與停用原因(「被封鎖」「MP 不足」)。
- `spellUsable` / `nonbattleSpellUsable` 改為「至少一隻可選」;清單為空時理由為「沒有可使用的魔物」,有但都不可選時用第一個原因。移除 `hasSpellMamodo`。
- `pickSpellUser(p, entry, {nonbattle}, cb)`:可選的只有 1 隻 → `cb(uid)`;攻擊 / 防禦有 2 隻以上可選 → 選擇視窗;非戰鬥戰術 2 隻以上可選且費用不全相同 → 選擇視窗,否則 `cb(第一隻可選的 uid)`。一律送出 `slot_uid`,不再依賴引擎的預設。
- **在場上選擇(不用對話框)**:同名魔物(兩隻 M-024)在對話框中無法區分,所以改用與引擎決策相同的場上選擇。新增前端的選擇狀態 `LOCAL_PICK = {player, title, source, options: Map(slot uid → {selectable, note, reason}), onpick}`;`pickState()` 在沒有引擎決策時由它建出 `PICK`(`local: true`),可選的魔物在 `PICK.slot` 中,所以沿用 `markPickable` 發光與放大檢視的「選擇」。`choosePick` 遇到 `local` 時呼叫 `onpick` 並清除狀態,不送 `choose` 指令。
  - 放大檢視:選擇期間只顯示「選擇」(原本的效果 / 攻擊等按鈕隱藏);按鈕旁顯示該魔物使用時的費用,不可選者停用並顯示原因。
  - 行動欄:顯示提示(標題 `ui.pick_spell_user`,指令戰術 `ui.pick_command_user`,搭檔 `choice.title.pick_mamodo_for_partner`)、來源卡與「取消」(`ui.cancel`),取消即清除狀態。
  - 狀態更新(收到新的快照)時清除,避免以過時的候選送出。
  - 舊的 `showDialog` 停用與說明支援不再需要,移除。

### D5:P-015 的任意頁戰術

- 快照(持有者視角)加 `any_page_spells`:對每個 1–32 頁,不是翻開的頁、`_spell_any_page_standby` 成立者,列出 `{"page", "card", "cost", "users"}`(`users` 同 D1)。待命用掉或過期就不再出現。
- 場上魔書翻閱(左右鍵)翻到 `any_page_spells` 中的頁時,`browsedPageEl` 以 `{kind: "any_page"}` 的 ctx 畫該頁並發光,放大檢視同樣提供「攻擊」;這是「翻到別頁只看不操作」的唯一例外。
- 前端:可宣告攻擊的時機(與翻開頁的攻擊按鈕相同條件)且 `any_page_spells` 非空時,行動欄加「從魔書使用〈戰術名〉」(`ui.any_page_spell`),按下開啟「查閱己方魔書」網格。網格中這些頁加 `pickable` 樣式發光;點卡開放大檢視,ctx 為 `{kind: "any_page", p, page}`,`zoomActions` 提供「攻擊」按鈕,可用性與使用魔物選擇沿用 D3(以該頁的 `users`、`cost`)。按「攻擊」時先關閉網格(網格的層級在選擇視窗之上,否則選擇視窗會被蓋住),再走使用魔物的選擇,送出 `declare_attack`(`page`、`slot_uid`)。
- P-015 在自己回合使用(非戰鬥時機),所以只提供攻擊。

### D6:搭檔卡的裝備對象

- `play_card` 增加可選的 `slot_uid`。搭檔分支:對應的魔物 = 頂層魔物的 `related_mamodo` 與搭檔相同;候選 = 對應且 `partner is None`。
  - 有 `slot_uid`:不在對應的魔物中 → `play.no_mamodo`;已有搭檔 → `play.partner_exists`。
  - 沒有 `slot_uid`:取第一隻候選;有對應的魔物但都已有搭檔 → `play.partner_exists`;沒有對應的魔物 → `play.no_mamodo`。
- 前端 `partnerTargets(p, def)` 以同樣規則在前端計算候選(只看對應魔物與是否已有搭檔,不涉及卡片專屬的相容規則)。沒有候選時「放出」停用並顯示原因(沿用 `ui.play.no_mamodo` / `ui.play.partner_exists`);一隻時直接送出;兩隻以上時以場上選擇(D3,標題沿用 `choice.title.pick_mamodo_for_partner`)。一律送出 `slot_uid`。
- NPC `candidates` 對搭檔卡的每個候選魔物各產生 `{"type": "play_card", "page", "slot_uid"}`;魔物卡維持只有 `page`。

### D4:i18n

新增 `ui.pick_spell_user`、`ui.spell.locked`(被封鎖)、`ui.any_page_spell`(從魔書使用〈戰術名〉);沒有可使用的魔物沿用既有 `ui.spell.no_mamodo`,加到 `zh-TW` / `en` / `ja`,簡中以工具產生。

### 行為決定(reconciliation 時寫入 `card-effects/design.md`「行為決定與理由」)

- **E-024 的封鎖也適用於非戰鬥戰術**:效果文「その魔物の『魔物の効果』や術を使えない」,術不分戰鬥與非戰鬥。目前非戰鬥戰術沒有檢查封鎖,與效果文不符。專案負責人確認,`Confirmed`。

## Risks / Trade-offs

- [前端的選擇狀態與引擎決策共用畫面] → `pickState` 優先使用引擎決策;前端選擇只在沒有引擎決策時存在,收到新快照即清除。
- [快照多了 `users`] → 只在持有者視角、只對翻開的戰術頁,資料量小。
- [非戰鬥戰術開始檢查封鎖,改變既有行為] → 依效果文(專案負責人已確認);先寫修改前會失敗的測試。
