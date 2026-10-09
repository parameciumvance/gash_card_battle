## Context

動機見 proposal.md。相關現況:

- **E-021**:`Sequence(HealFirstInjuredMamodo(), GainMp(2))`;`HealFirstInjuredMamodo` 自動回復第一隻負傷魔物。既有測試 `test_e021_heals_first_injured_and_gains_2mp` 驗證的是這個不符效果文的行為。
- **E-010**:`Choose(OpponentPartneredMamodo(), then=BorrowPartner())`。`OpponentPartneredMamodo` 列出對手所有裝搭檔的魔物(含 P-013、P-019)。`BorrowPartner` 加一個 `borrow_partner` modifier,`data={"slot_uid", "card"}`。使用時走 `_use_field_ability`:`zone: "partner"` 加對手魔物的 `slot_uid`,找到相符的 modifier 才算借用,付費、不棄卡、`data["used"]=True`;找不到該 slot 或搭檔已換就不能用。
- **前端**:沒有任何借用入口。`partnerButtons(p, slot)` 只看 `iControl(p)`,本機模式兩方都能操作,所以點對手的搭檔會出現對手自己的按鈕。
- **快照**:`_effects_view` 只公開 `_PUBLIC_EFFECT_DATA` 白名單(含 `card`),不含 `used`,`target_slot` 為 null。
- **NPC**:`npc/candidates._field_abilities` 在有 `borrow_partner` 時,對對手每個有效果的搭檔各送一個 `use_field_ability`。
- **P-003 / P-004**:`condition=All(OwnAttackBy(...), NoBattleDamageModifierFrom(...))`,效果 `IncreaseAttackDamage` / `DoubleAttackDamage` 無條件加在 `battle.attack_slot` 上。**P-006**:`condition=OwnFieldHas("M-010")`,效果 `NegateNextDamageThisBattle` 本身在沒有 M-010 時就不排程。
- 搭檔的效果樹都以 `ctx["player"]` 為準,沒有任何一張使用 `self_slot`。

## Goals / Non-Goals

**Goals:**
- E-021、E-010、P-003 / P-004 / P-006 依效果文運作,並有依效果文的測試。
- 借用的效果有清楚、與持有者自用分開的入口與指令。

**Non-Goals:**
- 不改其他搭檔「沒有對象就拒絕」的條件(P-008、P-009、P-011、P-016、P-017,以及 P-010 / P-018 的回合限制):那些效果沒有對象就什麼都做不到,維持現有的解讀。
- 不改 M-026 ジャマー的範圍(搭檔效果與借用效果都不觸發)。

## Decisions

### D1:E-021 以兩段選擇實作

```
Sequence(
  Choose(E021Effects(first=True), bind="first", prompt="pick_effect"),   -- 回復 / MP+2(沒有負傷魔物時只有 MP+2,單一選項自動)
  RunChosenEffect("first"),                                               -- 回復 → Choose(OwnInjuredMamodo, prompt="pick_own_injured_mamodo") → 回復
  Choose(E021Effects(after="first"), bind="second", prompt="pick_effect"),-- 另一個效果 / skip(另一個是回復但沒有負傷魔物時不問)
  RunChosenEffect("second"),
)
```

- 選項來源列出可用的效果:`{"value": "heal", "label": "heal_injured"}`、`{"value": "mp", "label": "gain_mp_2"}`;第二段多一個 `{"value": None, "label": "skip"}`。
- 實際寫法依效果樹既有節點組合(`Choose`、`When`、`Bound`、`Sequence`),必要時新增選項來源與「依綁定值分支」的節點;節點名稱語意化、不含卡號。
- 回復改由玩家選擇,沿用決策種類 `pick_own_injured_mamodo`;效果選擇新增決策種類 `pick_effect`(「選擇要使用的效果」),補 `choice.title.pick_effect` 與選項標籤 `heal_injured`、`gain_mp_2` 的前端對應。
- `HealFirstInjuredMamodo` 不再有使用者時刪除。

### D2:E-010 借用以卡號記錄,改用獨立指令

- 候選:新的選項來源(或 `OpponentPartneredMamodo` 加參數)排除帶「このカードが場にある→」的搭檔。判定以登記方式為準:搭檔沒有 `reg.ACTIVATED`(只有 `reg.trigger` 的被動效果,即 P-013、P-019)就排除。E-010 的使用前提改為「有可選的搭檔」。
- `BorrowPartner` 的 modifier 改為 `data={"card": <卡號>, "used": False}`,不再記 slot。
- 新指令 `{"type": "use_borrowed_effect", "player": p}`,由 `engine._use_borrowed_effect` 處理:
  - 找自己本回合未用過的 `borrow_partner`,沒有則 `ability.none`;已用過則 `ability.used`。
  - 取該卡號的 `reg.ACTIVATED`;依其 `timing` 檢查(`ability.timing`)、搭檔效果失效限制(`ability.partner_restricted`)、MP(`ability.mp`)、`condition`(`ability.condition`,呼叫時 `slot=None`)。
  - 付費、`data["used"] = True`,發出 `ability_used`(`player` 為使用者、`zone: "borrowed"`、`slot: null`、`via: "E-010"`),執行 handler(`slot=None`)。不棄任何卡、不記 `used_abilities`(持有者與借用者的使用次數各自獨立)。
  - 可使用的時點與一般場上效果相同:非戰鬥中自己有行動權、戰鬥中效果步驟輪到自己。
