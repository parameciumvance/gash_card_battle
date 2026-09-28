> 這是效果樹遷移的**權威進度來源**,跨多次工作階段使用。每次工作階段:
> 1. 讀本檔,挑一批未勾選的卡(建議照本檔的分組與排序,由上而下)。
> 2. 照 design.md 的三步驟(補特徵測試 → 需要才新增節點 → 遷移 + 全量測試)進行。
> 3. 完成後立刻把該批的 `- [ ]` 改成 `- [x]`,並在後面補上完成的 commit hash。
> `python -m pytest` 必須隨時保持全綠;每項卡名後的掛鉤類型取自 `registry.py` 的登記表,只供辨識用。

## 0. 已完成(effect-tree-interpreter 與後續兩批,列此供進度總覽,非本 change 產出)

- [x] E-001 (event) — `07cd466`/`7d6bedf`(effect-tree-interpreter)
- [x] S-004, S-014 (rider.on_damage)、S-021, S-025 (rider.on_declare)、S-026 (spell_nonbattle) — `7d6bedf`
- [x] S-027, S-035, S-037, S-040, S-041, S-045, S-046, S-057 — `5c3c656`
- [x] E-005, E-006, E-022, E-026 (event) — `701571a`

## 1. 術卡(spells.py)剩餘 19 卡(+2 張初次盤點漏列)— 已有現成掛鉤入口,優先做

- [x] S-003 ラシルド(rider.counter,純旗標)— `10af584`
- [x] S-007 フリズド(rider.on_damage)— `10af584`
- [x] S-009 グラビレイ(rider.on_damage)— `10af584`
- [x] S-011 アイアン・グラビレイ(rider.on_damage)— `10af584`
- [x] S-016 ゼルク(rider.on_declare)— `10af584`
- [x] S-017 ゼルセン(rider.on_declare)— `10af584`
- [x] S-019 ウルク(rider.on_win)— `f15915e`
- [x] S-020 ポルク(rider.on_win)— `f15915e`
- [x] S-030 ラシルド(rider.counter,純旗標)— `10af584`
- [x] S-031 バオウ・ザケルガ(rider.on_declare)— `10af584`
- [x] S-032 レイス(damage_cap,純旗標;初次盤點漏列)— `10af584`
- [x] S-033 グラビレイ(rider.on_damage)— `10af584`
- [x] S-034 ギガノ・レイス(damage_cap,純旗標;初次盤點漏列)— `10af584`
- [x] S-036 ディオガ・グラビドン(rider.on_win)— `f15915e`
- [x] S-038 ジキルガ(rider.on_damage)— `10af584`
- [x] S-039 ラドム(rider.on_damage)— `10af584`
- [x] S-042 ビライツ(rider.damage_bonus)— `f15915e`
- [x] S-043 レリ・ブルク(spell_nonbattle) — `972a5fe`
- [x] S-048 ゼベルオン(spell_nonbattle) — `972a5fe`
- [x] S-056 目をそらすな!(rider.on_defense_damaged)— `f15915e`
- [x] S-058 ザケル(rider.injure_instead,純旗標)— `10af584`

**盤點修正**:初次用程式盤點剩餘卡時,只計入 `SpellRider` 的 `on_declare`/`on_damage`/`on_win`/
`counter`/`damage_bonus`/`injure_instead`/`on_defense_damaged`,漏算了 `damage_cap`,所以 S-032/S-034
沒列入。它們和 S-003/S-030/S-058 一樣只有旗標、沒有邏輯,不需要樹節點,直接把原本那一行
`reg.spell_rider(...)` 搬到 `tree_cards.py` 即可(讓所有卡的註冊集中在一個檔案)。

**術卡已全部遷完**:S-043 / S-048 於 `972a5fe` 與 E-012 / E-016 / E-017 一起以「從魔本選頁」的選項規格遷移,`spells.py` 已刪除。

`f15915e` 補上了 `rider.on_win` / `rider.on_defense_damaged` 的樹入口;`damage_bonus` 因為要回傳
數值、不是效果,改用不可變可呼叫的規格物件(`DamageBonusIfAttackTotalAtLeast`),不經效果樹。

## 2. 事件卡(events.py)剩餘 22 卡 — 全部完成,`events.py` 已於 `ca87c12` 刪除

