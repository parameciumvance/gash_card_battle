# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 依效果文的行為測試:6 張的主要分支、使用條件不成立被拒絕(錯誤碼精確)、期間中上場的魔物、S-121 的各個選擇處、S-144 的各類效果、時效到期。

## 2. 實作

- [x] 2.1 引擎:`mamodo_attack_spec` / `mamodo_defense_spec`(D1)、依家族的不受傷害與 `selectable_opponent_slots`(D2)、非戰鬥戰術的 `user_slot` 與 `spell_no_user`(D3、D4)、`NO_DISCARD_COST_EFFECTS`(D5)、`any_spell` 的頁範圍(D6)。
- [x] 2.2 節點與登記;快照與 NPC 改用新的查詢函式;i18n。
- [x] 2.3 `pending_cards.json` 移除 6 張;已實作集合。

## 3. 驗證與文件

- [x] 3.1 快速測試組、相關瀏覽器測試、新 slow 測試;`openspec validate season4-spells-2b --strict`。(新測試 28 項;快速組 1816 項;相關瀏覽器測試 214 項;第 4 賽季戰術三批的自我對戰 27 局)
- [x] 3.2 reconciliation:`card-effects/design.md`、`game-engine/design.md`。
- [x] 3.4 使用者決定 S-095 改為之後上場的也算:先寫測試確認修正前失敗,改用 `FamilyNoDamage(duration=DUR_TURN)`,移除 `FamilyNoDamageThisTurn`。
- [ ] 3.3 使用者確認。
