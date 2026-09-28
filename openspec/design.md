# 專案設計(現況)

本檔記錄**目前有效**的設計與決定,以及為什麼這樣決定。

- 可觀察行為(遊戲規則、卡片效果的結果)寫在 `openspec/specs/`,本檔不重複。
- 各 change 的 `design.md` 是當時的討論紀錄,歸檔後不再更新;仍然有效的決定整理到本檔。
- 歸檔 change 前,依 AGENTS.md 的流程把該 change 仍有效的決定合併進來,被取代的改寫或刪除。
- 本檔第一版整理自 `effect-tree-interpreter` 與 `effect-tree-migration` 兩個 change;更早的 change 尚未整理。

## 1. 引擎

- 純 Python、無 IO:`engine.submit(game, command)` 收指令、回傳事件列表。前端、API、測試都只透過指令與事件互動。
- 狀態(`engine/state.py`)維持純資料:不存閉包或函式,將來的 history / 重播才可行。
- 等待玩家決策時建立 `PendingChoice`,期間只接受該玩家的 `choose` 指令。resolver 驗證失敗(拋出 `IllegalCommand`)時保留 pending 讓玩家重選,所以 resolver 必須先驗證、再改狀態。
- 引擎內建的決策種類保留給引擎使用,卡片效果不可重用(`tree.RESERVED_KINDS` 與 `reg.CHOICE_RESOLVERS` 的 key):`protect`、`damage_order`、`deploy_page`、`injure_instead_target`、`coin_confirm`、`opp_coin_redo`、`jammer_negate`、`spell_discount`。
- 只有回合玩家能宣告攻擊(`attack.not_turn_player`)。「下一場戰鬥」類效果的解讀建立在這條規則上(見 3.1)。

## 2. 效果樹

卡片效果以不可變節點組成的樹描述,程式在 `engine/effects/`:

| 檔案 | 內容 |
|---|---|
| `tree.py` | 節點、條件、選項規格、查詢規格,以及直譯器 |
| `tree_cards.py` | 所有卡片的登記(唯一的逐卡註冊檔;依卡號排序,排版規則見檔案開頭) |
| `primitives.py` | 節點共用的狀態操作(加魔力、翻頁、待命、擲幣⋯) |
| `registry.py` | 引擎與卡片效果之間的掛鉤表 |

### 2.1 節點是資料

- 節點是 `@dataclass(frozen=True)`,子節點放在欄位(`then`、`steps`、`otherwise`)。整棵樹在註冊時建好,存在 `EFFECTS["<卡號>:<掛鉤>"]`。
- 不用閉包 / lambda 組合:停下時必須把閉包存進狀態,狀態就不再是純資料。
- 節點與函式名稱語意化、不含卡號;`source`(卡號)由註冊層寫入 `ctx["source"]`。
- 通用節點組不出來時才新增專屬節點,新節點要有單元測試。

### 2.2 停點與續體

- 停下(等玩家選擇、擲幣確認、待命)時,只存續體 `(effect_id, path, ctx, floor)`,不存閉包。
  - `path` 是停點節點本身的位置。
  - `ctx` 可 JSON 序列化,至少含 `player`、`source`。
- 恢復後沿 `path` 由深往淺「上溯」:父節點是 `Sequence` 時執行之後的兄弟節點;上溯經過節點時呼叫其 `leave(ctx)`(`AsOpponent` 在此把 `player` 換回來)。
- pending 依專屬鍵分派,不只看「有沒有續體」,否則會跳過 M-012 / M-019 的確認 resolver:
  - `data["tree_choice"]`:由樹建立的選擇,交給節點的 `resume_choice`。
  - `data["tree_cont"]`:擲幣確認鏈結束、待命觸發時的 callback payload,交給節點的 `resume`。
- 目標以穩定的 slot UID 綁定,執行當下才重新查找;目標已離場時無效果、不發事件,也不改選別的目標。

### 2.3 擲幣

- `Coin` 只在第一次執行時消耗 `game.rng`;恢復時不重擲。玩家合法要求的 M-012 / M-019 重擲照原流程消耗 RNG。
- 沒有確認鏈時 `flip_coins` 會同步呼叫 callback。為避免上溯與外層 `Sequence` 各續行一次,`Coin.run` 使用行程內、不進狀態的 in-flight 記號(`tree._flip`)判斷是同步完成還是停下。
- 擲幣者與效果擁有者分開記錄:擲幣者寫在 `data["flipper"]`,呼叫端的 `data["player"]` 不可被覆寫(E-020 曾因此把 MP 給錯人)。
- 付費重擲(E-011)的迴圈只在 `CoinWithPaidReflip` 節點內部,外層節點只續行一次。

