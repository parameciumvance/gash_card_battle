# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 依規則寫測試:S-025 / S-069(防禦)/ S-106 在戰鬥中效果的時機攻擊尚未無效,雙方 pass 後才無效;S-025、S-027、S-069、S-079、S-106 防禦被 P-009 等無效時效果不解決;S-106 攻擊已先被無效時不翻魔書;S-021、S-095 維持現行行為。確認新行為的測試在修正前失敗。

## 2. 引擎

- [x] 2.1 新時機 `EffectsEnd`(待命種類 `effects_end`,`expires: "battle"`);`_resolve_showdown` 依建立順序解決,防禦被無效時移除不解決(design D1)。
- [x] 2.2 改寫 S-021、S-025、S-027、S-069、S-079、S-095、S-106(design D2);移除 `NegateAttackAtEffectsEnd` 與 `defender_no_damage_family` 特例;S-106「そうしたなら」的條件(`AttackNotNegated`);效果節點 `AtEffectsEnd`(登記檔不能有函式,所以做成 `Standby` 子類別)、`FamilyNoDamageThisTurn`。
- [x] 2.3 i18n `effect.standby.effects_end`(zh-TW / en / ja,zh-CN 以工具產生)。

## 3. 驗證與文件

- [x] 3.1 調整以「宣告後攻擊立即無效」為前提的既有測試;快速測試組與相關瀏覽器測試;`openspec validate defense-effects-timing --strict`。(新測試 11 項修正前全部失敗;快速組 1708 項;相關瀏覽器測試 71 項;改寫 10 個舊測試為新時機:test_cards 3、test_effect_characterization 5、test_level3 2)
- [x] 3.2 reconciliation:`card-effects/design.md`(行為決定與理由:防禦效果的解決時機)、`game-engine/design.md`。
- [ ] 3.3 使用者確認。

## Workflow follow-up

- 歸檔前依指南 §13 同步 delta spec;歸檔後以 `--no-ff` 合併回 `dev`;接著從新的 `dev` 開第 4 賽季批次 1。
