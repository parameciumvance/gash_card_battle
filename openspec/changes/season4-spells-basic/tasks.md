# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 依效果文的行為測試:非香草的 16 張各至少一項,涵蓋擲幣正 / 反、S-118 兩個選項與非法選擇、S-115 對手沒有魔物、S-132 防禦被無效、S-143 戰鬥中變動、S-115 / S-118 與 S-057;香草與 S-114 以參數化測試驗證傷害與防禦獲勝時無效。

## 2. 實作

- [x] 2.1 新節點與欄位(design D2):`OpponentDidNotDefend`、`IncreaseThisSpellDamagePerHeads`、`OwnDiscardMamodoCards` 與 `SpellRider.power_per_count`、`RememberDeclaredTarget`、`DiscardRememberedPartner`;`DamageOpponentBookAndAllMamodo` 處理 S-057。
- [x] 2.2 登記 16 張(design D1、D2);i18n 選項標籤與魔力明細。
- [x] 2.3 `pending_cards.json` 移除 27 張;`test_season4_cards` 的已實作集合。

## 3. 驗證與文件

- [x] 3.1 快速測試組、相關瀏覽器測試、新 slow 測試(含這批卡的自我對戰);`openspec validate season4-spells-basic --strict`。(新測試 49 項、修正前 25 項失敗;快速組 1757 項;相關瀏覽器測試 201 項;自我對戰 9 局。金手指與構築器的產品 / 家族測試改為:電撃フェスタ有 Ex-050、バランシャ已有開放的戰術,只有尚未開放卡片的家族改用ゴーレン)
- [x] 3.2 reconciliation:`card-effects/design.md`「第 4 賽季第 1 批戰術的解讀」、capability map。
- [ ] 3.3 使用者確認。