### 2.4 待命

- `Standby` 是脫離式:排程後立即完成,外層照常續行;觸發時只解決 `then`,不上溯到祖先(續體的 `floor` 設為 `len(path)+1`)。
- `Standby.then` 只能同步完成,註冊時 `validate_tree` 檢查(`NegateNextDamageThisBattle` 也一樣)。原因是開始階段會一次觸發所有到期的待命,不是可恢復的流程;兩個會停下的 `then` 會互相覆寫 pending。
- 待命的時效(`Standby.data["expires"]`):

| 值 | 移除時機 | 用於 |
|---|---|---|
| `"turn"`(預設) | 建立當回合結束 | 大多數「このターン中」 |
| `"next_start"` | 下回合開始階段觸發,該回合結束時移除 | E-001 |
| `"next_battle"` | 本回合下一場戰鬥開始時改為 `"battle"`;沒有戰鬥則回合結束時移除 | P-001、P-007、M-008、S-019、S-026 |
| `"battle"` | 戰鬥結束 | P-006(「このバトル中」) |

### 2.5 登記方式

- 會執行動作的效果以效果樹登記:`reg.event`、`reg.spell_rider(on_declare / on_damage / on_win / on_defense_damaged)`、`reg.spell_nonbattle`、`reg.activated`、`reg.on_play`、`reg.on_discard`、`reg.start_phase`、`reg.trigger`。後面幾種的 `ctx` 含 `self_slot`,觸發器另含 `event`。
- 只回傳值的查詢不是效果,以不可變、可呼叫的規格物件登記,不經效果樹:`static_power`、`damage_immunity`、`spell_compat`、`spell_use_limit`、`activated(condition=)`、`damage_bonus`。
- 純資料以對應函式登記:`stack_on`、`max_copies`、`mamodo_attack`、`jammer`。
- 登記是原子操作:先完成全部檢查才寫入;同卡同掛鉤重複登記一律拒絕。
- `registry.py` 仍接受舊的 `@reg.xxx` 裝飾器,只剩測試使用;新卡一律用效果樹。

## 3. 規則機制的共通決定

### 3.1 「このターン中の次のバトル」

待命只作用於本回合的下一場戰鬥:戰鬥開始時綁定到這場戰鬥(`engine._arm_next_battle_standbys`),條件不符而沒生效的在戰鬥結束時移除,不留到之後的戰鬥。無術攻擊的戰鬥也算下一場。E-013 / S-057 只能在自己的回合使用,而只有回合玩家能攻擊,所以「自己攻擊的下一場」與「下一場」相同,沿用「擁有者攻擊時消耗」的寫法即可。

### 3.2 「〇〇の術」以使用術的魔物判定

「スギナの術」「フェインの術」等,以**使用術的魔物**判定,不看術卡上的對應魔物;不限使用對象的指示術由該魔物使用時也適用。

- 費用:`spell_cost(game, player, page, card, slot=)` 依使用的魔物計算;未指定魔物時取可用魔物中最低的費用,供畫面顯示與宣告前的 MP 檢查。
- 加成待命(`spell_bonus`)只在使用魔物相符時消耗。

### 3.3 可選的減費(M-008)

- 宣告術(攻擊或防禦)時,若減費可用且付得起原價,建立 `spell_discount` 決策,之後才續行宣告(`_open_battle_in` / `_finish_defense_declaration`)。決定記在宣告資料的 `discount`,開戰付費時依此計算。
- `spell_cost(..., discount=False)` 不計可選的減費。可選的待命在 `data["optional"]` 標記。
- 術的魔力加減只作用在術本身、不低於 0(`_side_total`)。

### 3.4 翻 / 回翻自己的魔本

- 「翻 / 回翻自己魔本」的效果一律經過 `primitives.own_book_turn_effect`,由它記錄本回合用過(`page_effect_used` / `page_back_effect_used`)。
- P-010 / P-018 另外設定限制旗標(`page_effect_limited` / `page_back_effect_limited`),之後同方向的效果不發生,並發出 `page_turn_restricted` 事件。
- 回翻最多回到第一頁;`turn_back_pages` 回傳實際張數,沒有回翻時不發事件,P-019 依實際張數計算。
- 受傷翻頁、開始階段翻頁、結束階段強制翻頁不是效果,不經過這裡。

### 3.5 「減少對手 MP」的紀錄(E-018)

