## 1. 測試先行

- [x] 1.1 新增 `tests/test_l12_effect_fixes.py`,依 delta spec 逐項寫依效果文的測試，執行並確認修改前失敗(錯誤碼精確比對;斷言「沒有發生」時先確認不是停在其他 pending):
  - M-001 / M-017:其他魔物攻擊時可以使用、合計魔力不變;自己防禦的戰鬥中被拒絕(`ability.condition`,回歸)。M-010:其他魔物防禦時可以使用。
  - M-005:防禦時可以使用;該名稱的戰術反擊傷害 +1;其他名稱的戰術反擊傷害不變(使用成立、支付 MP)。
  - M-031:合計魔力 6000 以下的反擊傷害，以 M-031 保護時不受傷害;超過 6000 時受到傷害。
  - E-013:魔物受到的傷害不能保護(S-058 攻擊);使用者自己受到的反擊傷害可以保護;E-031 / M-042 仍可保護(回歸)。
  - S-035 類:S-057 正面後以 S-035 攻擊、擲出 2 次正面，傷害轉到魔物時不能保護。
  - P-027:受 E-013 / S-035 類 / P-026 / E-043 限制時，不能以 P-027 指定的對手魔物保護;受方有 E-031 時可以。
  - E-027:對手 M-049 的搭檔不棄掉;自己的 M-049 不阻止自己的 E-027。
  - S-040:防禦時擲 3 次，魔力為正面數 ×2000(正面數 0 與 >0 各一)。
  - S-057:以 S-020 攻擊時宣告不詢問對象、獲勝時對手 MP -3、沒有魔物受到傷害;以有傷害的戰術攻擊照舊(回歸)。
- [x] 1.2 依舊解讀寫、會反轉的既有測試改依新規則，並確認改後在修改前失敗。實作中其他因新規則失敗的測試，逐一判斷是應該反轉還是回歸，應該反轉的補列在這裡。(沒有需要反轉的行為測試;`test_m017_not_usable_when_defending` 等仍成立。因改名而更新:`tests/test_effect_tree.py` 的 `DisableProtection` / `AddSpellPowerPerHeads` / `OwnSideInBattle` 節點測試、`tests/test_level3.py::test_e036_removes_both_players_three_kinds`、`tests/test_npc.py` 的 `_attack_on`、`tests/test_battle_start_characterization.py`;`tests/golden/battle_start.json` 以 `GOLDEN_UPDATE=1` 重新產生,差異只有 `no_protect_book: true` → `no_protect: [1]` 與待命種類改名)

## 2. 引擎與卡片

- [x] 2.1 M-001 / M-010 / M-017 改用 `OwnSideInBattle`(D1)
- [x] 2.2 M-005 的使用條件與 `counter_book_damage` 的加值(D2)
- [x] 2.3 記錄 `defense_total`,`ImmuneToSpellDamageAtMost` 適用反擊(D3)
- [x] 2.4 `no_protect_book` 統一改為 `no_protect`,E-013 限制使用者的對手，`_eligible_protectors` 魔書與魔物都擋;P-027 指定的對手魔物也受受方的保護限制(D4)
- [x] 2.5 E-027 對手那一半跳過受保護的搭檔(D5)
- [x] 2.6 S-040 防禦時擲幣，`AddSpellPowerPerHeads`(D6)
- [x] 2.7 S-057 待命只適用本來會造成傷害的戰術(D7)
- [x] 2.8 刪除不再使用的節點(`SelfInBattleAs`、`OwnSpellOrEffectAttacking` 若無其他使用者),更新程式碼註解與 docstring 中的舊說法(「不能保護魔書」「只限攻擊」等);`python -m pytest tests -m "not slow and not browser" -q` 全過
- [x] 2.9 畫面上的效果說明:`effect.standby.no_protect_book` / `effect.restriction.no_protect_book` 改為 `no_protect`,四語文字改為「不能以魔物保護傷害」(不限魔書)

## 3. 驗證

- [x] 3.1 NPC 自我對戰不卡住(slow 自我對戰測試,全套測試中通過)
- [x] 3.2 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗(Reload 釋放記憶體後:1799 passed、1 failed——`test_cheat_editor.py::test_post_response_from_closed_editor_preserves_new_draft` 整套執行時失敗、單獨執行通過,與先前 change 記錄的情況相同,與本 change 無關。第一次執行時容器記憶體用滿 3 GB,瀏覽器測試大量逾時。`openspec validate`:battle-api、battle-ui、card-data 三個規格失敗,本 change 沒有修改它們)
- [x] 3.3 本機實際操作抽查(使用者)

## 4. Reconciliation(指南 §13)

- [x] 4.1 同步 delta spec 到 `openspec/specs/card-effects/spec.md`;既有需求中寫到「不能保護魔書」或與新行為衝突的文字一併修正(例如「限制效果的分類」中 S-035 類的列舉補上 S-111)
- [x] 4.2 `openspec/specs/card-effects/design.md`:
  - 規則機制改寫 `no_protect`(限制分類、移除限制兩節);
  - 「行為決定與理由」新增 M-001 類、M-005、M-031、不能保護的範圍、E-027、S-040、S-057 的決定。理由為效果文 / 卡頁 FAQ,確認狀態 `Project Decision`(使用者 2026-10-31 決定);E-027 選擇保留的方式 `Inferred`;
  - M-025 補記 FAQ 衝突與採用效果文的理由(D8)。
- [x] 4.3 `openspec/specs/game-engine/design.md`:待命表 `no_protect_book` → `no_protect`、可保護者的檢查順序說明(刪除「P-027 指定的對手魔物不受受方的限制」)
- [x] 4.4 `openspec/specs/effect-tree/spec.md` 的範例情境把 `SelfInBattleAs("attack")` 改為 `OwnSideInBattle("attack")`;確認 capability map 是否需要更新(不需要:沒有新增 capability,範圍描述不變)
