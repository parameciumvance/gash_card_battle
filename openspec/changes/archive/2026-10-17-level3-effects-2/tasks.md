## 1. 測試先行

- [x] 1.1 `tests/test_level3.py` 第 2 批:21 張依效果文的行為測試(擲幣正 / 反、選擇者、使用條件錯誤碼精確比對、時效跨回合),以及「第 2 批不在尚未開放清單」;確認修改前失敗
- [x] 1.2 限制的分類、無視與移除:M-038 無視 no_spells / no_attack_spell / 封鎖 / S-075;M-042 / E-031 無視 P-026 / E-043 / E-013 / S-035;M-051 不能保護;P-034 只移除自己的、整個複合效果移除;E-036 移除雙方三類;既有卡(E-002、E-024、E-025、P-014、E-013)行為不變的回歸測試;確認修改前失敗
- [x] 1.3 快照與 NPC:P-024 公開翻開頁(持有者看得到,其他視角不變)、事件卡 `cost` 含 M-040 加成、NPC 已知頁含 P-024 公開的頁;確認修改前失敗
- [x] 1.4 抓取工具:S-069 已知效果文錯誤的取代與「找不到原文時報錯」;確認修改前失敗

## 2. 引擎機制

- [x] 2.1 `engine.blocked(game, player, category, slot)` 與限制分類;既有檢查點改用它(design D1)
- [x] 2.2 無視:M-038 戰術、`protect_anyway`(M-042 / E-031)、`reg.cannot_protect`(M-051)(D2)
- [x] 2.3 `RemoveRestrictions` 與 `restrictions_removed` 事件;待命的分類標記(D3)
- [x] 2.4 新時效 `DUR_UNTIL_END_OWN_NEXT_TURN` 與 `no_effects_and_spells`(D4)
- [x] 2.5 保護限制:`protect_only`、`only_mamodo`、`_eligible_protectors` 的檢查順序(D5)
- [x] 2.6 事件卡費用 `event_cost`(M-040)、`damage_regardless`(S-100)、S-069 / S-070 / S-078 / S-079 / P-028 所需節點(D6)

## 3. 卡片登記與資料

- [x] 3.1 パピプリオ、ゼオン、ロップス、ウォンレイ 18 張與 E-031 / E-036 / E-043 登記(依卡號排序,香草戰術註記)
- [x] 3.2 `scrape_ja_effects.py` 的 `KNOWN_TEXT_ERRORS`;修正 S-069 的 `cards_ja.csv`、`cards.json`、文字檔(繁中、英文依修正後重寫,重產日文與簡中)(D7)
- [x] 3.3 `data/pending_cards.json` 移除 21 張;第 1 組測試全過

## 4. 快照、前端與 NPC

- [x] 4.1 `views`:P-024 公開翻開頁、事件卡 `cost`;`determinize`:P-024 的已知頁
- [x] 4.2 前端:事件卡以快照 `cost` 顯示與判斷;P-024 時對手翻開頁的卡面;瀏覽器測試
- [x] 4.3 記錄 `restrictions_removed`、作用中效果的新文字(zh-TW / en / ja,`build_zh_cn.py`)
- [x] 4.4 決策種類沿用既有 `choice.title.*`;新的選項標籤(S-070 二選一)在 `app.js` 對應

## 5. 驗證

- [x] 5.1 `pytest` 全過;`openspec validate --all --strict` 沒有新增失敗
- [x] 5.2 本機實際操作:M-038 + S-075、P-026 / E-031 的保護、P-034 / E-036 移除、P-024 顯示、S-069 / S-070 / S-078(自由調查時間)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 回 `card-effects`、`game-engine`、`battle-api`、`battle-ui`、`npc-opponent`、`card-data` 主 spec(歸檔時)
- [x] 6.2 `card-effects/design.md`:限制分類表與 `blocked`、無視與移除、新時效;「行為決定與理由」加入第 2 批的解讀(Confirmed,2026-10-15)與「不能用戰術攻擊也算不能使用戰術」;`game-engine/design.md` 保護者的檢查順序;`battle-api/design.md` P-024 與事件卡費用;`npc-opponent/design.md` 已知頁;`card-data/design.md` 已知效果文錯誤
- [x] 6.3 capability map 視需要更新

## Workflow follow-up

- 歸檔:`openspec archive level3-effects-2 -y`,在 `level3-effects-2` 分支提交;合併 main 與推送等使用者指示
- 第 3 批(エシュロス、ティオ、バリー、フリガロ + E-028 / E-034 / E-035)另開 change,先 explore
