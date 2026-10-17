## 1. 測試先行

- [x] 1.1 時機測試(修改前失敗):S-058 / S-057 宣告時選對手魔物、獲勝時不再詢問、選定魔物離場時沒有這份傷害;S-036 / S-101 只對宣告時在場的魔物;S-069 宣告時擲幣、獲勝時不再擲;S-070 宣告時選模式與魔物;S-021 戰鬥中效果期間攻擊未被無效、雙方 pass 後才無效(含防禦被 P-017 無效時不生效)
- [x] 1.2 回歸:S-004 / S-014 / S-037 / S-039 / S-078 維持造成傷害時;受影響卡片的既有測試依新時機改寫(不改變其驗證的效果本身)

## 2. 引擎與效果

- [x] 2.1 `RememberInBattle` / `BattleRemembered` 與相關結算節點(design D1)
- [x] 2.2 宣告時選擇對手魔物並在獲勝時使用(S-058、S-057、S-070)(D2)
- [x] 2.3 S-036 / S-101 宣告時的魔物清單(D3);S-069 宣告時擲幣(D4)
- [x] 2.4 S-021 於効果の使用的最後無效(D5)
- [x] 2.5 NPC 在宣告時的決策能走完(自我對戰與單元測試)

## 3. 文件

- [x] 3.1 AGENTS.md 的規則來源改為 atwiki 規則頁,加上「效果文明寫時機時以效果文為準」(D6)

## 4. 驗證

- [x] 4.1 `pytest` 全過;`openspec validate --all --strict` 沒有新增失敗
- [x] 4.2 本機實際操作:S-058、S-070、S-021(自由調查時間)

## 5. Reconciliation(指南 §13)

- [x] 5.1 同步 delta spec 回 `game-engine`、`card-effects` 主 spec(歸檔時)
- [x] 5.2 `game-engine/design.md`:宣告時結果存於 `battle.data`、規則出處;`card-effects/design.md`「行為決定與理由」:效果文明寫時機時以效果文為準(使用者確認,2026-10-17)、7 張的時機
- [x] 5.3 capability map 視需要更新

## Workflow follow-up

- 歸檔:`openspec archive declare-time-resolution -y`,在 `declare-time-resolution` 分支提交;合併 main 與推送等使用者指示
- 回到第 3 批(level3-effects-3)的 explore:確認其餘解讀(含 S-098 重用方式),S-064 / S-068 / S-104 依宣告時規則
