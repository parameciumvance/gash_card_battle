## 1. 測試先行

- [x] 1.1 新增 `tests/test_s057_target_scope.py`,依 delta spec 寫測試並確認修改前失敗(回歸項目除外):
  - S-036 / S-101:S-057 後攻擊,宣告時不詢問 `injure_instead_target`;獲勝時魔書與全部魔物受到傷害。
  - S-070:選魔書時不詢問 S-057 的對象、魔書受到傷害;選魔物時只詢問一次對象(回歸)。
  - S-069:宣告時詢問對象;正面時選定的魔物受到傷害、魔書不受傷害;反面時沒有傷害。
  - 不適用時仍用掉待命:先 S-036、再 S-008,第二場不詢問對象、魔書受到傷害。
  - S-020 / S-064 / 一般戰術(回歸)。
  - 守門:第 1〜3 彈有「ダメージ」的攻擊戰術中,不適用 S-057 的名單是 S-036 / S-058 / S-064 / S-070 / S-101。

## 2. 引擎與卡片

- [x] 2.1 共用的適用判斷與 rider 旗標(D1);`injure_instead` 待命改用它,刪除 `spell_deals_damage`;M-055 的條件改用共用的字串判斷
- [x] 2.2 `AttackBookDamage` 在 `injure_instead` 時改傷害選定的魔物(D2);S-070 設旗標
- [x] 2.3 更新程式碼註解;`python -m pytest tests -m "not slow and not browser" -q` 全過(1417 passed)
- [x] 2.4 實作中發現:S-057 的待命(`ScheduleInjureInsteadNextWin`)排程時沒有帶 `expires: "next_battle"`,條件不符時會留到本回合之後的戰鬥,與效果文「このターン中の次のバトル」不符(戰鬥開始特性測試的 `STANDBYS` 本來就假設有);補上。`tests/golden/battle_start.json` 以 `GOLDEN_UPDATE=1` 重新產生,差異只有 `spell_zeon`(S-058 攻擊)不再套用 S-057、待命留到戰鬥結束時移除;`test_golden_covers_expected_consumption` 加上這一項

## 3. 驗證

- [x] 3.1 全套 `python -m pytest tests -q` 通過(確認瀏覽器測試沒有被略過);`openspec validate --all --strict` 與基準相比沒有新增失敗(1808 passed、10 skipped;validate 的 battle-api、battle-ui、card-data 與基準相同)
- [x] 3.2 本機實際操作抽查(使用者)

## 4. Reconciliation(指南 §13)

- [x] 4.1 同步 delta spec 到 `openspec/specs/card-effects/spec.md`
- [x] 4.2 `openspec/specs/card-effects/design.md`:新增「S-057 只改變沒有指定對象的傷害」(`Project Decision`,2026-11-01),刪除 l12-effect-fixes 那一節的「待確認」
- [x] 4.3 `openspec/specs/game-engine/design.md` 待命表 `injure_instead` 的適用條件
- [x] 4.4 刪除 `todo.md` 的 S-036 / S-101 項目
