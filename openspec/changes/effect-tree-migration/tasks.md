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

## 1. 術卡(spells.py)剩餘 19 卡 — 已有現成掛鉤入口,優先做

- [ ] S-003 ラシルド(rider.counter)
- [ ] S-007 フリズド(rider.on_damage)
- [ ] S-009 グラビレイ(rider.on_damage)
- [ ] S-011 アイアン・グラビレイ(rider.on_damage)
- [ ] S-016 ゼルク(rider.on_declare)
- [ ] S-017 ゼルセン(rider.on_declare)
- [ ] S-019 ウルク(rider.on_win)
- [ ] S-020 ポルク(rider.on_win)
- [ ] S-030 ラシルド(rider.counter)
- [ ] S-031 バオウ・ザケルガ(rider.on_declare)
- [ ] S-033 グラビレイ(rider.on_damage)
- [ ] S-036 ディオガ・グラビドン(rider.on_win)
- [ ] S-038 ジキルガ(rider.on_damage)
- [ ] S-039 ラドム(rider.on_damage)
- [ ] S-042 ビライツ(rider.damage_bonus)
- [ ] S-043 レリ・ブルク(spell_nonbattle)
- [ ] S-048 ゼベルオン(spell_nonbattle)
- [ ] S-056 目をそらすな!(rider.on_defense_damaged)
- [ ] S-058 ザケル(rider.injure_instead)

`rider.on_win`(S-019/S-020/S-036)、`rider.counter`(S-003/S-030)、`rider.damage_bonus`(S-042)、
`rider.injure_instead`(S-058)、`rider.on_defense_damaged`(S-056)這幾種掛鉤目前 `tree.py` 還沒有
對應的樹入口(`registry.py` 的 `spell_rider` 目前只接 `on_damage`/`on_declare` 兩種樹),
遷移這些卡之前要先仿照 `rider_hook` 的模式補上。

## 2. 事件卡(events.py)剩餘 22 卡

- [ ] E-002 ティーナ
- [ ] E-003 ブリ
- [ ] E-004 友情のカレー
- [ ] E-007 木山つくし
- [ ] E-008 水野鈴芽
- [ ] E-009 やさしい王様
- [ ] E-010 やさしい清麿
- [ ] E-011 鉄のフォルゴレ — **需要專屬重試節點,見 design.md「已知阻礙」**
- [ ] E-012 ガッシュ登場
- [ ] E-013 ナオミちゃん
- [ ] E-014 ウマゴン
- [ ] E-015 バルカン300
- [ ] E-016 高嶺清太郎
- [ ] E-017 高嶺華
- [ ] E-018 フォルゴレのダンス
- [ ] E-019 清麿の怒り
- [ ] E-020 恵のコンサート — **遷移前需使用者決定是否連同既有 MP 分配 bug 一併修正,見 design.md「已知阻礙」**
- [ ] E-021 敵じゃない人がいる
- [ ] E-023 戦いの意義
- [ ] E-024 プロフェッサー・ダルタニアン
- [ ] E-025 ヨポポの踊り
- [ ] E-027 無二の親友

## 3. 術卡以外的掛鉤入口先補齊(進 mamodo.py/partners.py 之前)

- [ ] 3.1 `registry.py`/`tree.py` 補 `activated` 的樹入口(仿 `register_event`:mode=declare/mp/discard、timing、per_game、condition 皆需保留)。
- [ ] 3.2 補 `static_power`、`on_play`、`start_phase`、`on_discard` 的樹入口。
- [ ] 3.3 補 `trigger.<event_type>`、`damage_immunity`、`spell_compat`、`mamodo_attack` 的樹入口(這幾種較少見,視 mamodo.py/partners.py 實際需求決定要不要先做)。

## 4. 魔物卡(mamodo.py)29 卡

- [ ] M-001 ガッシュ・ベル(activated)
- [ ] M-002 ガッシュ・ベル(start_phase)
- [ ] M-003 ガッシュ・ベル(static_power)
- [ ] M-004 レイコム(static_power)
- [ ] M-005 ブラゴ(activated)
- [ ] M-006 ゴフレ(on_play)
- [ ] M-007 ゴフレ(変身後)(on_play)
- [ ] M-008 スギナ(activated)
- [ ] M-009 コルル(on_discard)
- [ ] M-010 コルル(変身後)(activated)
- [ ] M-011 フェイン(activated)
- [ ] M-013 キャンチョメ(activated)
- [ ] M-014 ティオ(static_power)
- [ ] M-015 ティオ(activated)
- [ ] M-016 ガッシュ・ベル(activated)
- [ ] M-017 ブラゴ(activated)
- [ ] M-018 ブラゴ(activated)
- [ ] M-019 キャンチョメ(activated)
- [ ] M-020 ティオ(activated)
- [ ] M-021 ハイド(activated)
- [ ] M-022 ゾフィス(activated)
- [ ] M-023 ポッケリオ(spell_compat)
- [ ] M-025 ロブノス(完全体)(on_play)
- [ ] M-026 マルス(activated)
- [ ] M-027 バルトロ(アーマー体)(mamodo_attack)
- [ ] M-028 バルトロ(本体)(trigger.stack_detached)
- [ ] M-029 ゼオン(activated, spell_compat)
- [ ] M-030 ヨポポ(activated)
- [ ] M-031 キクロプ(damage_immunity)

## 5. 夥伴卡(partners.py)19 卡

- [ ] P-001 高嶺清麿(activated)
- [ ] P-002 細川(activated)
- [ ] P-003 シェリー(activated)
- [ ] P-004 連次(activated)
- [ ] P-005 春彦(activated)
- [ ] P-006 しおり(activated)
- [ ] P-007 清兵衛(activated)
- [ ] P-008 パルコ・フォルゴレ(activated)
- [ ] P-009 大海恵(activated)
- [ ] P-010 高嶺清麿(activated)
- [ ] P-011 窪塚泳太(activated)
- [ ] P-012 シェリー(activated)
- [ ] P-013 ココ(trigger.mamodo_discarded)
- [ ] P-014 ペリコ(activated)
- [ ] P-015 リュック(activated)
- [ ] P-016 レンブラント(activated)
- [ ] P-017 ステング(activated)
- [ ] P-018 ジェム(activated)
- [ ] P-019 イギリス紳士(trigger.pages_turned)

## 6. 收尾(全部遷完之後)

- [ ] 6.1 確認 `mamodo.py`/`partners.py`/`events.py`/`spells.py` 只剩檔案說明註解(或整個檔案可以刪除),`tree_cards.py` 是唯一的逐卡註冊檔。
- [ ] 6.2 更新 README「卡片效果的寫法」段落與 `openspec/changes/todo.md`,移除「其餘卡片遷移」項目。
- [ ] 6.3 依 AGENTS.md 流程:`/opsx:sync` 同步 delta spec 回主 spec,再 `/opsx:archive` 歸檔本 change。