- 經 `reduce_opponent_mp` / `mark_opp_mp_reduced` 記錄到 `opp_mp_reduced_turns`,只保留本回合與前一回合。
- 會記錄的效果:E-018、S-020、P-002、P-019(被動效果也算「使用」)、E-004(對手 MP 為 1 以上時)。

### 3.6 ジャマー(M-026)

- 魔物的啟動效果使用前拍快照,效果(含其後的選擇)完成後才詢問持有 M-026 的一方。使用則以 `_restore_effect_state` 還原。
- 還原:玩家、modifier、待命、戰鬥內容。
- 不還原:行動權、pass 次數、戰鬥輪替。對手的費用與「本回合已使用」照算。
- 雙方都有 M-026 時可連鎖。效果使戰鬥開始 / 結束或遊戲結束時不提供。夥伴效果、被動效果、擲幣確認鏈中的 M-012 / M-019 不觸發。

### 3.7 術卡使用次數以頁計數

`spell_page_uses` 以頁計數,上限由 `spell_use_limit` 查詢掛鉤決定(M-024 兩隻分身體時 ビライツ 每張每回合 2 次)。

## 4. 效果文解讀紀錄

效果文沒有明說、由實作決定的部分。修改相關卡片前先看這裡;要改變解讀,先和使用者確認。「確認」欄:**使用者決定**是使用者明確選擇的;**已告知**是實作時告知使用者、未另外表示意見的。

| 卡 | 效果文沒說清楚的地方 | 採用的解讀 | 確認 | 來源 |
|---|---|---|---|---|
| E-018 | 被限制成減 0 時算不算「使用過減少 MP 的效果」 | 算,連續使用時之後都減 0 | 已告知 | effect-tree-migration |
| E-027 | 由誰選要保留的夥伴、要取的頁、要裝的魔物 | 各方玩家自己選;只有一個選項時不詢問 | 使用者決定 | effect-tree-migration |
| M-025 | 由誰選放回的空頁 | 玩家選(放回是玩家的動作) | 已告知 | effect-tree-migration |
| M-026 | 「無效」要還原到什麼程度 | 完整還原到效果前的快照,範圍見 3.6 | 使用者決定(細節已告知) | effect-tree-migration |
| 「〇〇の術」(P-001 / P-005 / P-007 / M-008) | 看術卡的對應魔物,還是使用術的魔物 | 使用術的魔物,指示術也適用 | 使用者決定 | effect-tree-migration |
| P-013 | 疊放的魔物入墓算幾張 | 依魔物卡張數:疊兩張算 2 張、裝甲體單獨入墓算 1 張、自魔本棄掉的魔物卡也算 | 使用者決定 | effect-tree-migration |
| P-018 | 魔本在第一頁時能不能用 | 不能(無法回翻,且會誤觸對手 P-019) | 已告知 | effect-tree-migration |
| P-010 / P-018 與 E-005 | E-005 算不算「自分の魔本をめくる/もどす効果」;限制卡本身算不算 | 都算。E-005 先翻過就不能用同方向的 P-010 / P-018;先用了 P-010 / P-018,E-005 同方向的結果不發生(E-005 仍可使用) | 使用者決定 | effect-tree-migration |
| 回翻 | 在第一頁「回翻」算不算用過回翻效果 | 不算;事件與 P-019 依實際回翻張數 | 已告知 | effect-tree-migration |
| 「次のバトル」(P-001 / S-019 / S-026) | 無術攻擊算不算下一場戰鬥 | 算:S-019 / S-026 不可防禦生效;P-001 限「用術攻擊」,不適用 | 已告知 | effect-tree-migration |
| M-008 | 何時決定是否減費;無法付原價時;本來費用為 0 時 | 宣告術時詢問;只付得起減費時直接使用;本来のコスト為 0(P-005、最後一頁、指示術)時不詢問、魔力不減;逾時預設不使用 | 已告知 | effect-tree-migration |
| S-026 / S-057 | 「オモテなら、次の効果を使える」要不要問是否使用 | 不問:宣告使用時就決定,且整張卡只有這個效果 | 使用者決定 | effect-tree-migration |

## 5. 已知限制與刻意簡化

- `Standby.then` 只能同步完成(見 2.4)。要支援會停下的 `then`,需先把開始階段改成可恢復的流程。
- 部分 `Choose` 的 `prompt`(= pending kind、前端 `choice.title.*` 的 key)仍含卡號,如 `e001_pick`。待另案改為依節點種類命名(`openspec/changes/todo.md`)。
- 房間狀態只存在單一行程的記憶體,樹只在啟動時建立一次,所以續體的 `path` 不會遇到樹版本不一致。若日後要持久化對局,需處理樹版本。