- `_use_field_ability` 移除借用分支(對手的 slot 一律 `ability.target`)。
- `register_slot_hook` 的 handler 在 `slot` 為 None 時 `self_slot` 給 None;搭檔效果都不用它。
- 替代方案:沿用 `use_field_ability` 加 `zone: "borrowed"`。不採用:它的必要參數(slot)在借用時沒有意義,分開更清楚。

### D3:快照與前端

- `_effects_view` 的白名單加入 `used`(bool),借用 modifier 本來就帶 `card`;借用項目另附 `ability`(該卡的 `_ability_view`,含 timing),前端據此判斷可否使用。前端從 `S.effects` 找 `kind === "borrow_partner"`、`owner === 自己`、`!used` 的項目。「作用中效果」清單在已使用時改顯示 `effect.modifier.borrow_partner.used`。
- 行動欄在可行動時加「借用效果:〈卡名〉」(`ui.borrowed_effect`);按下開啟放大檢視,ctx 為 `{kind: "borrowed", p}`;`zoomActions` 對此 ctx 回傳「使用」按鈕,可用性沿用 `abilityUsableNow`(加上搭檔效果失效的判斷),送出 `use_borrowed_effect`。modifier 消失或已使用時檢視自動關閉。
- 記錄:`ability_used` 帶 `via` 時顯示「{player} 以《E-010》使用《卡名》的效果」(`log.ability_used_borrowed`)。聚焦沿用 `ability_used` 的卡片聚焦。
- 本機模式點對手的搭檔仍是對手自己的按鈕(那是對手的合法操作),不另外處理。

### D4:NPC

`_field_abilities` 的借用分支改為:有自己未用過的 `borrow_partner` 時加入 `{"type": "use_borrowed_effect"}`。

### D5:P-003 / P-004 / P-006 移除使用條件

- P-003:`effect=When(All(OwnAttackBy("ブラゴ"), NoBattleDamageModifierFrom("P-003")), then=IncreaseAttackDamage(2))`,沒有 `condition`;P-004 同理。`OwnAttackBy`、`NoBattleDamageModifierFrom` 目前只有啟動條件介面 `__call__(game, player, slot)`,加上 `test(game, ctx)` 讓它們也能當 `When` 條件。
- 「重複しない」以 `source` 判定(借用時 source 同樣是 P-003),所以持有者與借用者在同一場都用時只有第一次有效。
- P-006:移除 `condition`,效果不變(沒有 M-010 時不排程)。
- `card-effects/design.md` 記錄此行為決定(專案負責人確認,`Confirmed`)。

### 行為決定(reconciliation 時寫入 `card-effects/design.md`「行為決定與理由」)

- **E-021 由玩家選擇效果、順序與回復對象**:「片方または両方を、好きな順で」「1体を選び」。沒有負傷魔物時只有 MP +2。專案負責人確認,`Confirmed`。
- **E-010 排除被動搭檔、以卡號記錄、離場後仍可使用**:對象在使用 E-010 時就決定。專案負責人確認,`Confirmed`。
- **借用效果中「自分」指使用者**:「自分のものとして使う」。專案負責人確認,`Confirmed`。
- **借用與持有者的使用次數各自計算**:效果文只限制「このターン中1回だけ」借用者;持有者是否能在同回合自用不受影響。專案負責人確認,`Confirmed`。
- **P-003 / P-004 / P-006 的作用對象不是使用條件**:效果文只限定作用對象,對象不成立時能用但沒有效果;持有者與借用一致。專案負責人確認,`Confirmed`。

## Risks / Trade-offs

- [舊存檔的 `borrow_partner` modifier 帶 `slot_uid`] → 對局狀態只在記憶體中,部署會清空,不需要相容。
- [E-021 多一兩次決策,逾時代打要有安全預設] → 逾時代打取第一個選項;第二段的第一個選項是另一個效果,屬可接受的預設。實作時確認逾時代打對 `pick_effect` 有效。
- [借用效果的 handler 拿到 `slot=None`] → 以測試涵蓋全部 17 張可借用的搭檔至少能被借用使用而不出錯。
