# effect-tree — 設計

## 檔案分工

程式在 `src/gash/engine/effects/`:

| 檔案 | 內容 |
|---|---|
| `tree.py` | 節點、條件、選項規格、查詢規格,以及直譯器 |
| `tree_cards.py` | 所有卡片的登記(唯一的逐卡註冊檔;依卡號排序,排版規則見檔案開頭) |
| `primitives.py` | 節點共用的狀態操作(加魔力、翻頁、待命、擲幣⋯) |
| `registry.py` | 引擎與卡片效果之間的掛鉤表 |

## 節點是資料

- 節點是 `@dataclass(frozen=True)`,子節點放在欄位(`then`、`steps`、`otherwise`)。整棵樹在註冊時建好,存在 `EFFECTS["<卡號>:<掛鉤>"]`。
- 不用閉包 / lambda 組合:停下時必須把閉包存進狀態,狀態就不再是純資料。
- 節點與函式名稱語意化、不含卡號;`source`(卡號)由註冊層寫入 `ctx["source"]`。
- 通用節點組不出來時才新增專屬節點,新節點要有單元測試。

## 停點與續體

- 停下(等玩家選擇、擲幣確認、待命)時,只存續體 `{"effect_id", "path", "ctx", "floor"}`(`Run.cont` 產生),不存閉包。
  - `effect_id` 為 `"<卡號>:<掛鉤>"`;`path` 是停點節點本身的位置(子節點索引的 list)。
  - `ctx` 可 JSON 序列化,至少含 `player`、`source`。
  - `floor` 是上溯的下界:一般為 0;脫離式的待命子樹為 `len(path)+1`,觸發時不上溯到祖先。
- 恢復後沿 `path` 由深往淺「上溯」:父節點是 `Sequence` 時執行之後的兄弟節點;上溯經過節點時呼叫其 `leave(ctx)`(`AsOpponent` 在此把 `player` 換回來)。
- pending 依專屬鍵分派,不只看「有沒有續體」,否則會跳過 M-012 / M-019 的確認 resolver:
  - `data["tree_choice"]`(常數 `tree.CHOICE_KEY`):由樹建立的選擇(`Choose`、`CoinWithPaidReflip` 的付費重擲詢問),引擎的 `_handle_choose` 只在 pending 含此鍵時交給 `tree.resume`,再由節點的 `resume_choice` 續行。
  - `data["tree_cont"]`(常數 `tree.CONT_KEY`):擲幣確認鏈結束、待命觸發時的 callback payload,經通用 resolver `effect_tree_resume` 交給節點的 `resume`。`CoinWithPaidReflip` 的確認鏈停點也用這個鍵。
- 目標以穩定的 slot UID 綁定,執行當下才重新查找;目標已離場時無效果、不發事件,也不改選別的目標。

## 擲幣

- `Coin` 只在第一次執行時消耗 `game.rng`;恢復時不重擲。玩家合法要求的 M-012 / M-019 重擲照原流程消耗 RNG。
- 沒有確認鏈時 `flip_coins` 會同步呼叫 callback。為避免上溯與外層 `Sequence` 各續行一次,`Coin.run` 使用行程內、不進狀態的 in-flight 記號(`tree._flip`)判斷是同步完成還是停下。
- 擲幣者與效果擁有者分開記錄:擲幣者寫在 `data["flipper"]`,呼叫端的 `data["player"]` 不可被覆寫(E-020 曾因此把 MP 給錯人)。
- 付費重擲(E-011)的迴圈只在 `CoinWithPaidReflip` 節點內部,外層節點只續行一次。

## 待命

- `Standby` 是脫離式:排程後立即完成,外層照常續行;觸發時只解決 `then`,不上溯到祖先(續體的 `floor` 設為 `len(path)+1`)。
- `Standby.then` 只能同步完成,註冊時 `validate_tree` 檢查(`NegateNextDamageThisBattle` 也一樣)。原因是開始階段會一次觸發所有到期的待命,不是可恢復的流程;兩個會停下的 `then` 會互相覆寫 pending。
- 待命的時效(`Standby.data["expires"]`),移除由引擎處理(`engine._arm_next_battle_standbys`、`_end_battle`、回合結束的收尾):

| 值 | 移除時機 | 用於 |
|---|---|---|
| `"turn"`(預設) | 建立當回合結束 | 大多數「このターン中」 |
| `"next_start"` | 下回合開始階段觸發,該回合結束時移除 | E-001 |
| `"next_battle"` | 本回合下一場戰鬥開始時改為 `"battle"`;沒有戰鬥則回合結束時移除 | P-001、P-007、M-008、S-019、S-026(規則見 `card-effects/design.md`) |
| `"battle"` | 戰鬥結束 | P-006(「このバトル中」) |

## 登記方式

- 會執行動作的效果以效果樹登記:`reg.event`、`reg.spell_rider(on_declare / on_damage / on_win / on_defense_damaged)`、`reg.spell_nonbattle`、`reg.activated`、`reg.on_play`、`reg.on_discard`、`reg.start_phase`、`reg.trigger`。後面幾種的 `ctx` 含 `self_slot`,觸發器另含 `event`。
- 只回傳值的查詢不是效果,以不可變、可呼叫的規格物件登記,不經效果樹:`static_power`、`damage_immunity`、`spell_compat`、`spell_use_limit`、`activated(condition=)`、`damage_bonus`。
- 純資料以對應函式登記:`stack_on`、`max_copies`、`mamodo_attack`、`jammer`。
- 登記是原子操作:先完成全部檢查才寫入;同卡同掛鉤重複登記一律拒絕。
- `registry.py` 仍接受舊的 `@reg.xxx` 裝飾器,只剩測試使用;新卡一律用效果樹。

## 已知限制

- `Standby.then` 只能同步完成(見「待命」)。要支援會停下的 `then`,需先把開始階段改成可恢復的流程。
- 部分 `Choose` 的 `prompt`(= pending kind、前端 `choice.title.*` 的 key)仍含卡號,如 `e001_pick`。待另案改為依節點種類命名(`openspec/changes/todo.md`)。
- 續體的 `path` 依賴樹的形狀。房間狀態目前只存在單一行程的記憶體(`online-room`),樹只在啟動時建立一次,所以不會遇到樹版本不一致;若日後要持久化對局,需處理樹版本。