- [x] E-002 ティーナ — `ebb4027`
- [x] E-003 ブリ — `ebb4027`
- [x] E-004 友情のカレー — `ebb4027`
- [x] E-007 木山つくし — `ebb4027`
- [x] E-008 水野鈴芽 — `ebb4027`
- [x] E-009 やさしい王様 — `ebb4027`
- [x] E-010 やさしい清麿 — `ebb4027`
- [x] E-011 鉄のフォルゴレ — `ca87c12`
- [x] E-012 ガッシュ登場 — `972a5fe`
- [x] E-013 ナオミちゃん — `ebb4027`
- [x] E-014 ウマゴン — `ebb4027`
- [x] E-015 バルカン300 — `ebb4027`
- [x] E-016 高嶺清太郎 — `972a5fe`
- [x] E-017 高嶺華 — `972a5fe`
- [x] E-018 フォルゴレのダンス — `ca87c12`
- [x] E-019 清麿の怒り — `ebb4027`
- [x] E-020 恵のコンサート — bug 修正 `71a699c`、遷移 `1a97b92`
- [x] E-021 敵じゃない人がいる — `ebb4027`
- [x] E-023 戦いの意義 — `ebb4027`
- [x] E-024 プロフェッサー・ダルタニアン — `ebb4027`
- [x] E-025 ヨポポの踊り — `ebb4027`
- [x] E-027 無二の親友 — `ca87c12`

## 3. 術卡以外的掛鉤入口先補齊(進 mamodo.py/partners.py 之前)

- [x] 3.1 `registry.py`/`tree.py` 補 `activated` 的樹入口(仿 `register_event`:mode=declare/mp/discard、timing、per_game、condition 皆需保留)。
- [x] 3.2 補 `static_power`、`on_play`、`start_phase`、`on_discard` 的樹入口。
- [x] 3.3 補 `trigger.<event_type>`、`damage_immunity`、`spell_compat`、`mamodo_attack` 的樹入口(這幾種較少見,視 mamodo.py/partners.py 實際需求決定要不要先做)。

入口於 `2b1be88` 補齊並以 17 張魔物卡驗證。`trigger` / `damage_immunity` / `spell_compat` 的入口已有單元測試,實際卡片(M-023 / M-028 / M-029 / M-031)在下一批遷移。`STACK_ON` / `MAX_COPIES` / `MAMODO_ATTACK` 等純資料登記仍留在 `mamodo.py`,與 M-024 / M-027 一起處理。借用對手夥伴(E-010)時,夥伴效果的 `self_slot` 會是對手的魔物,遷移夥伴卡時要留意。

## 4. 魔物卡(mamodo.py)29 卡 — 全部完成,`mamodo.py` 已於 `eb3daa1` 刪除

- [x] M-001 ガッシュ・ベル(activated) — `2b1be88`
- [x] M-002 ガッシュ・ベル(start_phase) — `2b1be88`
- [x] M-003 ガッシュ・ベル(static_power) — `2b1be88`
- [x] M-004 レイコム(static_power) — `2b1be88`
- [x] M-005 ブラゴ(activated) — `2b1be88`
- [x] M-006 ゴフレ(on_play) — `2b1be88`
- [x] M-007 ゴフレ(変身後)(on_play) — `2b1be88`
- [x] M-008 スギナ(activated) — `2b1be88`
- [x] M-009 コルル(on_discard) — `2b1be88`
- [x] M-010 コルル(変身後)(activated) — `2b1be88`
- [x] M-011 フェイン(activated) — `f87fc87`
- [x] M-013 キャンチョメ(activated) — `2b1be88`
- [x] M-014 ティオ(static_power) — `2b1be88`
- [x] M-015 ティオ(activated) — `2b1be88`
- [x] M-016 ガッシュ・ベル(activated) — `f87fc87`
- [x] M-017 ブラゴ(activated) — `2b1be88`
- [x] M-018 ブラゴ(activated) — `2b1be88`
- [x] M-019 キャンチョメ(activated) — `2b1be88`
- [x] M-020 ティオ(activated) — `f87fc87`
- [x] M-021 ハイド(activated) — `f87fc87`
- [x] M-022 ゾフィス(activated) — `f87fc87`
- [x] M-023 ポッケリオ(spell_compat) — `f87fc87`
- [x] M-025 ロブノス(完全体)(on_play) — `4e70210`(依效果文修正)
- [x] M-026 マルス(activated) — `eb3daa1`(依效果文改為ジャマー)
- [x] M-027 バルトロ(アーマー体)(mamodo_attack) — `f87fc87`
- [x] M-028 バルトロ(本体)(trigger.stack_detached) — `f87fc87`
- [x] M-029 ゼオン(activated, spell_compat) — `d995cc9`(依效果文修正)
- [x] M-030 ヨポポ(activated) — `2b1be88`
- [x] M-031 キクロプ(damage_immunity) — `f87fc87`
另:M-024(`max_copies` 與「二身一体」)原本不在清單中(盤點時只看效果掛鉤),`f87fc87` 移入資料登記、`29e77c0` 補上原本缺漏的「二身一体」效果。

