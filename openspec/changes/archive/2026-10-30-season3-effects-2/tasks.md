## 1. 測試先行

- [x] 1.1 `tests/test_season3_effects_2.py`:22 張每張至少一個依效果文寫的行為測試(擲幣正 / 反、可選效果的使用 / 不使用、選擇者、使用條件的錯誤碼、時效);執行並確認修改前失敗(卡片尚未開放或效果未註冊)
- [x] 1.2 機制測試:Ex-047 強制保護(已負傷、優先於 P-027、對象就是指定魔物、不妨礙防禦)、Ex-043 上一回合屬性(被無效的戰術也算)、PR-005 戰鬥階段有行動後被拒絕與順序選擇、Ex-048 四種方向(含 P-021 / P-020)、M-055 正 / 反 / 不使用 / 對手沒有魔物、P-042 / P-043 以其他魔物攻擊時待命消失、M-059 不能保護且 M-051 也負傷、PR-009 只移除限制;確認修改前失敗

## 2. 引擎機制

- [x] 2.1 強制保護 `forced_protector`(design D1);Ex-047 測試與既有保護測試通過
- [x] 2.2 戰術屬性紀錄 `spell_attrs_by_turn`(D2);Ex-043 測試通過
- [x] 2.3 `battle_phase_acted` 與 PR-005 的條件、順序選擇(D3);PR-005 測試通過
- [x] 2.4 `SetBothMp`(D4);Ex-048 測試與既有 MP 保護測試通過
- [x] 2.5 攻擊資訊加 `attack_slot`、`attack_undefendable` 限定魔物 UID、`battle_lock` 待命、`on_attack` 待命決策(D5);M-054 / M-055 / P-042 / P-043 測試與既有下一場戰鬥待命測試通過
- [x] 2.6 限制旗標 `NO_EVENTS` / `NO_DEFENSE_SPELL_SLOT` / `NO_PROTECT_SLOT` / `NO_NAMED_SPELLS` 與 P-038 的常駐檢查;移除範圍(P-034 / E-036)依分類(D6);相關測試通過
- [x] 2.7 `InjureChosenOpponentMamodo`(D7)、Ex-031 的使用條件(D8)、`named_immune`(D9)、結束階段棄掉的待命(D10);對應測試與既有結束階段定序測試通過

## 3. 卡片登記

- [x] 3.1 22 張登記於 `effects/cards/` 對應檔案(依卡號排序)
- [x] 3.2 `data/pending_cards.json` 移除 22 張;`tests/test_season3_cards.py` 的開放張數更新;`python -m pytest tests -m "not slow and not browser" -q` 全過

## 4. 前端與 NPC

- [x] 4.1 新事件(`protect_forced`、無傷害的負傷等)、作用中效果、限制與選項的文字(zh-TW / en / ja,`build_zh_cn.py` 產生 zh-CN);新的決策種類若有,補 `choice.title.<kind>`;相關瀏覽器測試通過
- [x] 4.2 NPC 自我對戰牌組含這批卡不卡住(slow 自我對戰測試)

## 5. 驗證

- [x] 5.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗
- [x] 5.2 本機實際操作抽查(使用者)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 回 `card-effects`、`game-engine` 主 spec
- [x] 6.2 `card-effects/design.md`:「行為決定與理由」加入這批的解讀(依 design D11 的狀態)、限制分類表更新;`game-engine/design.md`:強制保護、攻擊時的待命決策、戰鬥階段行動紀錄
- [x] 6.3 capability map 視需要更新

## Workflow follow-up

- 歸檔:`openspec archive season3-effects-2 --skip-specs -y`(主 spec 已手動同步),在 `season3-effects-2` 分支提交;合併 main 與推送等使用者指示