## 5. 夥伴卡(partners.py)19 卡 — 全部完成,`partners.py` 已於 `e7141c2` 刪除

- [x] P-001 高嶺清麿(activated) — `e7141c2`
- [x] P-002 細川(activated) — `e7141c2`
- [x] P-003 シェリー(activated) — `e7141c2`
- [x] P-004 連次(activated) — `e7141c2`
- [x] P-005 春彦(activated) — `e7141c2`(依使用者決定:以使用術的魔物判定)
- [x] P-006 しおり(activated) — `e7141c2`(依效果文修正)
- [x] P-007 清兵衛(activated) — `e7141c2`(依使用者決定:以使用術的魔物判定)
- [x] P-008 パルコ・フォルゴレ(activated) — `e7141c2`(依效果文修正)
- [x] P-009 大海恵(activated) — `e7141c2`(依效果文修正)
- [x] P-010 高嶺清麿(activated) — `e7141c2`(依效果文修正)
- [x] P-011 窪塚泳太(activated) — `e7141c2`
- [x] P-012 シェリー(activated) — `e7141c2`
- [x] P-013 ココ(trigger.mamodo_discarded / trigger.card_discarded) — `e7141c2`(依效果文修正)
- [x] P-014 ペリコ(activated) — `e7141c2`
- [x] P-015 リュック(activated) — `e7141c2`
- [x] P-016 レンブラント(activated) — `e7141c2`
- [x] P-017 ステング(activated) — `e7141c2`
- [x] P-018 ジェム(activated) — `e7141c2`(保留「第一頁不能用」的限制,見 design.md 第 4 節)
- [x] P-019 イギリス紳士(trigger.pages_turned) — `e7141c2`(依效果文修正)

M-008 的「スギナの術」判定與 P-005 / P-007 一起改為以使用術的魔物判定(`e7141c2`)。
照原樣遷移的 11 張,補上依效果文的行為測試並在遷移前的程式(HEAD 的 worktree)上確認通過;
依效果文修正的 8 張(含 M-008),測試在舊寫法上確認失敗。

遷移後發現的兩項差異,使用者決定以效果文為準,於 `c551b9f` 修正(見 design.md 第 4 節):

- [x] P-001 / P-007 / M-008(及同節點的 S-019 / S-026)「このターン中の次のバトル」只作用於本回合的下一場戰鬥 — `c551b9f`
- [x] P-010 / P-018「自分の魔本をめくる/もどす効果を合計1回」把 E-005 計入;回翻依實際張數 — `c551b9f`

## 6. 收尾(全部遷完之後)

- [x] 6.1 確認 `mamodo.py`/`partners.py`/`events.py` 只剩檔案說明註解(或整個檔案可以刪除),`tree_cards.py` 是唯一的逐卡註冊檔(`spells.py` 已於 `972a5fe` 刪除)。— 四個舊檔都已刪除(`events.py` `ca87c12`、`mamodo.py` `eb3daa1`、`partners.py` `e7141c2`)
- [x] 6.2 更新 README「卡片效果的寫法」段落與 `openspec/changes/todo.md`,移除「其餘卡片遷移」項目。
- [ ] 6.3 依 AGENTS.md 流程:`/opsx:sync` 同步 delta spec 回主 spec,再 `/opsx:archive` 歸檔本 change。
